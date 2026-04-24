# 👤 Setup Guide — Victim Machine(s)

Machine 3+ in the lab. Any WiFi-capable device (Linux, Windows, macOS, Android, iOS).

---

## Requirements

- WiFi capability
- DHCP client (automatic IP — enabled by default on all OSes)

---

## Step 1 — Connect to the Hotspot

| Field     | Value       |
|-----------|-------------|
| SSID      | `DHCP-Lab`  |
| Password  | `12345678`  |
| Security  | WPA2        |

### Linux (NetworkManager)
```bash
nmcli dev wifi connect "DHCP-Lab" password "12345678"
```

### Linux (wpa_supplicant manual)
```bash
wpa_passphrase "DHCP-Lab" "12345678" > /tmp/wpa.conf
sudo wpa_supplicant -B -i wlan0 -c /tmp/wpa.conf
sudo dhclient wlan0
```

### Windows
- Click WiFi icon → find `DHCP-Lab` → Connect → enter `12345678`

### macOS
- Menu bar WiFi → `DHCP-Lab` → password `12345678`

---

## Step 2 — Verify IP Assignment

After connecting, confirm the assigned IP:

```bash
# Linux
ip addr show wlan0
# or
ifconfig wlan0

# Windows
ipconfig /all

# macOS
ifconfig en0
```

**Expected (legitimate):** IP in range `192.168.1.100 – 192.168.1.120`  
**If rogue DHCP wins:** IP in range `192.168.1.150 – 192.168.1.170` (attack demonstrated)

---

## Step 3 — Test Connectivity

```bash
ping 192.168.1.1        # Kali gateway
ping 8.8.8.8            # Internet (via NAT)
curl http://example.com # HTTP traffic — visible to MITM sniffer
```

---

## Step 4 — Observe DHCP Assignment

To watch DHCP in real time on Linux:
```bash
sudo tcpdump -i wlan0 -n port 67 or port 68
```

---

## Notes

- Set IP to **Automatic (DHCP)** — do NOT set a static IP
- The machine needs no special software installed
- In the MITM demo phase, HTTP traffic to non-HTTPS sites will be captured
- HTTPS traffic is **not** visible to the MITM sniffer (SSL/TLS protects it)
