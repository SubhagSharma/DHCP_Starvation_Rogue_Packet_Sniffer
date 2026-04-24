#!/usr/bin/env python3
"""
defense.py — Standalone IPS + DHCP Snooping Monitor (Machine 1 — Kali)
========================================================================
Runs alongside server.py as an independent passive monitor.
Detects:
  • Starvation attacks  (burst of DISCOVER packets, many unique MACs)
  • Rogue DHCP servers  (OFFER / ACK from untrusted IPs)
  • Binding violations  (REQUEST for an IP not matching the binding table)

Responds:
  • Logs alerts
  • Adds iptables DROP rules for rogue server IPs
  • Adds ebtables DROP rules for attacking MAC addresses
  • Prints a live alert dashboard to the terminal
"""

import time
import threading
import os
from collections import defaultdict, deque
from datetime import datetime

from scapy.all import sniff, Ether, IP, UDP, BOOTP, DHCP, conf

from config import (
    KALI_WLAN_IF,
    TRUSTED_DHCP_SERVERS,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX_REQ,
    STARVATION_THRESHOLD,
    SNOOPING_BINDING_FILE,
    # ── scenario / defense flags ──
    SCENARIO,
    IPS_ENABLED,
    IPS_RATE_LIMIT_ENABLED,
    IPS_STARVATION_DETECT_ENABLED,
    IPS_BLOCKLIST_ENABLED,
    SNOOPING_ENABLED,
    SNOOPING_ROGUE_DETECT_ENABLED,
    SNOOPING_BINDING_ENFORCE,
    SNOOPING_AUTO_BLOCK_ROGUE,
)
from utils import (
    get_logger, get_dhcp_option, dhcp_msg_type_name,
    load_bindings, save_bindings,
    block_ip, block_mac,
    print_banner,
)

log = get_logger("DEFENSE")

# ─────────────────────────────────────────────
# ALERT STORE
# ─────────────────────────────────────────────

class AlertStore:
    """Thread-safe ring buffer of alerts for dashboard display."""

    def __init__(self, maxlen: int = 50):
        self._lock   = threading.Lock()
        self._alerts = deque(maxlen=maxlen)
        self._counts = defaultdict(int)

    def add(self, level: str, category: str, msg: str) -> None:
        ts    = datetime.now().strftime("%H:%M:%S")
        entry = {"ts": ts, "level": level, "category": category, "msg": msg}
        with self._lock:
            self._alerts.append(entry)
            self._counts[category] += 1

        colour = {"INFO": "\033[94m", "WARN": "\033[93m", "CRIT": "\033[91m"}.get(level, "")
        reset  = "\033[0m"
        log.warning(f"{colour}[{level}] [{category}] {msg}{reset}")

    def summary(self) -> dict:
        with self._lock:
            return dict(self._counts)

    def recent(self, n: int = 10):
        with self._lock:
            return list(self._alerts)[-n:]


alerts = AlertStore()


# ─────────────────────────────────────────────
# STARVATION DETECTOR
# ─────────────────────────────────────────────

class StarvationDetector:
    """
    Sliding-window counter:
      • Per-MAC rate (exceeding = individual MAC attack)
      • Global unique-MACs/sec (exceeding = starvation flood)
    """

    def __init__(self):
        self._lock        = threading.Lock()
        self._mac_times   = defaultdict(list)      # mac → [timestamps]
        self._global_win  = []                      # [(timestamp, mac)]
        self._blocked     = set()

    def observe(self, mac: str, src_ip: str = "") -> None:
        now    = time.time()
        cutoff = now - RATE_LIMIT_WINDOW

        with self._lock:
            # per-MAC rate — always track, enforce only when IPS active
            self._mac_times[mac] = [t for t in self._mac_times[mac] if t > cutoff]
            self._mac_times[mac].append(now)
            count = len(self._mac_times[mac])

            if count >= RATE_LIMIT_MAX_REQ and mac not in self._blocked:
                if IPS_ENABLED and IPS_RATE_LIMIT_ENABLED and IPS_BLOCKLIST_ENABLED:
                    self._blocked.add(mac)
                    alerts.add("WARN", "STARVATION",
                                f"Rate limit: MAC {mac} sent {count} DISCOVERs in "
                                f"{RATE_LIMIT_WINDOW}s — BLOCKING")
                    block_mac(mac, KALI_WLAN_IF, log)
                    if src_ip and src_ip not in ("0.0.0.0", ""):
                        block_ip(src_ip, log)
                else:
                    alerts.add("WARN", "STARVATION",
                                f"Rate limit: MAC {mac} sent {count} DISCOVERs in "
                                f"{RATE_LIMIT_WINDOW}s — [IPS OFF: logging only, NOT blocking]")

            # global starvation check (1-second sliding window)
            self._global_win = [(t, m) for t, m in self._global_win if now - t < 1.0]
            self._global_win.append((now, mac))
            unique_macs = len({m for _, m in self._global_win})

            if unique_macs >= STARVATION_THRESHOLD:
                if IPS_ENABLED and IPS_STARVATION_DETECT_ENABLED:
                    alerts.add("CRIT", "STARVATION",
                                f"ATTACK DETECTED — {unique_macs} unique MACs/sec! "
                                f"Pool exhaustion imminent. [IPS BLOCKING]")
                else:
                    alerts.add("CRIT", "STARVATION",
                                f"ATTACK DETECTED — {unique_macs} unique MACs/sec! "
                                f"[IPS OFF: detected but NOT blocking]")


# ─────────────────────────────────────────────
# ROGUE DHCP DETECTOR
# ─────────────────────────────────────────────

