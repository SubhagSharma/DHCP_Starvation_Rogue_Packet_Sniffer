#!/usr/bin/env bash
# =============================================================================
# setup_attacker.sh — Machine 2 Setup (Attacker Machine)
# =============================================================================
# Run once on the attacker machine before running any attack scripts.
# Must be executed as root.
#
# Usage:
#   chmod +x setup_attacker.sh
#   sudo ./setup_attacker.sh
# =============================================================================

set -euo pipefail

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
ATTACKER_IF="eth0"           # Interface that connects to DHCP-Lab hotspot
ATTACKER_IP="192.168.1.200"   # Desired static IP for rogue server / MITM
SSID="DHCP-Lab"
WIFI_PASS="12345678"

# ── COLORS ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

[[ "$EUID" -eq 0 ]] || error "Run as root."

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   DHCP Security Lab — Machine 2 (Attacker) Setup         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── STEP 1: Install dependencies ─────────────────────────────────────────────
info "Step 1/5 — Installing packages..."
apt-get update -qq
apt-get install -y \
    python3-pip \
    python3-dev \
    net-tools \
    iproute2 \
    wireless-tools \
    wpasupplicant \
    iptables \
    > /dev/null
pip3 install --quiet scapy --break-system-packages
success "Packages installed"

# Step 2 replacement — no WiFi, just set static IP on eth0
info "Step 2/5 — Assigning static IP on ${ATTACKER_IF}..."
ip link set "$ATTACKER_IF" up
ip addr flush dev "$ATTACKER_IF" 2>/dev/null || true
ip addr add "${ATTACKER_IP}/24" dev "$ATTACKER_IF"
ip route add default via 192.168.1.1 dev "$ATTACKER_IF" 2>/dev/null || true
success "IP ${ATTACKER_IP} assigned to ${ATTACKER_IF}"

# ── STEP 3: Assign rogue static IP (additional alias) ─────────────────────────
info "Step 3/5 — Adding rogue IP alias ${ATTACKER_IP} ..."
ip addr add "${ATTACKER_IP}/24" dev "$ATTACKER_IF" 2>/dev/null \
    && success "Rogue IP ${ATTACKER_IP} added to ${ATTACKER_IF}" \
    || warn "${ATTACKER_IP} already assigned (OK)"

# ── STEP 4: Enable IP forwarding (for MITM) ───────────────────────────────────
info "Step 4/5 — Enabling IP forwarding for MITM..."
echo 1 > /proc/sys/net/ipv4/ip_forward
success "IP forwarding enabled"

# ── STEP 5: Verify connectivity ───────────────────────────────────────────────
info "Step 5/5 — Verifying connectivity to Kali (192.168.1.1)..."
if ping -c 2 -W 2 192.168.1.1 &>/dev/null; then
    success "Can reach Kali at 192.168.1.1"
else
    warn "Cannot ping 192.168.1.1 — verify hotspot connection manually"
fi

# ── SUMMARY ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Attacker Setup Complete!                                ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║   Interface  : ${ATTACKER_IF}                                    ║"
echo "║   Rogue IP   : ${ATTACKER_IP}                            ║"
echo "║   Connected  : ${SSID}                               ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║   Attack scripts (run each in a separate terminal):       ║"
echo "║     sudo python3 starvation.py                           ║"
echo "║     sudo python3 rogue_dhcp.py                           ║"
echo "║     sudo python3 mitm_sniffer.py                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
