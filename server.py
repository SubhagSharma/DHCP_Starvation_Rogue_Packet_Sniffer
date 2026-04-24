#!/usr/bin/env python3
"""
server.py — Legitimate DHCP Server (Machine 1 / Kali)
======================================================
• Handles DISCOVER → OFFER → REQUEST → ACK lifecycle
• Maintains IP pool with lease tracking
• Built-in IPS: rate limiting + MAC block-list + pool exhaustion guard
• Built-in DHCP Snooping: trusted-server enforcement + binding table
• All using Scapy only — NO dnsmasq / isc-dhcp-server
"""

import time
import threading
from collections import defaultdict

from scapy.all import (
    sniff, sendp, Ether, IP, UDP, BOOTP, DHCP,
    get_if_hwaddr, conf
)

from config import (
    SERVER_IP, SUBNET_MASK, GATEWAY_IP, DNS_SERVER,
    BROADCAST, LEASE_TIME,
    POOL_START, POOL_END,
    KALI_WLAN_IF,
    RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_REQ,
    STARVATION_THRESHOLD,
    TRUSTED_DHCP_SERVERS,
    SNOOPING_BINDING_FILE,
    # ── scenario / defense flags ──
    SCENARIO,
    IPS_ENABLED,
    IPS_RATE_LIMIT_ENABLED,
    IPS_STARVATION_DETECT_ENABLED,
    IPS_BLOCKLIST_ENABLED,
    IPS_POOL_GUARD_ENABLED,
    SNOOPING_ENABLED,
    SNOOPING_ROGUE_DETECT_ENABLED,
    SNOOPING_BINDING_ENFORCE,
    SNOOPING_AUTO_BLOCK_ROGUE,
)
from utils import (
    get_logger, generate_pool, ip_to_int,
    mac_str_to_bytes, mac_bytes_to_str,
    get_dhcp_option, dhcp_msg_type_name,
    load_bindings, save_bindings,
    block_ip, block_mac,
    print_banner,
)

log = get_logger("DHCP-SERVER")


# ═══════════════════════════════════════════════════
# LEASE DATABASE
# ═══════════════════════════════════════════════════

class LeaseDB:
    """Thread-safe IP pool + lease table."""

    def __init__(self):
        self._lock    = threading.Lock()
        self._pool    = generate_pool(POOL_START, POOL_END)  # available IPs
        self._leases  = {}    # ip → {mac, expiry}
        self._mac_map = {}    # mac → ip  (for offer/ack lookup)

    # ── allocation ─────────────────────────────────

    def allocate(self, mac: str) -> str | None:
        """
        Return an IP for mac.
        Reuses the same IP if mac already has a lease/offer.
        Returns None if pool is exhausted.
        """
        with self._lock:
            # reuse existing assignment
            if mac in self._mac_map:
                ip = self._mac_map[mac]
                self._refresh_lease(ip, mac)
                return ip
            # assign new
            self._expire_leases()
            if not self._pool:
                return None
            ip = self._pool.pop(0)
            self._mac_map[mac] = ip
            self._leases[ip]   = {"mac": mac, "expiry": time.time() + LEASE_TIME}
            return ip

    def confirm(self, mac: str, ip: str) -> bool:
        """ACK the lease (called on REQUEST). Returns False if mismatch."""
        with self._lock:
            entry = self._leases.get(ip)
            if entry and entry["mac"] == mac:
                self._refresh_lease(ip, mac)
                return True
            return False

    def release(self, mac: str) -> None:
        with self._lock:
            ip = self._mac_map.pop(mac, None)
            if ip and ip in self._leases:
                del self._leases[ip]
                self._pool.append(ip)
                log.info(f"[RELEASE] {mac} released {ip}")

    # ── internal ───────────────────────────────────

    def _refresh_lease(self, ip: str, mac: str) -> None:
        self._leases[ip] = {"mac": mac, "expiry": time.time() + LEASE_TIME}

    def _expire_leases(self) -> None:
        now = time.time()
        expired = [ip for ip, e in self._leases.items() if e["expiry"] < now]
        for ip in expired:
            mac = self._leases[ip]["mac"]
            del self._leases[ip]
            self._mac_map.pop(mac, None)
            self._pool.append(ip)
            log.info(f"[EXPIRE] lease {ip} ({mac}) expired")

    # ── stats ──────────────────────────────────────

    @property
    def available(self) -> int:
        with self._lock:
            return len(self._pool)

    @property
    def leases(self) -> dict:
        with self._lock:
            return dict(self._leases)

    def pool_exhausted(self) -> bool:
        with self._lock:
            return len(self._pool) == 0


