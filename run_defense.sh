#!/usr/bin/env bash
# run_defense.sh — Run only the defense engine (Machine 1 — Kali)
# Usage: sudo ./run_defense.sh [interface]

set -euo pipefail
IFACE="${1:-wlan0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

[[ "$EUID" -eq 0 ]] || { echo "Run as root"; exit 1; }

cd "$SCRIPT_DIR"
echo "Launching defense engine on interface: $IFACE"
python3 defense.py "$IFACE"