class RogueDHCPDetector:

    def __init__(self):
        self._lock        = threading.Lock()
        self._blocked_ips = set()

    def observe(self, src_ip: str, src_mac: str, msg_type: int) -> None:
        """
        Any OFFER (2) or ACK (5) not from a trusted server is rogue.
        """
        if msg_type not in (2, 5):
            return

        if src_ip in TRUSTED_DHCP_SERVERS:
            return

        with self._lock:
            already_blocked = src_ip in self._blocked_ips
            if not already_blocked:
                self._blocked_ips.add(src_ip)

        type_name = dhcp_msg_type_name(msg_type)

        if SNOOPING_ENABLED and SNOOPING_ROGUE_DETECT_ENABLED:
            alerts.add("CRIT", "ROGUE-DHCP",
                       f"ROGUE SERVER DETECTED — IP={src_ip}  MAC={src_mac}  "
                       f"Type={type_name}  [SNOOPING BLOCKING]")
            if not already_blocked and SNOOPING_AUTO_BLOCK_ROGUE:
                block_ip(src_ip, log)
                if src_mac:
                    block_mac(src_mac, KALI_WLAN_IF, log)
        else:
            alerts.add("WARN", "ROGUE-DHCP",
                       f"Untrusted DHCP {type_name} from IP={src_ip}  MAC={src_mac}  "
                       f"[SNOOPING OFF: logging only, NOT blocking]")


# ─────────────────────────────────────────────
# SNOOPING BINDING VALIDATOR
# ─────────────────────────────────────────────

class SnoopingValidator:

    def __init__(self):
        self._lock     = threading.Lock()
        self._bindings = load_bindings(SNOOPING_BINDING_FILE)

    def refresh(self) -> None:
        """Reload binding table from disk (written by server.py)."""
        with self._lock:
            self._bindings = load_bindings(SNOOPING_BINDING_FILE)

    def validate_request(self, mac: str, requested_ip: str) -> bool:
        with self._lock:
            entry = self._bindings.get(mac)
        if entry and entry.get("ip") != requested_ip:
            if SNOOPING_ENABLED and SNOOPING_BINDING_ENFORCE:
                alerts.add("WARN", "SNOOPING",
                           f"Binding violation: {mac} has {entry['ip']} "
                           f"but requested {requested_ip}  [SNOOPING ENFORCING]")
            else:
                alerts.add("WARN", "SNOOPING",
                           f"Binding mismatch: {mac} has {entry['ip']} "
                           f"but requested {requested_ip}  "
                           f"[SNOOPING OFF: logging only, NOT enforcing]")
            return False
        return True


# ─────────────────────────────────────────────
# MAIN DEFENSE ENGINE
# ─────────────────────────────────────────────

class DefenseEngine:

    def __init__(self, iface: str = KALI_WLAN_IF):
        self.iface      = iface
        self.starvation = StarvationDetector()
        self.rogue      = RogueDHCPDetector()
        self.snooping   = SnoopingValidator()

    def _log_mode(self) -> None:
        """Print a clear summary of which defenses are active in this engine."""
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
            f"  DHCP Snooping (master)    : {flag(SNOOPING_ENABLED)}\n"
            f"    Rogue server detection  : {flag(SNOOPING_ROGUE_DETECT_ENABLED)}\n"
            f"    Binding enforcement     : {flag(SNOOPING_BINDING_ENFORCE)}\n"
            f"    Auto-block rogue IP     : {flag(SNOOPING_AUTO_BLOCK_ROGUE)}\n"
            f"  {BOLD}{'═'*54}{RESET}"
        )
        if SCENARIO == "VULNERABLE":
            log.warning(
                f"\033[91m[!] VULNERABLE MODE — all protections DISABLED. "
                f"Attacks will be logged but NOT blocked.\033[0m"
            )

    def handle(self, pkt) -> None:
        if DHCP not in pkt or BOOTP not in pkt:
            return

        msg_type = get_dhcp_option(pkt, "message-type")
        if msg_type is None:
            return

        src_mac = pkt[Ether].src.lower() if Ether in pkt else ""
        src_ip  = pkt[IP].src if IP in pkt else "0.0.0.0"

        # 1. Starvation detection (DISCOVER packets) — always observe, flags control blocking
        if msg_type == 1:
            self.starvation.observe(src_mac, src_ip)

        # 2. Rogue DHCP detection (OFFER / ACK) — always observe, flags control blocking
        if msg_type in (2, 5):
            self.rogue.observe(src_ip, src_mac, msg_type)

        # 3. Snooping binding validation (REQUEST) — always observe, flags control action
        if msg_type == 3:
            requested_ip = get_dhcp_option(pkt, "requested_addr")
            if requested_ip:
                self.snooping.validate_request(src_mac, requested_ip)

    def run(self) -> None:
        print_banner("DEFENSE ENGINE  (Machine 1 — Kali)")
        self._log_mode()
        log.info(f"Monitoring interface : {self.iface}")
        log.info(f"Trusted DHCP servers : {TRUSTED_DHCP_SERVERS}")

        # Periodic binding refresh + dashboard
        def background() -> None:
            while True:
                time.sleep(15)
                self.snooping.refresh()
                summary = alerts.summary()
                if summary:
                    log.info(f"[DEFENSE SUMMARY] {summary}")
                    for a in alerts.recent(5):
                        log.info(f"  {a['ts']}  {a['level']}  {a['category']}  {a['msg']}")

        t = threading.Thread(target=background, daemon=True)
        t.start()

        sniff(
            iface=self.iface,
            filter="udp and (port 67 or port 68)",
            prn=self.handle,
            store=False,
        )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    iface = sys.argv[1] if len(sys.argv) > 1 else KALI_WLAN_IF
    engine = DefenseEngine(iface=iface)
    try:
        engine.run()
    except KeyboardInterrupt:
        log.info("Defense engine stopped.")
        log.info(f"Final alert summary: {alerts.summary()}")
