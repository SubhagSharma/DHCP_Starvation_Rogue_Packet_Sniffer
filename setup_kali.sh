#!/usr/bin/env bash
# setup_kali.sh — Ethernet + USB-tethering variant

set -euo pipefail

LAN_IF="eth0"       # ethernet to router
USB_IF="usb0"       # USB tethered phone (internet)
KALI_IP="192.168.1.2"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

[[ "$EUID" -eq 0 ]] || error "Run as root."

echo "╔══════════════════════════════════════════╗"
echo "║  DHCP Lab — Kali Setup (Ethernet mode)   ║"
echo "╚══════════════════════════════════════════╝"

# Step 1: packages (no hostapd/wireless-tools needed)
info "Step 1/5 — Installing packages..."
apt-get update -qq
apt-get install -y python3-pip net-tools iptables ebtables iproute2 > /dev/null
pip3 install --quiet scapy --break-system-packages
success "Packages installed"

# Step 2: disable competing DHCP services
info "Step 2/5 — Disabling system DHCP services..."
for svc in dnsmasq isc-dhcp-server; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        systemctl stop "$svc" && systemctl disable "$svc"
        warn "$svc stopped and disabled"
    fi
done
success "System DHCP services disabled"

# Step 3: configure LAN interface
info "Step 3/5 — Configuring ${LAN_IF} (${KALI_IP}/24)..."
ip link set "$LAN_IF" up
ip addr flush dev "$LAN_IF" 2>/dev/null || true
ip addr add "${KALI_IP}/24" dev "$LAN_IF"
success "${LAN_IF} → ${KALI_IP}/24"

# Step 4: USB tethering check
info "Step 4/5 — Checking USB internet (${USB_IF})..."
if ip link show "$USB_IF" &>/dev/null; then
    # USB tethering already visible — request IP via DHCP from phone
    dhclient "$USB_IF" 2>/dev/null || true
    success "${USB_IF} found — internet should be available"
else
    warn "${USB_IF} not found yet. Enable USB tethering on your phone, then run:"
    warn "    dhclient usb0"
fi

# Step 5: NAT — forward LAN traffic out through USB
info "Step 5/5 — Setting up NAT (${LAN_IF} → ${USB_IF})..."
echo 1 > /proc/sys/net/ipv4/ip_forward

iptables -F FORWARD 2>/dev/null || true
iptables -t nat -F   2>/dev/null || true

iptables -t nat -A POSTROUTING -o "$USB_IF" -j MASQUERADE
iptables -A FORWARD -i "$LAN_IF" -o "$USB_IF" -j ACCEPT
iptables -A FORWARD -i "$USB_IF" -o "$LAN_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT

# Allow DHCP on LAN
iptables -A INPUT  -i "$LAN_IF" -p udp --dport 67 -j ACCEPT
iptables -A OUTPUT -o "$LAN_IF" -p udp --sport 67 -j ACCEPT

success "NAT configured"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  Setup complete!                         ║"
echo "║  LAN  : ${LAN_IF} → ${KALI_IP}              ║"
echo "║  WAN  : ${USB_IF} (USB tethering)           ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Next: sudo python3 server.py            ║"
echo "║        sudo python3 defense.py           ║"
echo "╚══════════════════════════════════════════╝"