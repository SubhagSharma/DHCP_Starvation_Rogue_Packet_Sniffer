#!/usr/bin/env bash
# run_attacker.sh — Interactive menu to launch attack scripts (Machine 2)
# Usage: sudo ./run_attacker.sh [interface]

set -euo pipefail
IFACE="${1:-wlan0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

[[ "$EUID" -eq 0 ]] || { echo "Run as root"; exit 1; }

cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   DHCP Lab — Attacker Machine Menu               ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  1) DHCP Starvation Attack                       ║"
echo "║  2) Rogue DHCP Server                            ║"
echo "║  3) MITM Traffic Sniffer                         ║"
echo "║  4) Run ALL attacks simultaneously               ║"
echo "║  q) Quit                                         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
read -rp "Select option: " choice

case "$choice" in
    1)
        echo "Starting DHCP Starvation..."
        python3 starvation.py -i "$IFACE"
        ;;
    2)
        echo "Starting Rogue DHCP Server..."
        python3 rogue_dhcp.py "$IFACE"
        ;;
    3)
        echo "Starting MITM Sniffer..."
        python3 mitm_sniffer.py "$IFACE"
        ;;
    4)
        echo "Starting ALL attacks (Ctrl+C to stop all)..."
        python3 starvation.py -i "$IFACE" &
        PID1=$!
        python3 rogue_dhcp.py "$IFACE" &
        PID2=$!
        python3 mitm_sniffer.py "$IFACE" &
        PID3=$!
        echo "PIDs: starvation=$PID1  rogue=$PID2  sniffer=$PID3"
        wait
        ;;
    q|Q)
        echo "Bye."
        ;;
    *)
        echo "Invalid option."
        exit 1
        ;;
esac
