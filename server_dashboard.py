#!/usr/bin/env python3
"""
server_dashboard.py  —  DHCP Server Live Dashboard
====================================================
Reads the log produced by server.py and visualises all activity in real-time.

Usage:
    streamlit run server_dashboard.py -- --log server.log
"""

import re, os, time, argparse, subprocess
from datetime import datetime

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DHCP Server Monitor",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Exo+2:wght@300;600;900&display=swap');

html, body, [class*="css"] { background:#04080f !important; color:#b0bec5; }
*, *::before, *::after { box-sizing:border-box; }

/* sidebar */
section[data-testid="stSidebar"] { background:#060c15 !important; border-right:1px solid #0a1628; }
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span { color:#2d4a6b !important; font-family:'JetBrains Mono',monospace !important; font-size:.72rem !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2   { color:#1565c0 !important; font-family:'Exo 2',sans-serif !important; }

/* hero */
.hero {
    position:relative; padding:26px 32px 20px;
    background:linear-gradient(135deg,#04080f 0%,#060e1c 60%,#04100a 100%);
    border:1px solid #0a1628; border-radius:12px; margin-bottom:24px; overflow:hidden;
}
.hero::before {
    content:''; position:absolute; inset:0;
    background:radial-gradient(ellipse 50% 90% at 85% 50%, rgba(21,101,192,.09) 0%, transparent 70%),
               radial-gradient(ellipse 30% 60% at 10% 50%, rgba(27,94,32,.07) 0%, transparent 70%);
}
.hero-title {
    font-family:'Exo 2',sans-serif; font-weight:900; font-size:2rem;
    letter-spacing:5px; text-transform:uppercase; margin:0 0 4px;
    color:#42a5f5; text-shadow:0 0 28px rgba(66,165,245,.45);
}
.hero-sub { font-family:'JetBrains Mono',monospace; font-size:.68rem; color:#1a2e4a; letter-spacing:3px; }
.hero-row { display:flex; gap:12px; margin-top:14px; flex-wrap:wrap; }
.hero-pill {
    display:inline-flex; align-items:center; gap:7px;
    border-radius:20px; padding:4px 14px;
    font-family:'JetBrains Mono',monospace; font-size:.68rem;
}
.hero-pill.live  { background:rgba(66,165,245,.08); border:1px solid rgba(66,165,245,.2); color:#64b5f6; }
.hero-pill.vuln  { background:rgba(229,57,53,.08);  border:1px solid rgba(229,57,53,.25); color:#ef9a9a; }
.hero-pill.prot  { background:rgba(46,125,50,.1);   border:1px solid rgba(46,125,50,.25); color:#a5d6a7; }
.hero-pill.part  { background:rgba(245,127,23,.08); border:1px solid rgba(245,127,23,.2); color:#ffe082; }

.pulse { width:8px; height:8px; border-radius:50%; background:#42a5f5;
         box-shadow:0 0 6px #42a5f5; animation:pulse 1.4s ease-in-out infinite; }
.pulse.red   { background:#e53935; box-shadow:0 0 6px #e53935; }
.pulse.green { background:#43a047; box-shadow:0 0 6px #43a047; }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:.2} }

/* ── ATTACK CONTROL PANEL ── */
.ctrl-panel {
    background:#080c13;
    border:1px solid #0e1822;
    border-radius:10px;
    padding:20px 24px;
    margin-bottom:24px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:20px;
    flex-wrap:wrap;
}
.ctrl-status {
    display:flex; align-items:center; gap:10px;
    font-family:'JetBrains Mono',monospace; font-size:.75rem;
}
.ctrl-status-dot {
    width:10px; height:10px; border-radius:50%;
    flex-shrink:0;
}
.ctrl-status-dot.alive  { background:#00c853; box-shadow:0 0 8px #00c853; animation:pulse 1.2s infinite; }
.ctrl-status-dot.dead   { background:#e53935; box-shadow:0 0 6px #e53935; }
.ctrl-label-alive { color:#69f0ae; }
.ctrl-label-dead  { color:#ef9a9a; }
.ctrl-meta { color:#37474f; font-size:.65rem; margin-top:3px; }

/* section label */
.sec-label {
    font-family:'JetBrains Mono',monospace; font-size:.63rem; color:#1a2e4a;
    letter-spacing:3px; text-transform:uppercase;
    border-bottom:1px solid #080e1a; padding-bottom:7px; margin:26px 0 14px;
    display:flex; align-items:center; gap:10px;
}
.sec-label::before { content:'▶'; color:#1565c0; font-size:.55rem; }

/* KPI grid */
.kpi-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:4px; }
.kpi-card {
    background:#060c15; border:1px solid #0a1628;
    border-radius:10px; padding:18px 18px 14px; position:relative; overflow:hidden;
}
.kpi-card::after { content:''; position:absolute; bottom:0; left:0; right:0; height:2px; }
.kpi-card.blue::after   { background:linear-gradient(90deg,transparent,#1565c0,transparent); }
.kpi-card.green::after  { background:linear-gradient(90deg,transparent,#2e7d32,transparent); }
.kpi-card.red::after    { background:linear-gradient(90deg,transparent,#c62828,transparent); }
.kpi-card.amber::after  { background:linear-gradient(90deg,transparent,#f57f17,transparent); }
.kpi-card.teal::after   { background:linear-gradient(90deg,transparent,#00695c,transparent); }
.kpi-label { font-family:'JetBrains Mono',monospace; font-size:.58rem; color:#1a2e4a;
             letter-spacing:2px; text-transform:uppercase; margin-bottom:8px; }
.kpi-value { font-family:'Exo 2',sans-serif; font-weight:900; font-size:2.2rem; line-height:1; margin-bottom:5px; }
.kpi-value.blue  { color:#42a5f5; text-shadow:0 0 18px rgba(66,165,245,.35); }
.kpi-value.green { color:#66bb6a; text-shadow:0 0 18px rgba(102,187,106,.3); }
.kpi-value.red   { color:#ef5350; text-shadow:0 0 18px rgba(239,83,80,.35); }
.kpi-value.amber { color:#ffca28; text-shadow:0 0 18px rgba(255,202,40,.3); }
.kpi-value.teal  { color:#4db6ac; text-shadow:0 0 18px rgba(77,182,172,.3); }
.kpi-sub { font-family:'JetBrains Mono',monospace; font-size:.6rem; color:#2d4a6b; }

/* pool bar */
.pool-wrap { background:#060c15; border:1px solid #0a1628; border-radius:10px; padding:18px 22px; }
.pool-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.pool-title  { font-family:'JetBrains Mono',monospace; font-size:.62rem; color:#1a2e4a; letter-spacing:2px; text-transform:uppercase; }
.pool-nums   { font-family:'Exo 2',sans-serif; font-weight:900; font-size:1.4rem; }
.pool-bar-bg { height:14px; background:#080e1a; border-radius:7px; overflow:hidden; position:relative; }
.pool-bar-used  { position:absolute; left:0; top:0; height:100%; border-radius:7px;
                   background:linear-gradient(90deg,#c62828,#e53935,#ff7043);
                   box-shadow:0 0 10px rgba(229,57,53,.5); transition:width .6s ease; }
.pool-bar-avail { position:absolute; right:0; top:0; height:100%; border-radius:7px;
                   background:linear-gradient(90deg,#1b5e20,#2e7d32,#43a047);
                   box-shadow:0 0 10px rgba(67,160,71,.3); transition:width .6s ease; }
.pool-legend { display:flex; gap:18px; margin-top:8px; font-family:'JetBrains Mono',monospace; font-size:.6rem; }
.pool-dot { display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:5px; }

/* defense grid */
.def-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.def-card {
    background:#060c15; border:1px solid #0a1628; border-radius:8px;
    padding:12px 16px; display:flex; align-items:center; gap:12px;
}
.def-icon { font-size:1.1rem; }
.def-info { flex:1; }
.def-name { font-family:'JetBrains Mono',monospace; font-size:.65rem; color:#2d4a6b;
            text-transform:uppercase; letter-spacing:1px; }
.def-stat { font-family:'Exo 2',sans-serif; font-weight:700; font-size:.95rem; margin-top:2px; }
.def-stat.on  { color:#66bb6a; }
.def-stat.off { color:#ef5350; }

/* lease table */
.lease-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:.72rem; }
.lease-table th { color:#1a2e4a; text-transform:uppercase; letter-spacing:2px; font-size:.58rem;
                  padding:8px 14px; border-bottom:1px solid #0a1628; text-align:left; font-weight:400; }
.lease-table td { padding:8px 14px; border-bottom:1px solid #060c15; vertical-align:middle; }
.lease-table tr:hover td { background:#060c15; }
.lease-table .mac-col  { color:#7986cb; }
.lease-table .ip-col   { color:#4db6ac; }
.lease-table .evt-col  { }
.t-badge {
    display:inline-block; padding:1px 9px; border-radius:10px;
    font-size:.58rem; font-weight:700; letter-spacing:1px;
}
.t-badge.discover { background:rgba(66,165,245,.1);  color:#42a5f5;  border:1px solid rgba(66,165,245,.2); }
.t-badge.offer    { background:rgba(255,202,40,.1);  color:#ffca28;  border:1px solid rgba(255,202,40,.2); }
.t-badge.request  { background:rgba(126,87,194,.1);  color:#ce93d8;  border:1px solid rgba(126,87,194,.2); }
.t-badge.ack      { background:rgba(46,125,50,.12);  color:#a5d6a7;  border:1px solid rgba(46,125,50,.25); }
.t-badge.nak      { background:rgba(229,57,53,.1);   color:#ef9a9a;  border:1px solid rgba(229,57,53,.2); }
.t-badge.release  { background:rgba(84,110,122,.1);  color:#90a4ae;  border:1px solid rgba(84,110,122,.2); }
.t-badge.binding  { background:rgba(0,105,92,.12);   color:#80cbc4;  border:1px solid rgba(0,105,92,.25); }
.t-badge.violation{ background:rgba(229,57,53,.12);  color:#ff8a80;  border:1px solid rgba(229,57,53,.3); }
.t-badge.snooping { background:rgba(245,127,23,.1);  color:#ffe082;  border:1px solid rgba(245,127,23,.2); }

/* active leases */
.lease-entry {
    display:flex; align-items:center; gap:12px;
    background:#060c15; border:1px solid #0a1628; border-radius:8px;
    padding:10px 16px; margin-bottom:6px;
    font-family:'JetBrains Mono',monospace; font-size:.72rem;
}
.lease-entry .arrow { color:#1565c0; font-size:1rem; }
.lease-mac { color:#7986cb; }
.lease-ip  { color:#4db6ac; font-weight:700; }

/* violation alert */
.alert-box {
    background:rgba(229,57,53,.06); border:1px solid rgba(229,57,53,.25);
    border-radius:8px; padding:12px 16px; margin-bottom:8px;
    font-family:'JetBrains Mono',monospace; font-size:.7rem; color:#ef9a9a;
}
.alert-title { color:#e53935; font-weight:700; font-size:.72rem; margin-bottom:4px; letter-spacing:1px; }

/* log stream */
.log-wrap { background:#020408; border:1px solid #0a1628; border-radius:10px;
            padding:14px 16px; height:340px; overflow-y:auto; }
.log-line  { padding:2px 0; font-family:'JetBrains Mono',monospace;
             font-size:.67rem; line-height:1.8; white-space:pre-wrap; word-break:break-all; }
.ll-ts   { color:#141e2e; }
.ll-rx   { color:#1565c0; }
.ll-offer{ color:#f9a825; }
.ll-ack  { color:#2e7d32; }
.ll-nak  { color:#b71c1c; }
.ll-warn { color:#b71c1c; }
.ll-snoop{ color:#00695c; }
.ll-pool { color:#37474f; }
.ll-info { color:#1a2a3a; }

/* session info */
.sess-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }
.sess-row  { display:flex; justify-content:space-between; align-items:center;
             padding:9px 14px; background:#060c15; border:1px solid #0a1628;
             border-radius:6px; font-family:'JetBrains Mono',monospace; font-size:.7rem; }
.sess-key  { color:#1a2e4a; text-transform:uppercase; letter-spacing:1px; font-size:.6rem; }
.sess-val  { color:#80cbc4; }

#MainMenu,footer,header,[data-testid="stToolbar"] { visibility:hidden; }
div[data-testid="stDecoration"] { display:none; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# PARSER
# ══════════════════════════════════════════════════════════════════

_ANSI = re.compile(r'\x1b?\[[\d;]*m|\[[\d;]*m')

P = {
    'TS':          re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'),
    'START':       re.compile(r'DHCP Server starting on (\S+)\s+\(([\da-f:]+)\)'),
    'POOL_DEF':    re.compile(r'Pool:\s+([\d.]+)\s+[–\-]+\s+([\d.]+)\s+\((\d+) IPs\)'),
    'SCENARIO':    re.compile(r'SCENARIO\s*:\s*(?:\[[\d;]*m)?(\w+)'),
    'IPS_MAST':    re.compile(r'IPS \(master\)\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'RATE_LIM':    re.compile(r'Rate limiting\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'STARV_DET':   re.compile(r'Starvation detection\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'BLOCKLIST':   re.compile(r'MAC/IP block-list\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'POOL_GUARD':  re.compile(r'Pool exhaustion guard\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'SNOOP_MAST':  re.compile(r'DHCP Snooping \(master\)\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'ROGUE_DET':   re.compile(r'Rogue server detection\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'BIND_ENF':    re.compile(r'Binding enforcement\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'AUTO_BLOCK':  re.compile(r'Auto-block rogue IP\s+:\s+(?:\[[\d;]*m)?(ON|OFF)'),
    'POOL_AVAIL':  re.compile(r'Pool available:\s+(\d+)\s*/\s*(\d+)'),
    'LEASES_CNT':  re.compile(r'Active leases\s+:\s+(\d+)'),
    'SNOOP_TBL':   re.compile(r'Snooping table:\s+(\d+) bindings'),
    'SNOOP_LOAD':  re.compile(r'\[SNOOPING\] Loaded (\d+) existing bindings'),
    'RX':          re.compile(r'\[RX\]\s+(\w+)\s+src_mac=([\da-f:]+)\s+src_ip=([\d.]+)\s+pool_left=(\d+)'),
    'OFFER_TX':    re.compile(r'\[OFFER\]\s+──▶\s+mac=([\da-f:]+)\s+ip=([\d.]+)\s+pool_remaining=(\d+)/(\d+)'),
    'ACK_TX':      re.compile(r'\[ACK\]\s+──▶\s+mac=([\da-f:]+)\s+ip=([\d.]+)\s+pool_remaining=(\d+)/(\d+)'),
    'NAK_TX':      re.compile(r'\[NAK\]\s+──▶'),
    'BIND_ADD':    re.compile(r'\[SNOOPING\] Binding added:\s+([\da-f:]+)\s+→\s+([\d.]+)'),
    'BIND_VIOL':   re.compile(r'\[SNOOPING\] Binding violation:\s+([\da-f:]+) has ([\d.]+) but requested ([\d.]+)'),
    'LEASE_ENTRY': re.compile(r'DHCP-SERVER\s+([\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2})\s+→\s+([\d.]+)'),
    'EXPIRE':      re.compile(r'\[EXPIRE\] lease ([\d.]+) \(([\da-f:]+)\)'),
    'RELEASE':     re.compile(r'\[RELEASE\] ([\da-f:]+) released ([\d.]+)'),
    'BLOCKED_MAC': re.compile(r'\[IPS\] MAC ([\da-f:]+) added to block-list'),
    'BLOCKED_IP':  re.compile(r'\[IPS\] IP ([\d.]+) added to block-list'),
    'RATE_EXC':    re.compile(r'\[IPS\] Rate limit exceeded for MAC ([\da-f:]+)'),
    'STARV_DET2':  re.compile(r'\[IPS\] STARVATION DETECTED'),
    'ROGUE_DET2':  re.compile(r'\[SNOOPING\] ROGUE DHCP SERVER DETECTED.*?from ([\d.]+)'),
}

# ══════════════════════════════════════════════════════════════════
# PROCESS MANAGEMENT  —  stored in st.session_state
# ══════════════════════════════════════════════════════════════════

def get_proc() -> subprocess.Popen | None:
    return st.session_state.get("starvation_proc", None)

def is_running() -> bool:
    proc = get_proc()
    if proc is None:
        return False
    return proc.poll() is None   # None means still alive

def start_attack(log_path: str):
    if is_running():
        return
    log_file = open(log_path, "w")          # append so we don't lose history
    proc = subprocess.Popen(
        ["sudo", "python3", "server.py"],
        stdout=log_file,
        stderr=subprocess.STDOUT,           # merge stderr → same log
        preexec_fn=os.setsid,               # own process group → clean kill
    )
    st.session_state["starvation_proc"]     = proc
    st.session_state["starvation_log_file"] = log_file
    st.session_state["starvation_started"]  = datetime.now().strftime("%H:%M:%S")

def stop_attack():
    proc = get_proc()
    if proc is None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)   # kill whole group
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    lf = st.session_state.get("starvation_log_file")
    if lf:
        try:
            lf.close()
        except Exception:
            pass
    st.session_state.pop("starvation_proc",     None)
    st.session_state.pop("starvation_log_file", None)
    st.session_state.pop("starvation_started",  None)



def parse_log(path: str) -> dict:
    d = dict(
        # session
        interface='—', server_mac='—', pool_start='—', pool_end='—',
        pool_total=0, scenario='UNKNOWN', started_at='—',
        # defenses
        ips_master='OFF', rate_limit='OFF', starv_detect='OFF',
        blocklist='OFF', pool_guard='OFF',
        snoop_master='OFF', rogue_detect='OFF', bind_enforce='OFF',
        auto_block='OFF',
        # live counters (latest status snapshot)
        pool_available=0, pool_used=0,
        active_leases=0, snoop_bindings=0,
        # packet counters
        rx_discover=0, rx_request=0, rx_offer=0, rx_ack=0, rx_nak=0, rx_release=0,
        tx_offer=0, tx_ack=0, tx_nak=0,
        # events list for timeline
        events=[],
        # current leases from latest snapshot
        current_leases={},     # mac → ip
        # security events
        bind_violations=[],
        blocked_macs=[], blocked_ips=[],
        rate_exceeded=[], starv_alerts=0, rogue_alerts=[],
        # pool history for chart [{ts, avail, used}]
        pool_history=[],
        # packet flow history [{ts, discover, offer, request, ack}]
        pkt_history=[],
        # raw lines
        raw_lines=[],
    )

    if not os.path.exists(path):
        return d

    try:
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        return d

    d['raw_lines'] = lines

    # track running totals for pool history
    _snapshot_avail = None
    _snapshot_total = None

    for line in lines:
        c = _ANSI.sub('', line)
        ts_m = P['TS'].match(c.strip())
        ts = ts_m.group(1) if ts_m else ''

        # ── session init ──
        m = P['START'].search(c)
        if m:
            d['interface']  = m.group(1)
            d['server_mac'] = m.group(2)
            d['started_at'] = ts

        m = P['POOL_DEF'].search(c)
        if m:
            d['pool_start'] = m.group(1)
            d['pool_end']   = m.group(2)
            d['pool_total'] = int(m.group(3))

        m = P['SCENARIO'].search(c)
        if m:
            d['scenario'] = m.group(1)

        # ── defense flags ──
        for key, pkey in [
            ('ips_master','IPS_MAST'),('rate_limit','RATE_LIM'),
            ('starv_detect','STARV_DET'),('blocklist','BLOCKLIST'),
            ('pool_guard','POOL_GUARD'),('snoop_master','SNOOP_MAST'),
            ('rogue_detect','ROGUE_DET'),('bind_enforce','BIND_ENF'),
            ('auto_block','AUTO_BLOCK'),
        ]:
            m = P[pkey].search(c)
            if m:
                d[key] = m.group(1)

        # ── pool snapshots ──
        m = P['POOL_AVAIL'].search(c)
        if m:
            avail = int(m.group(1))
            total = int(m.group(2))
            d['pool_available'] = avail
            d['pool_total']     = max(d['pool_total'], total)
            d['pool_used']      = total - avail
            if ts:
                d['pool_history'].append(dict(ts=ts, avail=avail, used=total - avail, total=total))

        m = P['LEASES_CNT'].search(c)
        if m:
            d['active_leases'] = int(m.group(1))

        m = P['SNOOP_TBL'].search(c)
        if m:
            d['snoop_bindings'] = int(m.group(1))

        # ── live lease entries from status snapshots ──
        m = P['LEASE_ENTRY'].search(c)
        if m:
            d['current_leases'][m.group(1)] = m.group(2)

        # ── RX packets ──
        m = P['RX'].search(c)
        if m:
            ptype = m.group(1).lower()
            mac   = m.group(2)
            src   = m.group(3)
            pleft = int(m.group(4))
            if ptype == 'discover': d['rx_discover'] += 1
            elif ptype == 'request': d['rx_request'] += 1
            elif ptype == 'offer':   d['rx_offer']   += 1
            elif ptype == 'ack':     d['rx_ack']      += 1
            elif ptype == 'nak':     d['rx_nak']      += 1
            elif ptype == 'release': d['rx_release']  += 1
            d['events'].append(dict(ts=ts, kind='RX-'+ptype.upper(),
                                    mac=mac, ip=src, extra=f'pool_left={pleft}'))
            continue

        # ── TX OFFER ──
        m = P['OFFER_TX'].search(c)
        if m:
            d['tx_offer'] += 1
            d['events'].append(dict(ts=ts, kind='TX-OFFER',
                                    mac=m.group(1), ip=m.group(2),
                                    extra=f'pool={m.group(3)}/{m.group(4)}'))
            continue

        # ── TX ACK ──
        m = P['ACK_TX'].search(c)
        if m:
            d['tx_ack'] += 1
            d['events'].append(dict(ts=ts, kind='TX-ACK',
                                    mac=m.group(1), ip=m.group(2),
                                    extra=f'pool={m.group(3)}/{m.group(4)}'))
            continue

        # ── Binding added ──
        m = P['BIND_ADD'].search(c)
        if m:
            d['events'].append(dict(ts=ts, kind='BINDING',
                                    mac=m.group(1), ip=m.group(2), extra='added'))
            continue

        # ── Binding violation ──
        m = P['BIND_VIOL'].search(c)
        if m:
            d['bind_violations'].append(dict(ts=ts, mac=m.group(1),
                                             expected=m.group(2), requested=m.group(3)))
            d['events'].append(dict(ts=ts, kind='VIOLATION',
                                    mac=m.group(1), ip=m.group(3),
                                    extra=f'expected={m.group(2)}'))
            continue

        # ── security events ──
        m = P['BLOCKED_MAC'].search(c)
        if m and m.group(1) not in d['blocked_macs']:
            d['blocked_macs'].append(m.group(1))

        m = P['BLOCKED_IP'].search(c)
        if m and m.group(1) not in d['blocked_ips']:
            d['blocked_ips'].append(m.group(1))

        m = P['RATE_EXC'].search(c)
        if m:
            d['rate_exceeded'].append(dict(ts=ts, mac=m.group(1)))

        m = P['STARV_DET2'].search(c)
        if m:
            d['starv_alerts'] += 1

        m = P['ROGUE_DET2'].search(c)
        if m:
            d['rogue_alerts'].append(dict(ts=ts, ip=m.group(1)))

    # pool used = total - available
    if d['pool_total'] and d['pool_available']:
        d['pool_used'] = d['pool_total'] - d['pool_available']

    return d


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def flag_html(val: str) -> str:
    if val == 'ON':
        return '<span class="def-stat on">● ON</span>'
    return '<span class="def-stat off">○ OFF</span>'


def badge(kind: str) -> str:
    kind_l = kind.lower()
    cls = 'discover'
    if 'offer'    in kind_l: cls = 'offer'
    elif 'request' in kind_l: cls = 'request'
    elif 'ack'     in kind_l: cls = 'ack'
    elif 'nak'     in kind_l: cls = 'nak'
    elif 'release' in kind_l: cls = 'release'
    elif 'binding' in kind_l: cls = 'binding'
    elif 'violation' in kind_l: cls = 'violation'
    elif 'snooping' in kind_l: cls = 'snooping'
    label = kind.replace('RX-','').replace('TX-','')
    return f'<span class="t-badge {cls}">{label}</span>'


# ══════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════

_L = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='JetBrains Mono', color='#2d4a6b', size=10),
    margin=dict(l=48, r=16, t=36, b=44),
    xaxis=dict(gridcolor='#080e1a', zerolinecolor='#080e1a'),
    yaxis=dict(gridcolor='#080e1a', zerolinecolor='#080e1a'),
    legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=9)),
)


# def chart_pool_history(data):
#     ph = data['pool_history']
#     fig = go.Figure()
#     if ph:
#         df = pd.DataFrame(ph)
#         fig.add_trace(go.Scatter(
#             x=df['ts'], y=df['avail'],
#             mode='lines', name='Available',
#             line=dict(color='#43a047', width=2),
#             fill='tozeroy', fillcolor='rgba(67,160,71,0.07)',
#         ))
#         fig.add_trace(go.Scatter(
#             x=df['ts'], y=df['used'],
#             mode='lines', name='Used',
#             line=dict(color='#e53935', width=2, dash='dot'),
#         ))
#     fig.update_layout(
#         **_L,
#         title=dict(text='POOL AVAILABILITY OVER TIME', font=dict(size=11, color='#1a2e4a'), x=0),
#         yaxis_title='IPs', xaxis_title='snapshot time', height=240,
#         xaxis=dict(**_L['xaxis'], tickangle=-25, tickfont=dict(size=8)),
#     )
#     return fig
def chart_pool_history(data):
    ph = data['pool_history']
    fig = go.Figure()

    if ph:
        df = pd.DataFrame(ph)
        fig.add_trace(go.Scatter(
            x=df['ts'], y=df['avail'],
            mode='lines', name='Available',
            line=dict(color='#43a047', width=2),
            fill='tozeroy', fillcolor='rgba(67,160,71,0.07)',
        ))
        fig.add_trace(go.Scatter(
            x=df['ts'], y=df['used'],
            mode='lines', name='Used',
            line=dict(color='#e53935', width=2, dash='dot'),
        ))

    # ✅ FIX: do NOT override xaxis inside update_layout
    fig.update_layout(
        **_L,
        title=dict(text='POOL AVAILABILITY OVER TIME', font=dict(size=11, color='#1a2e4a'), x=0),
        yaxis_title='IPs',
        xaxis_title='snapshot time',
        height=240,
    )

    # ✅ apply xaxis config separately
    fig.update_xaxes(
        tickangle=-25,
        tickfont=dict(size=8)
    )

    return fig


# def chart_packet_counts(data):
#     cats   = ['DISCOVER','REQUEST','OFFER','ACK','NAK']
#     rx_vals = [data['rx_discover'], data['rx_request'], data['rx_offer'], data['rx_ack'], data['rx_nak']]
#     tx_vals = [0, 0, data['tx_offer'], data['tx_ack'], data['tx_nak']]
#     colors  = ['#42a5f5','#ce93d8','#ffca28','#66bb6a','#ef5350']

#     fig = go.Figure()
#     fig.add_trace(go.Bar(name='RX (seen)', x=cats, y=rx_vals,
#                          marker_color=[c+'88' for c in colors], marker_line_width=0))
#     fig.add_trace(go.Bar(name='TX (sent)', x=cats, y=tx_vals,
#                          marker_color=colors, marker_line_width=0))
#     fig.update_layout(
#         **_L, barmode='group',
#         title=dict(text='PACKET BREAKDOWN  ·  RX vs TX', font=dict(size=11, color='#1a2e4a'), x=0),
#         yaxis_title='count', height=240,
#     )
#     return fig
def chart_packet_counts(data):
    cats   = ['DISCOVER','REQUEST','OFFER','ACK','NAK']
    rx_vals = [
        data['rx_discover'],
        data['rx_request'],
        data['rx_offer'],
        data['rx_ack'],
        data['rx_nak']
    ]
    tx_vals = [
        0, 0,
        data['tx_offer'],
        data['tx_ack'],
        data['tx_nak']
    ]

    # Base colors (hex)
    colors = ['#42a5f5', '#ce93d8', '#ffca28', '#66bb6a', '#ef5350']

    # ✅ Convert to rgba with opacity
    def hex_to_rgba(hex_color, alpha):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f'rgba({r},{g},{b},{alpha})'

    rx_colors = [hex_to_rgba(c, 0.5) for c in colors]  # semi-transparent
    tx_colors = [hex_to_rgba(c, 1.0) for c in colors]  # solid

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='RX (seen)',
        x=cats,
        y=rx_vals,
        marker_color=rx_colors,
        marker_line_width=0
    ))

    fig.add_trace(go.Bar(
        name='TX (sent)',
        x=cats,
        y=tx_vals,
        marker_color=tx_colors,
        marker_line_width=0
    ))

    fig.update_layout(
        **_L,
        barmode='group',
        title=dict(text='PACKET BREAKDOWN  ·  RX vs TX',
                   font=dict(size=11, color='#1a2e4a'), x=0),
        yaxis_title='count',
        height=240,
    )

    return fig


# def chart_event_timeline(data):
#     """Scatter plot of events over time coloured by type."""
#     evts = data['events'][-200:]
#     if not evts:
#         fig = go.Figure()
#         fig.update_layout(**_L, title='EVENT TIMELINE (no data)', height=200)
#         return fig

#     type_color = {
#         'RX-DISCOVER': '#42a5f5','RX-REQUEST':'#ce93d8','RX-OFFER':'#ffca28',
#         'RX-ACK':'#66bb6a','RX-NAK':'#ef5350','TX-OFFER':'#f9a825',
#         'TX-ACK':'#2e7d32','BINDING':'#4db6ac','VIOLATION':'#e53935',
#     }
#     groups = {}
#     for i, e in enumerate(evts):
#         k = e['kind']
#         if k not in groups: groups[k] = {'x':[],'y':[],'text':[]}
#         groups[k]['x'].append(e['ts'])
#         groups[k]['y'].append(i)
#         groups[k]['text'].append(f"{e['mac']} | {e['ip']} | {e['extra']}")

#     fig = go.Figure()
#     for k, g in groups.items():
#         fig.add_trace(go.Scatter(
#             x=g['x'], y=g['y'], mode='markers', name=k,
#             marker=dict(size=7, color=type_color.get(k,'#546e7a'), opacity=0.85,
#                         line=dict(width=0)),
#             text=g['text'], hovertemplate='%{text}<extra>%{fullData.name}</extra>',
#         ))
#     fig.update_layout(
#         **_L,
#         title=dict(text='EVENT TIMELINE — all packet events', font=dict(size=11, color='#1a2e4a'), x=0),
#         yaxis_title='event #', xaxis_title='time',
#         height=260,
#         xaxis=dict(**_L['xaxis'], tickangle=-25, tickfont=dict(size=8)),
#     )
#     return fig

def chart_event_timeline(data):
    evts = data['events'][-200:]

    if not evts:
        fig = go.Figure()
        fig.update_layout(**_L, title='EVENT TIMELINE (no data)', height=200)
        return fig

    type_color = {
        'RX-DISCOVER': '#42a5f5',
        'RX-REQUEST': '#ce93d8',
        'RX-OFFER': '#ffca28',
        'RX-ACK': '#66bb6a',
        'RX-NAK': '#ef5350',
        'TX-OFFER': '#f9a825',
        'TX-ACK': '#2e7d32',
        'BINDING': '#4db6ac',
        'VIOLATION': '#e53935',
    }

    groups = {}
    for i, e in enumerate(evts):
        k = e['kind']
        if k not in groups:
            groups[k] = {'x': [], 'y': [], 'text': []}
        groups[k]['x'].append(e['ts'])
        groups[k]['y'].append(i)
        groups[k]['text'].append(f"{e['mac']} | {e['ip']} | {e['extra']}")

    fig = go.Figure()

    for k, g in groups.items():
        fig.add_trace(go.Scatter(
            x=g['x'],
            y=g['y'],
            mode='markers',
            name=k,
            marker=dict(
                size=7,
                color=type_color.get(k, '#546e7a'),
                opacity=0.85,
                line=dict(width=0)
            ),
            text=g['text'],
            hovertemplate='%{text}<extra>%{fullData.name}</extra>',
        ))

    # ✅ FIX HERE
    fig.update_layout(
        **_L,
        title=dict(text='EVENT TIMELINE — all packet events', font=dict(size=11, color='#1a2e4a'), x=0),
        yaxis_title='event #',
        xaxis_title='time',
        height=260,
    )

    # ✅ apply separately
    fig.update_xaxes(
        tickangle=-25,
        tickfont=dict(size=8)
    )

    return fig


# ══════════════════════════════════════════════════════════════════
# LOG STREAM
# ══════════════════════════════════════════════════════════════════

def render_log(lines):
    html = []
    for line in reversed(lines[-300:]):
        c = _ANSI.sub('', line).rstrip()
        if not c.strip():
            continue
        cls = 'll-info'
        cl  = c.lower()
        if '[rx]' in cl:
            if 'discover' in cl: cls = 'll-rx'
            elif 'request' in cl: cls = 'll-rx'
            elif 'offer'   in cl: cls = 'll-offer'
            elif 'ack'     in cl: cls = 'll-ack'
            elif 'nak'     in cl: cls = 'll-nak'
            else: cls = 'll-rx'
        elif '[offer]' in cl: cls = 'll-offer'
        elif '[ack]'   in cl: cls = 'll-ack'
        elif '[nak]'   in cl: cls = 'll-nak'
        elif '[warning' in cl or 'violation' in cl or 'rogue' in cl or 'blocked' in cl: cls = 'll-warn'
        elif '[snooping]' in cl or 'binding' in cl: cls = 'll-snoop'
        elif 'pool available' in cl or '====' in cl or '────' in cl: cls = 'll-pool'
        safe = c.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        html.append(f'<div class="log-line {cls}">{safe}</div>')
    return '<div class="log-wrap">' + '\n'.join(html) + '</div>'


# ══════════════════════════════════════════════════════════════════
# EVENT TABLE
# ══════════════════════════════════════════════════════════════════

def render_event_table(data, n=35):
    evts = data['events'][-n:]
    rows = []
    for e in reversed(evts):
        kind_tx = 'TX' if e['kind'].startswith('TX') else ('⚠' if 'VIOL' in e['kind'] else 'RX')
        direction = (
            '<span style="color:#ffca28">▲ TX</span>' if kind_tx == 'TX'
            else '<span style="color:#42a5f5">▼ RX</span>' if kind_tx == 'RX'
            else '<span style="color:#e53935">⚠ ALERT</span>'
        )
        rows.append(
            f'<tr>'
            f'<td><span style="color:#1a2e4a">{e["ts"]}</span></td>'
            f'<td>{direction}</td>'
            f'<td>{badge(e["kind"])}</td>'
            f'<td class="mac-col">{e["mac"]}</td>'
            f'<td class="ip-col">{e["ip"]}</td>'
            f'<td style="color:#2d4a6b">{e["extra"]}</td>'
            f'</tr>'
        )
    body = ''.join(rows) if rows else '<tr><td colspan="6" style="color:#1a2e4a;padding:14px">No events yet</td></tr>'
    return f"""
    <table class="lease-table">
      <thead><tr>
        <th>Timestamp</th><th>Dir</th><th>Type</th><th>MAC</th><th>IP</th><th>Extra</th>
      </tr></thead>
      <tbody>{body}</tbody>
    </table>"""


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════

def sidebar_ui(default_log):
    with st.sidebar:
        st.markdown("## 🛡 DHCP Server Monitor")
        st.markdown("---")
        log_path = st.text_input("Log file path", value=default_log)
        refresh  = st.slider("Auto-refresh (sec)", 1, 30, 3)
        live     = st.toggle("Live mode", value=True)
        st.markdown("---")
        st.markdown(
            "<small style='color:#1a2e4a;font-family:JetBrains Mono,monospace'>"
            "Reads the log produced by server.py<br>and visualises all DHCP activity<br>"
            "and security events in real-time.<br><br>"
            "⚠ Lab / educational use only.</small>",
            unsafe_allow_html=True)
    return log_path, refresh, live



# ══════════════════════════════════════════════════════════════════
# ATTACK CONTROL PANEL  (rendered in main body)
# ══════════════════════════════════════════════════════════════════

def render_control_panel(log_path: str):
    alive     = is_running()
    pid       = get_proc().pid if alive else None
    started   = st.session_state.get("starvation_started", "—")
    dot_class = "alive" if alive else "dead"
    lbl_class = "ctrl-label-alive" if alive else "ctrl-label-dead"
    status_txt = f"RUNNING  ·  PID {pid}  ·  started {started}" if alive else "STOPPED"

    st.markdown(f"""
    <div class="ctrl-panel">
        <div class="ctrl-status">
            <div class="ctrl-status-dot {dot_class}"></div>
            <div>
                <div class="{lbl_class}">server.py — {status_txt}</div>
                <div class="ctrl-meta">sudo python3 server.py 2&gt;&amp;1 | tee {log_path}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_start, col_stop, col_spacer = st.columns([1, 1, 5])

    with col_start:
        if st.button(
            "▶  START ATTACK",
            disabled=alive,
            use_container_width=True,
            type="primary",
        ):
            start_attack(log_path)
            st.rerun()

    with col_stop:
        if st.button(
            "■  STOP ATTACK",
            disabled=not alive,
            use_container_width=True,
            type="secondary",
        ):
            stop_attack()
            st.rerun()




# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--log", default="server.log")
    args, _ = parser.parse_known_args()

    log_path, refresh_sec, live_mode = sidebar_ui(args.log)
    data = parse_log(log_path)

    # ── HERO ──────────────────────────────────────────────────────
    file_ok = os.path.exists(log_path)
    scenario = data['scenario']
    scen_cls = 'vuln' if scenario == 'VULNERABLE' else ('prot' if scenario == 'PROTECTED' else 'part')
    scen_dot = 'red' if scenario == 'VULNERABLE' else 'green'
    status_color = '#ef9a9a' if not file_ok else '#64b5f6'

    st.markdown(f"""
    <div class="hero">
        <div class="hero-title">🛡 DHCP SERVER MONITOR</div>
        <div class="hero-sub">Real-time traffic analyser &amp; security event dashboard</div>
        <div class="hero-row">
            <div class="hero-pill live">
                <span class="pulse"></span>
                {'LIVE  ·  ' + log_path if file_ok else '⚠  FILE NOT FOUND  ·  ' + log_path}
            </div>
            <div class="hero-pill {scen_cls}">
                <span class="pulse {scen_dot}"></span>
                SCENARIO : {scenario}
            </div>
            <div class="hero-pill live">
                🖥  {data['interface']}  ·  {data['server_mac']}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ATTACK CONTROL PANEL ──────────────────────────────────────
    st.markdown('<div class="sec-label">ATTACK CONTROL</div>', unsafe_allow_html=True)
    render_control_panel(log_path)

    # ── KPI CARDS ─────────────────────────────────────────────────
    st.markdown('<div class="sec-label">KEY METRICS</div>', unsafe_allow_html=True)
    pool_pct = round(data['pool_used'] / max(data['pool_total'], 1) * 100, 1)
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card green">
            <div class="kpi-label">Pool Available</div>
            <div class="kpi-value green">{data['pool_available']}</div>
            <div class="kpi-sub">of {data['pool_total']} total IPs</div>
        </div>
        <div class="kpi-card red">
            <div class="kpi-label">Pool Used</div>
            <div class="kpi-value red">{data['pool_used']}</div>
            <div class="kpi-sub">{pool_pct}% consumed</div>
        </div>
        <div class="kpi-card blue">
            <div class="kpi-label">Active Leases</div>
            <div class="kpi-value blue">{data['active_leases']}</div>
            <div class="kpi-sub">confirmed clients</div>
        </div>
        <div class="kpi-card teal">
            <div class="kpi-label">Snoop Bindings</div>
            <div class="kpi-value teal">{data['snoop_bindings']}</div>
            <div class="kpi-sub">MAC↔IP entries</div>
        </div>
        <div class="kpi-card amber">
            <div class="kpi-label">Security Alerts</div>
            <div class="kpi-value amber">{len(data['bind_violations']) + data['starv_alerts'] + len(data['rogue_alerts'])}</div>
            <div class="kpi-sub">violations detected</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── POOL BAR ──────────────────────────────────────────────────
    st.markdown('<div class="sec-label">IP POOL STATUS</div>', unsafe_allow_html=True)
    used_pct  = min(pool_pct, 100)
    avail_pct = 100 - used_pct
    st.markdown(f"""
    <div class="pool-wrap">
        <div class="pool-header">
            <span class="pool-title">Pool  {data['pool_start']}  —  {data['pool_end']}</span>
            <span class="pool-nums" style="color:#ef5350">{data['pool_used']} used</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#1a2e4a">|</span>
            <span class="pool-nums" style="color:#66bb6a">{data['pool_available']} free</span>
        </div>
        <div class="pool-bar-bg">
            <div class="pool-bar-used"  style="width:{used_pct}%"></div>
            <div class="pool-bar-avail" style="width:{avail_pct}%; left:{used_pct}%"></div>
        </div>
        <div class="pool-legend">
            <span><span class="pool-dot" style="background:#e53935"></span><span style="color:#2d4a6b">Used ({used_pct}%)</span></span>
            <span><span class="pool-dot" style="background:#2e7d32"></span><span style="color:#2d4a6b">Available ({avail_pct}%)</span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── DEFENSE STATUS ────────────────────────────────────────────
    st.markdown('<div class="sec-label">DEFENSE STATUS</div>', unsafe_allow_html=True)
    defenses = [
        ("🔒", "IPS Master",          data['ips_master']),
        ("⏱", "Rate Limiting",        data['rate_limit']),
        ("🌊", "Starvation Detect",    data['starv_detect']),
        ("🚫", "MAC/IP Blocklist",     data['blocklist']),
        ("🛡", "Pool Guard",           data['pool_guard']),
        ("👁", "DHCP Snooping",        data['snoop_master']),
        ("🔍", "Rogue Detection",      data['rogue_detect']),
        ("📋", "Binding Enforcement",  data['bind_enforce']),
        ("⛔", "Auto-block Rogue",     data['auto_block']),
    ]
    cards = ''.join(f"""
        <div class="def-card">
            <div class="def-icon">{icon}</div>
            <div class="def-info">
                <div class="def-name">{name}</div>
                {flag_html(val)}
            </div>
        </div>""" for icon, name, val in defenses)
    st.markdown(f'<div class="def-grid">{cards}</div>', unsafe_allow_html=True)

    # ── SESSION INFO ──────────────────────────────────────────────
    st.markdown('<div class="sec-label">SESSION INFORMATION</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sess-grid">
        <div class="sess-row"><span class="sess-key">Interface</span><span class="sess-val">{data['interface']}</span></div>
        <div class="sess-row"><span class="sess-key">Server MAC</span><span class="sess-val">{data['server_mac']}</span></div>
        <div class="sess-row"><span class="sess-key">Started At</span><span class="sess-val">{data['started_at']}</span></div>
        <div class="sess-row"><span class="sess-key">Pool Range</span><span class="sess-val">{data['pool_start']} – {data['pool_end']}</span></div>
        <div class="sess-row"><span class="sess-key">Pool Size</span><span class="sess-val">{data['pool_total']} IPs</span></div>
        <div class="sess-row"><span class="sess-key">Scenario</span><span class="sess-val" style="color:{'#ef9a9a' if scenario=='VULNERABLE' else '#a5d6a7'}">{scenario}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── PACKET COUNTERS ───────────────────────────────────────────
    st.markdown('<div class="sec-label">PACKET COUNTERS</div>', unsafe_allow_html=True)
    total_rx = data['rx_discover'] + data['rx_request'] + data['rx_offer'] + data['rx_ack'] + data['rx_nak']
    total_tx = data['tx_offer'] + data['tx_ack'] + data['tx_nak']
    st.markdown(f"""
    <div class="sess-grid">
        <div class="sess-row"><span class="sess-key">RX DISCOVER</span><span class="sess-val" style="color:#42a5f5">{data['rx_discover']}</span></div>
        <div class="sess-row"><span class="sess-key">RX REQUEST</span><span class="sess-val" style="color:#ce93d8">{data['rx_request']}</span></div>
        <div class="sess-row"><span class="sess-key">RX OTHER</span><span class="sess-val" style="color:#546e7a">{data['rx_offer']+data['rx_ack']+data['rx_nak']}</span></div>
        <div class="sess-row"><span class="sess-key">TX OFFER</span><span class="sess-val" style="color:#ffca28">{data['tx_offer']}</span></div>
        <div class="sess-row"><span class="sess-key">TX ACK</span><span class="sess-val" style="color:#66bb6a">{data['tx_ack']}</span></div>
        <div class="sess-row"><span class="sess-key">TX NAK</span><span class="sess-val" style="color:#ef5350">{data['tx_nak']}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── CHARTS ────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">LIVE CHARTS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_pool_history(data),   use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(chart_packet_counts(data),  use_container_width=True, config={"displayModeBar": False})
    st.plotly_chart(chart_event_timeline(data), use_container_width=True, config={"displayModeBar": False})

    # ── SECURITY ALERTS ───────────────────────────────────────────
    has_alerts = (data['bind_violations'] or data['starv_alerts'] or
                  data['rogue_alerts'] or data['blocked_macs'] or data['rate_exceeded'])
    if has_alerts:
        st.markdown('<div class="sec-label">⚠ SECURITY ALERTS</div>', unsafe_allow_html=True)
        for v in data['bind_violations']:
            st.markdown(f"""<div class="alert-box">
                <div class="alert-title">⚠ SNOOPING — BINDING VIOLATION</div>
                {v['ts']}  ·  MAC <b>{v['mac']}</b> has binding <b>{v['expected']}</b> but requested <b>{v['requested']}</b>
            </div>""", unsafe_allow_html=True)
        for r in data['rogue_alerts']:
            st.markdown(f"""<div class="alert-box">
                <div class="alert-title">🚨 ROGUE DHCP SERVER DETECTED</div>
                {r['ts']}  ·  Untrusted OFFER/ACK from <b>{r['ip']}</b>
            </div>""", unsafe_allow_html=True)
        if data['starv_alerts']:
            st.markdown(f"""<div class="alert-box">
                <div class="alert-title">🌊 STARVATION ATTACK DETECTED</div>
                {data['starv_alerts']} starvation pattern(s) triggered during this session
            </div>""", unsafe_allow_html=True)
        for m in data['blocked_macs']:
            st.markdown(f"""<div class="alert-box">
                <div class="alert-title">🚫 MAC BLOCKED</div>
                MAC <b>{m}</b> added to IPS block-list
            </div>""", unsafe_allow_html=True)

    # ── ACTIVE LEASES ─────────────────────────────────────────────
    if data['current_leases']:
        st.markdown('<div class="sec-label">ACTIVE LEASES</div>', unsafe_allow_html=True)
        for mac, ip in data['current_leases'].items():
            st.markdown(f"""
            <div class="lease-entry">
                <span class="lease-mac">{mac}</span>
                <span class="arrow">→</span>
                <span class="lease-ip">{ip}</span>
            </div>""", unsafe_allow_html=True)

    # ── EVENT TABLE ───────────────────────────────────────────────
    st.markdown('<div class="sec-label">EVENT TIMELINE  (last 35)</div>', unsafe_allow_html=True)
    st.markdown(render_event_table(data), unsafe_allow_html=True)

    # ── RAW LOG ───────────────────────────────────────────────────
    st.markdown('<div class="sec-label">RAW LOG STREAM  (newest first)</div>', unsafe_allow_html=True)
    st.markdown(render_log(data['raw_lines']), unsafe_allow_html=True)

    # ── AUTO REFRESH ──────────────────────────────────────────────
    if live_mode:
        time.sleep(refresh_sec)
        st.rerun()


if __name__ == '__main__':
    main()