# ═══════════════════════════════════════════════════
# IPS — Intrusion Prevention System
# ═══════════════════════════════════════════════════

class IPS:
    """
    Rate-limit DHCP DISCOVER requests per MAC.
    Detect starvation (burst of unique MACs).
    Maintain MAC block-list.
    """

    def __init__(self):
        self._lock         = threading.Lock()
        self._rate_table   = defaultdict(list)   # mac → [timestamps]
        self._blocked_macs = set()
        self._blocked_ips  = set()
        self._window_macs  = []   # (timestamp, mac) for starvation detection

    # ── per-MAC rate limit ─────────────────────────

    def check_rate(self, mac: str) -> bool:
        """
        Returns True  → request is ALLOWED.
        Returns False → rate limit exceeded, request should be dropped.
        """
        with self._lock:
            now = time.time()
            cutoff = now - RATE_LIMIT_WINDOW
            # purge old timestamps
            self._rate_table[mac] = [t for t in self._rate_table[mac] if t > cutoff]
            if len(self._rate_table[mac]) >= RATE_LIMIT_MAX_REQ:
                log.warning(f"[IPS] Rate limit exceeded for MAC {mac} "
                             f"({len(self._rate_table[mac])} reqs in {RATE_LIMIT_WINDOW}s)")
                return False
            self._rate_table[mac].append(now)
            return True

    # ── starvation detection ───────────────────────

    def record_discover(self, mac: str) -> bool:
        """
        Track unique MACs in a sliding 1-second window.
        Returns True if starvation threshold is exceeded.
        """
        with self._lock:
            now = time.time()
            self._window_macs = [(t, m) for t, m in self._window_macs if now - t < 1.0]
            self._window_macs.append((now, mac))
            unique = len({m for _, m in self._window_macs})
            if unique >= STARVATION_THRESHOLD:
                log.critical(f"[IPS] STARVATION DETECTED — {unique} unique MACs/sec!")
                return True
            return False

    # ── block-list ─────────────────────────────────

    def block_mac(self, mac: str) -> None:
        with self._lock:
            self._blocked_macs.add(mac)
        log.warning(f"[IPS] MAC {mac} added to block-list")
        block_mac(mac, KALI_WLAN_IF, log)

    def block_ip_addr(self, ip: str) -> None:
        with self._lock:
            self._blocked_ips.add(ip)
        log.warning(f"[IPS] IP {ip} added to block-list")
        block_ip(ip, log)

    def is_blocked_mac(self, mac: str) -> bool:
        with self._lock:
            return mac in self._blocked_macs

    def is_blocked_ip(self, ip: str) -> bool:
        with self._lock:
            return ip in self._blocked_ips


# ═══════════════════════════════════════════════════
# DHCP SNOOPING
# ═══════════════════════════════════════════════════

class DHCPSnooping:
    """
    • Maintains a MAC ↔ IP binding table (persisted to disk).
    • Validates that DHCP OFFERs / ACKs come only from trusted servers.
    • Validates client REQUESTs against the binding table.
    """

    def __init__(self):
        self._lock    = threading.Lock()
        self._bindings = load_bindings(SNOOPING_BINDING_FILE)
        log.info(f"[SNOOPING] Loaded {len(self._bindings)} existing bindings")

    # ── rogue OFFER / ACK detection ────────────────

    def validate_server_packet(self, src_ip: str, msg_type: int) -> bool:
        """
        Returns True if the packet comes from a trusted DHCP server.
        Called for OFFER (2) and ACK (5) packets observed on the network.
        """
        if msg_type not in (2, 5):   # only OFFER / ACK
            return True
        trusted = src_ip in TRUSTED_DHCP_SERVERS
        if not trusted:
            log.critical(
                f"[SNOOPING] ROGUE DHCP SERVER DETECTED! "
                f"Untrusted OFFER/ACK from {src_ip}"
            )
        return trusted

    # ── binding management ─────────────────────────

    def add_binding(self, mac: str, ip: str) -> None:
        with self._lock:
            self._bindings[mac] = {"ip": ip, "timestamp": time.time()}
            save_bindings(self._bindings, SNOOPING_BINDING_FILE)
        log.info(f"[SNOOPING] Binding added: {mac} → {ip}")

    def validate_request(self, mac: str, requested_ip: str) -> bool:
        """
        If a binding exists for mac, the requested IP must match.
        New MACs are always allowed (binding will be created on ACK).
        """
        with self._lock:
            entry = self._bindings.get(mac)
        if entry and entry["ip"] != requested_ip:
            log.warning(
                f"[SNOOPING] Binding violation: {mac} has {entry['ip']} "
                f"but requested {requested_ip}"
            )
            return False
        return True

    def get_binding(self, mac: str) -> str | None:
        with self._lock:
            entry = self._bindings.get(mac)
            return entry["ip"] if entry else None

    @property
    def bindings(self):
        with self._lock:
            return dict(self._bindings)


