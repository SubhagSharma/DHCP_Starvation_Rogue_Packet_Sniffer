#!/usr/bin/env bash
# run_server.sh — Start DHCP Server + Defense Engine (Machine 1 — Kali)
# Usage: sudo ./run_server.sh [wlan-interface]

set -euo pipefail
IFACE="${1:-wlan0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

[[ "$EUID" -eq 0 ]] || { echo "Run as root"; exit 1; }

echo "Starting DHCP Server + Defense on interface: $IFACE"
echo "Press Ctrl+C in each terminal to stop."
echo ""

# Launch server.py in background, defense.py in foreground
cd "$SCRIPT_DIR"

# Terminal 1: server
echo "[1/2] Launching server.py in background (logs: /tmp/dhcp_lab.log)..."
python3 server.py "$IFACE" &
SERVER_PID=$!
echo "      server.py PID: $SERVER_PID"

sleep 1

# Terminal 2: defense (foreground — shows live alerts)
echo "[2/2] Launching defense.py (foreground — shows alerts)..."
python3 defense.py "$IFACE"

# Cleanup on exit
wait "$SERVER_PID" 2>/dev/null || true
