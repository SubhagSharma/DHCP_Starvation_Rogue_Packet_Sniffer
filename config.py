"""
config.py — Central configuration for DHCP Security Lab
All tunable parameters live here. Import this in every module.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SCENARIO SELECTOR  ← change this one value to switch modes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  "VULNERABLE"  — All defenses OFF.  Attacks succeed fully.
                  Use this to demonstrate what happens without protection.

  "PROTECTED"   — All defenses ON.   IPS + DHCP Snooping active.
                  Use this to demonstrate the mitigations working.

  "CUSTOM"      — Each defense toggled individually below.
                  Mix and match for partial-defense scenarios.
"""

# ┌─────────────────────────────────────────────────────┐
# │  ★  CHANGE THIS TO SWITCH THE ENTIRE LAB MODE  ★   │
# └─────────────────────────────────────────────────────┘
SCENARIO = "CUSTOM"      # "VULNERABLE" | "PROTECTED" | "CUSTOM"


# ═══════════════════════════════════════════════════════
# INDIVIDUAL DEFENSE FLAGS  (only used when SCENARIO = "CUSTOM")
# ═══════════════════════════════════════════════════════
#
# Set each flag to True (enabled) or False (disabled).
# When SCENARIO is "VULNERABLE" all flags are forced OFF.
# When SCENARIO is "PROTECTED"  all flags are forced ON.
# When SCENARIO is "CUSTOM"     each flag is used as-is.
#
# ── IPS controls ──────────────────────────────────────
IPS_ENABLED                  = True   # master IPS switch
IPS_RATE_LIMIT_ENABLED       = True   # drop DISCOVERs exceeding per-MAC rate
IPS_STARVATION_DETECT_ENABLED = True  # alert + drop on MAC flood burst
IPS_BLOCKLIST_ENABLED        = True   # enforce MAC / IP block-list entries
IPS_POOL_GUARD_ENABLED       = True   # refuse OFFERs when pool is exhausted

# ── DHCP Snooping controls ────────────────────────────
SNOOPING_ENABLED             = True   # master snooping switch
SNOOPING_ROGUE_DETECT_ENABLED = True  # flag OFFER/ACK from untrusted server IPs
SNOOPING_BINDING_ENFORCE     = True   # reject REQUEST that mismatches binding table
SNOOPING_AUTO_BLOCK_ROGUE    = True   # add iptables rule for detected rogue server


# ═══════════════════════════════════════════════════════
# SCENARIO RESOLVER  — do NOT edit below this line
# ═══════════════════════════════════════════════════════
# Applies the SCENARIO override so every module just imports
# the resolved flags (IPS_* / SNOOPING_*) and checks them.

def _apply_scenario(scenario: str) -> None:
    """Force all flags ON or OFF according to SCENARIO."""
    import sys
    this = sys.modules[__name__]

    ips_flags = [
        "IPS_ENABLED",
        "IPS_RATE_LIMIT_ENABLED",
        "IPS_STARVATION_DETECT_ENABLED",
        "IPS_BLOCKLIST_ENABLED",
        "IPS_POOL_GUARD_ENABLED",
    ]
    snoop_flags = [
        "SNOOPING_ENABLED",
        "SNOOPING_ROGUE_DETECT_ENABLED",
        "SNOOPING_BINDING_ENFORCE",
        "SNOOPING_AUTO_BLOCK_ROGUE",
    ]

    if scenario == "VULNERABLE":
        for f in ips_flags + snoop_flags:
            setattr(this, f, False)

    elif scenario == "PROTECTED":
        for f in ips_flags + snoop_flags:
            setattr(this, f, True)

    # "CUSTOM" → leave flags as defined above

_apply_scenario(SCENARIO)


# ─────────────────────────────────────────────
# NETWORK
# ─────────────────────────────────────────────
NETWORK        = "192.168.1.0/24"
SERVER_IP      = "192.168.1.2"
SUBNET_MASK    = "255.255.255.0"
BROADCAST      = "192.168.1.255"
GATEWAY_IP     = "192.168.1.2"
DNS_SERVER     = "8.8.8.8"
LEASE_TIME     = 3600          # seconds

# ─────────────────────────────────────────────
# DHCP POOL
# ─────────────────────────────────────────────
POOL_START     = "192.168.1.140"
POOL_END       = "192.168.1.160"
POOL_SIZE      = 21            # 100–120 inclusive

# ─────────────────────────────────────────────
# NETWORK INTERFACE NAMES
# ─────────────────────────────────────────────
# Machine 1 (Kali) — adjust to your actual interface names
KALI_WLAN_IF   = "eth0"       # hotspot interface
KALI_ETH_IF    = "usb0"        # uplink / internet interface

# Machine 2 (Attacker) — adjust to your actual interface name
ATTACKER_IF    = "eth0"       # interface connected to DHCP-Lab

# ─────────────────────────────────────────────
# IPS THRESHOLDS
# ─────────────────────────────────────────────
RATE_LIMIT_WINDOW    = 10      # seconds in the rate-limit sliding window
RATE_LIMIT_MAX_REQ   = 5       # max DHCP DISCOVERs per MAC per window
STARVATION_THRESHOLD = 10      # unique MACs/sec to trigger starvation alert
ROGUE_DHCP_TIMEOUT   = 2.0     # seconds — if OFFER arrives before this, flag rogue

# ─────────────────────────────────────────────
# DHCP SNOOPING
# ─────────────────────────────────────────────
TRUSTED_DHCP_SERVERS  = [SERVER_IP]   # only these IPs may send OFFERs/ACKs
SNOOPING_BINDING_FILE = "/tmp/dhcp_snooping_bindings.json"

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL      = "INFO"        # DEBUG | INFO | WARNING | ERROR
LOG_FILE       = "/tmp/dhcp_lab.log"

# ─────────────────────────────────────────────
# ROGUE DHCP (attacker settings)
# ─────────────────────────────────────────────
ROGUE_SERVER_IP   = "192.168.1.2"   # attacker's rogue IP
ROGUE_GATEWAY     = "192.168.1.2"   # redirect traffic through attacker
ROGUE_DNS         = "192.168.1.2"   # attacker's fake DNS
ROGUE_POOL_START  = "192.168.1.150"
ROGUE_POOL_END    = "192.168.1.170"

# ─────────────────────────────────────────────
# STARVATION ATTACK
# ─────────────────────────────────────────────
STARVATION_PACKET_INTERVAL = 0.05    # seconds between flood packets
STARVATION_PACKET_COUNT    = 200      # total packets to send (0 = infinite)

# ─────────────────────────────────────────────
# MITM SNIFFER
# ─────────────────────────────────────────────
MITM_CAPTURE_FILE = "/tmp/mitm_capture.log"
HTTP_PORT         = 80
DNS_PORT          = 53