# ═══════════════════════════════════════════════════
# DHCP SERVER
# ═══════════════════════════════════════════════════

class DHCPServer:

    def __init__(self, iface: str = KALI_WLAN_IF):
        self.iface      = iface
        self.server_mac = get_if_hwaddr(iface)
        self.db         = LeaseDB()
        self.ips        = IPS()
        self.snooping   = DHCPSnooping()
        log.info(f"DHCP Server starting on {iface} ({self.server_mac})")
        log.info(f"Pool: {POOL_START} – {POOL_END}  ({self.db.available} IPs)")
        self._log_mode()

    # ── mode banner ────────────────────────────────

    def _log_mode(self) -> None:
        """Print a clear summary of which defenses are active."""
        RED   = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
        BOLD  = "\033[1m";  RESET = "\033[0m"

        def flag(enabled: bool) -> str:
            return f"{GREEN}ON {RESET}" if enabled else f"{RED}OFF{RESET}"

        scenario_colour = GREEN if SCENARIO == "PROTECTED" else (
                          RED   if SCENARIO == "VULNERABLE" else YELLOW)

        log.info(
            f"\n"
            f"  {BOLD}{'═'*54}{RESET}\n"
            f"  {BOLD}  SCENARIO : {scenario_colour}{SCENARIO}{RESET}\n"
            f"  {BOLD}{'─'*54}{RESET}\n"
            f"  IPS (master)              : {flag(IPS_ENABLED)}\n"
            f"    Rate limiting           : {flag(IPS_RATE_LIMIT_ENABLED)}\n"
            f"    Starvation detection    : {flag(IPS_STARVATION_DETECT_ENABLED)}\n"
            f"    MAC/IP block-list       : {flag(IPS_BLOCKLIST_ENABLED)}\n"
            f"    Pool exhaustion guard   : {flag(IPS_POOL_GUARD_ENABLED)}\n"
            f"  DHCP Snooping (master)    : {flag(SNOOPING_ENABLED)}\n"
            f"    Rogue server detection  : {flag(SNOOPING_ROGUE_DETECT_ENABLED)}\n"
            f"    Binding enforcement     : {flag(SNOOPING_BINDING_ENFORCE)}\n"
            f"    Auto-block rogue IP     : {flag(SNOOPING_AUTO_BLOCK_ROGUE)}\n"
            f"  {BOLD}{'═'*54}{RESET}"
        )
        if SCENARIO == "VULNERABLE":
            log.warning(
                f"\033[91m[!] VULNERABLE MODE — all protections DISABLED. "
                f"Attacks will succeed.\033[0m"
            )

    # ── packet handler ─────────────────────────────

    def handle(self, pkt) -> None:
        if DHCP not in pkt or BOOTP not in pkt:
            return

        msg_type = get_dhcp_option(pkt, "message-type")
        if msg_type is None:
            return

        src_mac = pkt[Ether].src.lower()
        src_ip  = pkt[IP].src if IP in pkt else "0.0.0.0"

        # ── DHCP Snooping: monitor ALL DHCP traffic ──
        if SNOOPING_ENABLED and SNOOPING_ROGUE_DETECT_ENABLED:
            if not self.snooping.validate_server_packet(src_ip, msg_type):
                # Rogue server detected
                if SNOOPING_AUTO_BLOCK_ROGUE:
                    self.ips.block_ip_addr(src_ip)
                return
        elif msg_type in (2, 5) and src_ip not in TRUSTED_DHCP_SERVERS:
            # Snooping disabled — just log, do NOT block
            log.warning(
                f"[SNOOPING-OFF] OFFER/ACK from untrusted {src_ip} — "
                f"snooping disabled, allowing through"
            )

        # ── Dispatch ──────────────────────────────────
        name = dhcp_msg_type_name(msg_type)
        # Always log at INFO so every packet is visible in the terminal
        log.info(
            f"[RX] {name:<10} src_mac={src_mac}  src_ip={src_ip}  "
            f"pool_left={self.db.available}"
        )

        if msg_type == 1:   # DISCOVER
            self._handle_discover(pkt, src_mac)
        elif msg_type == 3:  # REQUEST
            self._handle_request(pkt, src_mac)
        elif msg_type == 7:  # RELEASE
            self.db.release(src_mac)

    # ── DISCOVER → OFFER ───────────────────────────

    def _handle_discover(self, pkt, mac: str) -> None:

        # IPS: block-list check
        if IPS_ENABLED and IPS_BLOCKLIST_ENABLED:
            if self.ips.is_blocked_mac(mac):
                log.warning(f"[IPS] Dropping DISCOVER from blocked MAC {mac}")
                return
        else:
            if self.ips.is_blocked_mac(mac):
                log.info(f"[IPS-OFF] MAC {mac} is in block-list but IPS/blocklist disabled — allowing")

        # IPS: rate limit
        if IPS_ENABLED and IPS_RATE_LIMIT_ENABLED:
            if not self.ips.check_rate(mac):
                return
        else:
            # Still track for logging, but don't enforce
            self.ips.check_rate(mac)

        # IPS: starvation detection
        if IPS_ENABLED and IPS_STARVATION_DETECT_ENABLED:
            if self.ips.record_discover(mac):
                log.critical("[IPS] Starvation attack in progress — pool protection active")
                return
        else:
            # Record for logging/observation even without enforcement
            if self.ips.record_discover(mac):
                log.warning(
                    "[IPS-OFF] Starvation pattern detected — "
                    "NOT blocking (IPS/starvation detection disabled)"
                )

        # Pool protection
        if self.db.pool_exhausted():
            if IPS_ENABLED and IPS_POOL_GUARD_ENABLED:
                log.error("[SERVER] Pool exhausted — cannot offer address (pool guard active)")
                return
            else:
                log.error(
                    "[SERVER] Pool exhausted — "
                    "pool guard disabled, no IPs to assign anyway"
                )
                return

        offered_ip = self.db.allocate(mac)
        if not offered_ip:
            log.error(f"[SERVER] No IP available for {mac}")
            return

        log.info(
            f"[OFFER] ──▶  mac={mac}  ip={offered_ip}  "
            f"pool_remaining={self.db.available}/{len(generate_pool(POOL_START, POOL_END))}"
        )
        self._send_offer(pkt, mac, offered_ip)

    def _send_offer(self, pkt, client_mac: str, offered_ip: str) -> None:
        xid = pkt[BOOTP].xid

        # ── Broadcast flag check ──────────────────────────────────────────
        # RFC 2131: if the BROADCAST bit (bit 15 of 'flags') is set in the
        # DISCOVER, or the client has no real wireless association (spoofed
        # MAC during starvation), we MUST send the OFFER as a broadcast so
        # the frame is not silently dropped by the AP driver.
        # Using broadcast dst is always safe — real clients accept it too.
        broadcast_bit = (pkt[BOOTP].flags & 0x8000) != 0
        eth_dst = "ff:ff:ff:ff:ff:ff"   # broadcast on hotspot for visibility

        offer = (
            Ether(src=self.server_mac, dst=eth_dst)
            / IP(src=SERVER_IP, dst="255.255.255.255")
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2,
                xid=xid,
                yiaddr=offered_ip,
                siaddr=SERVER_IP,
                giaddr="0.0.0.0",
                chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
                flags=0x8000,   # set broadcast bit in reply
            )
            / DHCP(options=[
                ("message-type", "offer"),
                ("server_id",    SERVER_IP),
                ("lease_time",   LEASE_TIME),
                ("subnet_mask",  SUBNET_MASK),
                ("router",       GATEWAY_IP),
                ("name_server",  DNS_SERVER),
                "end",
            ])
        )
        sendp(offer, iface=self.iface, verbose=False)

    # ── REQUEST → ACK / NAK ────────────────────────

    def _handle_request(self, pkt, mac: str) -> None:

        if IPS_ENABLED and IPS_BLOCKLIST_ENABLED:
            if self.ips.is_blocked_mac(mac):
                log.warning(f"[IPS] Dropping REQUEST from blocked MAC {mac}")
                return

        requested_ip = get_dhcp_option(pkt, "requested_addr")
        server_id    = get_dhcp_option(pkt, "server_id")

        # If client is responding to a different server's offer — ignore
        if server_id and server_id != SERVER_IP:
            log.info(f"[SERVER] {mac} accepted offer from {server_id}, ignoring")
            return

        # Use yiaddr if no requested_addr option
        if not requested_ip:
            requested_ip = pkt[BOOTP].ciaddr or self.db._mac_map.get(mac)

        if not requested_ip:
            log.warning(f"[SERVER] REQUEST from {mac} has no IP — sending NAK")
            self._send_nak(pkt, mac)
            return

        # Snooping: binding validation
        if SNOOPING_ENABLED and SNOOPING_BINDING_ENFORCE:
            if not self.snooping.validate_request(mac, requested_ip):
                self._send_nak(pkt, mac)
                return
        else:
            # Check and log only — do not reject
            if not self.snooping.validate_request(mac, requested_ip):
                log.warning(
                    f"[SNOOPING-OFF] Binding mismatch for {mac} / {requested_ip} — "
                    f"snooping enforcement disabled, continuing"
                )

        # Confirm lease
        if self.db.confirm(mac, requested_ip):
            log.info(
                f"[ACK]   ──▶  mac={mac}  ip={requested_ip}  "
                f"pool_remaining={self.db.available}/{len(generate_pool(POOL_START, POOL_END))}"
            )
            self.snooping.add_binding(mac, requested_ip)
            self._send_ack(pkt, mac, requested_ip)
        else:
            log.warning(f"[NAK] {mac} requested {requested_ip} — not in lease table")
            self._send_nak(pkt, mac)

    def _send_ack(self, pkt, client_mac: str, ip: str) -> None:
        xid = pkt[BOOTP].xid
        ack = (
            Ether(src=self.server_mac, dst="ff:ff:ff:ff:ff:ff")
            / IP(src=SERVER_IP, dst="255.255.255.255")
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2,
                xid=xid,
                yiaddr=ip,
                siaddr=SERVER_IP,
                chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
                flags=0x8000,
            )
            / DHCP(options=[
                ("message-type", "ack"),
                ("server_id",    SERVER_IP),
                ("lease_time",   LEASE_TIME),
                ("subnet_mask",  SUBNET_MASK),
                ("router",       GATEWAY_IP),
                ("name_server",  DNS_SERVER),
                "end",
            ])
        )
        sendp(ack, iface=self.iface, verbose=False)

    def _send_nak(self, pkt, client_mac: str) -> None:
        xid = pkt[BOOTP].xid
        nak = (
            Ether(src=self.server_mac, dst="ff:ff:ff:ff:ff:ff")
            / IP(src=SERVER_IP, dst=BROADCAST)
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2, xid=xid,
                chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
            )
            / DHCP(options=[
                ("message-type", "nak"),
                ("server_id",    SERVER_IP),
                "end",
            ])
        )
        sendp(nak, iface=self.iface, verbose=False)

    # ── status printer ─────────────────────────────

    def print_status(self) -> None:
        log.info("=" * 50)
        log.info(f"Pool available: {self.db.available} / {len(generate_pool(POOL_START, POOL_END))}")
        log.info(f"Active leases : {len(self.db.leases)}")
        log.info(f"Snooping table: {len(self.snooping.bindings)} bindings")
        for mac, entry in self.db.leases.items():
            log.info(f"  {entry['mac']}  →  {mac}")
        log.info("=" * 50)

    # ── main loop ──────────────────────────────────

    def run(self) -> None:
        print_banner("DHCP SERVER  (Machine 1 — Kali)")
        log.info(f"Listening on {self.iface}  (port 67/UDP) ...")

        # Periodic status printer
        def status_loop():
            while True:
                time.sleep(30)
                self.print_status()

        t = threading.Thread(target=status_loop, daemon=True)
        t.start()

        sniff(
            iface=self.iface,
            filter="udp and (port 67 or port 68)",
            prn=self.handle,
            store=False,
        )


# ═══════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    iface = sys.argv[1] if len(sys.argv) > 1 else KALI_WLAN_IF
    server = DHCPServer(iface=iface)
    try:
        server.run()
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
        server.print_status()
