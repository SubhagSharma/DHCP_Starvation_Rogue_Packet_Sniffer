# 🔐 DHCP Info Security Lab
### Demonstrating DHCP Attacks & Advanced Defenses (IPS + DHCP Snooping)

> **Educational use only.** Run exclusively in an isolated, controlled lab network.
> Never deploy against systems you do not own and have explicit permission to test.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Network Diagram](#network-diagram)
4. [Project Structure](#project-structure)
5. [Module Reference](#module-reference)
6. [Quick Start](#quick-start)
7. [Configuration](#configuration)
8. [Limitations](#limitations)

---

## Overview

This project is a complete, self-contained lab environment for studying DHCP
protocol vulnerabilities and the defenses used against them. It implements
everything in pure Python 3 + Scapy — no dnsmasq, no isc-dhcp-server,
no external attack tools.

**Demonstrated attacks:**
| Attack | Script | Description |
|---|---|---|
| DHCP Starvation | `starvation.py` | Exhausts the IP pool with random MACs |
| Rogue DHCP Server | `rogue_dhcp.py` | Wins the DHCP race with a faster OFFER |
| MITM Interception | `mitm_sniffer.py` | Captures DNS + HTTP after rogue DHCP wins |

**Demonstrated defenses:**
| Defense | Module | Description |
|---|---|---|
| Rate Limiting | `server.py` (IPS) | Drops DISCOVERs exceeding threshold per MAC |
| Starvation Detection | `defense.py` | Alerts on burst of unique MACs/sec |
| Rogue DHCP Detection | `defense.py` | Flags OFFERs/ACKs from untrusted IPs |
| DHCP Snooping | `server.py` + `defense.py` | Binding table enforcement |
| IP/MAC Blocking | `utils.py` | iptables + ebtables auto-block |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Machine 1 — Kali Linux                     │
│  Role: Legitimate DHCP Server + AP          │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ hostapd  │  │server.py │  │defense.py│ │
│  │ (AP/HW)  │  │(DHCP+IPS)│  │(IPS+snoop│ │
│  └──────────┘  └──────────┘  └──────────┘ │
│       │              │              │       │
│    wlan0          wlan0           wlan0     │
└──────────────────────────────────────────────
           │  (802.11 WiFi — DHCP-Lab)
    ───────┴────────────────────────────
    │                                  │
┌───┴──────────────────┐  ┌────────────┴────────────────┐
│  Machine 2 — Attacker│  │  Machine 3+ — Victims       │
│                      │  │                             │
│  starvation.py       │  │  Any WiFi device            │
│  rogue_dhcp.py       │  │  SSID: DHCP-Lab             │
│  mitm_sniffer.py     │  │  IP via DHCP (automatic)    │
└──────────────────────┘  └─────────────────────────────┘
```

---

## Network Diagram

```
Internet
    │
    │ eth0 (uplink)
┌───┴──────────────────────────────────────────────┐
│  Kali (192.168.1.1)                               │
│  iptables NAT: wlan0 → eth0                       │
│  wlan0 — AP "DHCP-Lab"                            │
│  DHCP Pool: 192.168.1.100 – 192.168.1.120         │
└───────────────────┬───────────────────────────────┘
                    │  192.168.1.0/24
          ┌─────────┴──────────────────┐
          │                            │
    ┌─────┴──────────┐        ┌────────┴──────────┐
    │ Attacker       │        │ Victim(s)         │
    │ 192.168.1.200  │        │ .100 – .120 (legit│
    │ or .150–.170   │        │  or .150–.170 if  │
    │ (rogue pool)   │        │  rogue wins)      │
    └────────────────┘        └───────────────────┘
```

---

## Project Structure

```
dhcp_security_project/
│
├── config.py          — All tunable parameters
├── utils.py           — Shared helpers (logging, IP/MAC, iptables)
│
├── server.py          — Legitimate DHCP server + IPS + DHCP Snooping
├── defense.py         — Standalone IPS + Snooping monitor
│
├── starvation.py      — Attack: DHCP Starvation flood
├── rogue_dhcp.py      — Attack: Rogue DHCP Server
├── mitm_sniffer.py    — Attack: MITM DNS+HTTP capture
│
├── setup_kali.sh      — Machine 1 full setup
├── setup_attacker.sh  — Machine 2 full setup
├── setup_victim.md    — Machine 3+ instructions
│
├── run_server.sh      — Start server + defense (Machine 1)
├── run_attacker.sh    — Interactive attack launcher (Machine 2)
├── run_defense.sh     — Start defense only (Machine 1)
│
├── README.md          — This file
└── demo_guide.md      — Step-by-step demo walkthrough
```

---

## Module Reference

### `config.py`
Central configuration. Edit this first.

Key settings:
```python
SERVER_IP      = "192.168.1.1"
POOL_START     = "192.168.1.100"
POOL_END       = "192.168.1.120"
KALI_WLAN_IF   = "wlan0"
ATTACKER_IF    = "wlan0"
RATE_LIMIT_MAX_REQ    = 5   # DISCOVERs per MAC per 10s
STARVATION_THRESHOLD  = 10  # unique MACs/sec
```

### `server.py`
Full DHCP lifecycle (DISCOVER→OFFER, REQUEST→ACK/NAK).

IPS features:
- `LeaseDB` — thread-safe pool + lease tracking with expiry
- `IPS` — per-MAC rate limiting, starvation detection, block-list
- `DHCPSnooping` — binding table + rogue server validation

### `defense.py`
Passive monitor. Runs alongside `server.py`.

Detectors:
- `StarvationDetector` — sliding window, per-MAC + global rate
- `RogueDHCPDetector` — OFFER/ACK from untrusted IPs
- `SnoopingValidator` — cross-checks binding table

### `starvation.py`
Sends DHCP DISCOVER packets with random spoofed MACs.

```bash
sudo python3 starvation.py -i wlan0 -c 200 -t 0.05
```

### `rogue_dhcp.py`
Listens for DISCOVER, responds with OFFER containing malicious gateway/DNS.

### `mitm_sniffer.py`
Captures DNS queries and HTTP traffic (including POST credentials).

---

## Quick Start

### Machine 1 (Kali)
```bash
sudo chmod +x setup_kali.sh
sudo ./setup_kali.sh

# Terminal 1
sudo python3 server.py

# Terminal 2
sudo python3 defense.py
```

### Machine 2 (Attacker)
```bash
sudo chmod +x setup_attacker.sh
sudo ./setup_attacker.sh

sudo python3 starvation.py     # Attack 1
sudo python3 rogue_dhcp.py     # Attack 2
sudo python3 mitm_sniffer.py   # Attack 3
```

### Machine 3+ (Victim)
Connect to WiFi: **SSID: DHCP-Lab** / **Password: 12345678**  
Set IP to Automatic (DHCP).

---

## Configuration

All parameters are in `config.py`. Key values to adjust before running:

| Parameter | Default | Notes |
|---|---|---|
| `KALI_WLAN_IF` | `wlan0` | Adjust to your actual WiFi interface name |
| `ATTACKER_IF` | `wlan0` | Attacker's WiFi interface |
| `KALI_ETH_IF` | `eth0` | Internet uplink on Kali |
| `RATE_LIMIT_MAX_REQ` | `5` | DISCOVERs per MAC allowed in window |
| `STARVATION_THRESHOLD` | `10` | Unique MACs/sec before alert fires |
| `STARVATION_PACKET_COUNT` | `200` | 0 = infinite |

---

## Limitations

| Limitation | Detail |
|---|---|
| HTTPS traffic | Not visible to MITM sniffer — SSL/TLS encrypts it |
| DHCP race | Rogue DHCP win depends on timing; not guaranteed |
| Root required | All scripts need `sudo` (raw socket / iptables access) |
| Hardware | WiFi card must support AP mode for `hostapd` (check: `iw list`) |
| Binding table | `defense.py` reads bindings written by `server.py`; run both |
| ARP poisoning | Not included — MITM requires rogue DHCP to redirect gateway |
| IPv6 | Not covered — only IPv4 DHCP |

---

## Dependencies

```
Python 3.10+
scapy >= 2.5.0
hostapd
iptables / ebtables
```

Install:
```bash
apt install hostapd ebtables net-tools
pip3 install scapy
```
Note- If Rogue Server code doesn't work properly, change required IP Pool and run server.py from attacker machine
