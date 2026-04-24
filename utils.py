"""
utils.py — Shared utility functions for DHCP Security Lab
"""

import logging
import socket
import struct
import random
import json
import os
from datetime import datetime
from config import LOG_LEVEL, LOG_FILE


# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that writes to both stdout and a log file.
    Each module passes its __name__ or a descriptive name.
    """
    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s  [%(levelname)-8s]  %(name)-20s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    try:
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except PermissionError:
        pass   # non-root environments may not have /tmp write access

    return logger


# ─────────────────────────────────────────────
# IP HELPERS
# ─────────────────────────────────────────────

def ip_to_int(ip: str) -> int:
    """Convert dotted-quad IP to integer."""
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def int_to_ip(n: int) -> str:
    """Convert integer to dotted-quad IP."""
    return socket.inet_ntoa(struct.pack("!I", n))


def ip_in_pool(ip: str, start: str, end: str) -> bool:
    """Return True if ip is within [start, end] inclusive."""
    return ip_to_int(start) <= ip_to_int(ip) <= ip_to_int(end)


def generate_pool(start: str, end: str) -> list:
    """Return list of all IPs in the pool as strings."""
    s, e = ip_to_int(start), ip_to_int(end)
    return [int_to_ip(i) for i in range(s, e + 1)]


# ─────────────────────────────────────────────
# MAC HELPERS
# ─────────────────────────────────────────────

def random_mac() -> str:
    """
    Generate a random unicast MAC address.
    Bit 0 of the first octet = 0 (unicast).
    Bit 1 of the first octet = 0 (globally unique — can keep as is for spoofing).
    """
    mac = [random.randint(0x00, 0xff) for _ in range(6)]
    mac[0] &= 0xfe   # ensure unicast
    return ":".join(f"{b:02x}" for b in mac)


def mac_str_to_bytes(mac: str) -> bytes:
    """Convert 'aa:bb:cc:dd:ee:ff' → b'\\xaa\\xbb\\xcc\\xdd\\xee\\xff'"""
    return bytes(int(x, 16) for x in mac.split(":"))


def mac_bytes_to_str(b: bytes) -> str:
    """Convert b'\\xaa\\xbb...' → 'aa:bb:...'"""
    return ":".join(f"{x:02x}" for x in b)


# ─────────────────────────────────────────────
# DHCP OPTION HELPERS
# ─────────────────────────────────────────────

def get_dhcp_option(pkt, opt_name: str):
    """
    Extract a named DHCP option value from a Scapy packet.
    Returns the value or None.
    """
    from scapy.layers.dhcp import DHCP
    if DHCP not in pkt:
        return None
    for opt in pkt[DHCP].options:
        if isinstance(opt, tuple) and opt[0] == opt_name:
            return opt[1]
    return None


def dhcp_msg_type_name(code: int) -> str:
    """Human-readable name for DHCP message type code."""
    names = {
        1: "DISCOVER",
        2: "OFFER",
        3: "REQUEST",
        4: "DECLINE",
        5: "ACK",
        6: "NAK",
        7: "RELEASE",
        8: "INFORM",
    }
    return names.get(code, f"UNKNOWN({code})")


# ─────────────────────────────────────────────
# BINDING TABLE  (DHCP Snooping persistence)
# ─────────────────────────────────────────────

def load_bindings(path: str) -> dict:
    """Load MAC→IP binding table from JSON file."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_bindings(bindings: dict, path: str) -> None:
    """Persist MAC→IP binding table to JSON file."""
    try:
        with open(path, "w") as f:
            json.dump(bindings, f, indent=2)
    except OSError as e:
        pass  # non-fatal


# ─────────────────────────────────────────────
# IPTABLES HELPERS
# ─────────────────────────────────────────────

def block_ip(ip: str, logger=None) -> None:
    """Block all traffic from an IP using iptables DROP rule."""
    cmd = f"iptables -I INPUT -s {ip} -j DROP"
    ret = os.system(cmd)
    msg = f"[BLOCK] {ip} — iptables rule added (ret={ret})"
    if logger:
        logger.warning(msg)
    else:
        print(msg)


def block_mac(mac: str, interface: str, logger=None) -> None:
    """Block a MAC address via ebtables (if available)."""
    cmd = f"ebtables -I INPUT -i {interface} -s {mac} -j DROP"
    ret = os.system(cmd)
    msg = f"[BLOCK] MAC {mac} on {interface} — ebtables rule added (ret={ret})"
    if logger:
        logger.warning(msg)
    else:
        print(msg)


def unblock_ip(ip: str, logger=None) -> None:
    """Remove DROP rule for an IP (for cleanup / testing)."""
    cmd = f"iptables -D INPUT -s {ip} -j DROP"
    ret = os.system(cmd)
    msg = f"[UNBLOCK] {ip} — iptables rule removed (ret={ret})"
    if logger:
        logger.info(msg)
    else:
        print(msg)


# ─────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────

def print_banner(title: str) -> None:
    width = 60
    print("\n" + "═" * width)
    print(f"  {title}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * width + "\n")
