# #!/usr/bin/env python3
# """
# dashboard.py  —  DHCP Starvation Live Dashboard
# ================================================
# Usage:
#     streamlit run dashboard.py -- --log starvation.log
# """

# import re, os, time, argparse
# from datetime import datetime
# from pathlib import Path

# import streamlit as st
# import plotly.graph_objects as go
# import pandas as pd

# # ══════════════════════════════════════════════════════════════════
# # PAGE CONFIG
# # ══════════════════════════════════════════════════════════════════
# st.set_page_config(
#     page_title="DHCP Starvation Monitor",
#     page_icon="☠",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # ══════════════════════════════════════════════════════════════════
# # GLOBAL CSS
# # ══════════════════════════════════════════════════════════════════
# st.markdown("""
# <style>
# @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Exo+2:wght@300;600;900&display=swap');

# /* ── reset & base ── */
# html, body, [class*="css"]  { background:#05080d !important; color:#b0bec5; }
# *, *::before, *::after      { box-sizing:border-box; }

# /* ── sidebar ── */
# section[data-testid="stSidebar"] {
#     background:#080c13 !important;
#     border-right:1px solid #0e1822;
# }
# section[data-testid="stSidebar"] label,
# section[data-testid="stSidebar"] p,
# section[data-testid="stSidebar"] span { color:#546e7a !important; font-family:'JetBrains Mono',monospace !important; font-size:0.72rem !important; }
# section[data-testid="stSidebar"] h1,
# section[data-testid="stSidebar"] h2   { color:#e53935 !important; font-family:'Exo 2',sans-serif !important; }

# /* ── hero header ── */
# .hero {
#     position:relative; padding:28px 32px 20px;
#     background:linear-gradient(135deg,#0a0f1a 0%,#0d1520 60%,#120a0a 100%);
#     border:1px solid #1a2332; border-radius:12px;
#     margin-bottom:28px; overflow:hidden;
# }
# .hero::before {
#     content:''; position:absolute; inset:0;
#     background:radial-gradient(ellipse 60% 80% at 80% 50%, rgba(229,57,53,.07) 0%, transparent 70%);
# }
# .hero-title {
#     font-family:'Exo 2',sans-serif; font-weight:900;
#     font-size:2.1rem; letter-spacing:5px; text-transform:uppercase;
#     color:#e53935; text-shadow:0 0 30px rgba(229,57,53,.5);
#     margin:0 0 4px;
# }
# .hero-sub {
#     font-family:'JetBrains Mono',monospace; font-size:.7rem;
#     color:#37474f; letter-spacing:3px; text-transform:uppercase;
# }
# .hero-badge {
#     display:inline-flex; align-items:center; gap:8px;
#     background:rgba(229,57,53,.08); border:1px solid rgba(229,57,53,.2);
#     border-radius:20px; padding:4px 14px; margin-top:14px;
#     font-family:'JetBrains Mono',monospace; font-size:.7rem; color:#e57373;
# }
# .pulse { width:8px; height:8px; border-radius:50%; background:#e53935;
#          box-shadow:0 0 6px #e53935; animation:pulse 1.4s ease-in-out infinite; }
# @keyframes pulse { 0%,100%{opacity:1}50%{opacity:.2} }

# /* ── section labels ── */
# .sec-label {
#     font-family:'JetBrains Mono',monospace; font-size:.65rem;
#     color:#37474f; letter-spacing:3px; text-transform:uppercase;
#     border-bottom:1px solid #0e1822; padding-bottom:8px; margin:28px 0 14px;
#     display:flex; align-items:center; gap:10px;
# }
# .sec-label::before { content:'▶'; color:#e53935; font-size:.55rem; }

# /* ── metric cards ── */
# .kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:4px; }
# .kpi-card {
#     background:#080c13; border:1px solid #0e1822;
#     border-radius:10px; padding:20px 22px 16px;
#     position:relative; overflow:hidden;
#     transition:border-color .25s;
# }
# .kpi-card:hover { border-color:#1a2332; }
# .kpi-card::after {
#     content:''; position:absolute; bottom:0; left:0; right:0; height:2px;
# }
# .kpi-card.red::after   { background:linear-gradient(90deg,transparent,#e53935,transparent); }
# .kpi-card.blue::after  { background:linear-gradient(90deg,transparent,#1565c0,transparent); }
# .kpi-card.amber::after { background:linear-gradient(90deg,transparent,#f57f17,transparent); }
# .kpi-card.teal::after  { background:linear-gradient(90deg,transparent,#00695c,transparent); }

# .kpi-label { font-family:'JetBrains Mono',monospace; font-size:.62rem;
#              color:#37474f; letter-spacing:2px; text-transform:uppercase; margin-bottom:10px; }
# .kpi-value { font-family:'Exo 2',sans-serif; font-weight:900; font-size:2.4rem;
#              line-height:1; margin-bottom:6px; }
# .kpi-value.red   { color:#e53935; text-shadow:0 0 20px rgba(229,57,53,.4); }
# .kpi-value.blue  { color:#42a5f5; text-shadow:0 0 20px rgba(66,165,245,.3); }
# .kpi-value.amber { color:#ffca28; text-shadow:0 0 20px rgba(255,202,40,.3); }
# .kpi-value.teal  { color:#4db6ac; text-shadow:0 0 20px rgba(77,182,172,.3); }
# .kpi-sub  { font-family:'JetBrains Mono',monospace; font-size:.62rem; color:#546e7a; }

# /* ── progress bar ── */
# .pool-bar-wrap { background:#080c13; border:1px solid #0e1822; border-radius:10px; padding:20px 24px; }
# .pool-bar-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
# .pool-bar-title  { font-family:'JetBrains Mono',monospace; font-size:.65rem; color:#37474f; letter-spacing:2px; text-transform:uppercase; }
# .pool-bar-pct    { font-family:'Exo 2',sans-serif; font-weight:900; font-size:1.6rem; color:#e53935; }
# .pool-bar-bg     { height:12px; background:#0e1822; border-radius:6px; overflow:hidden; }
# .pool-bar-fill   { height:100%; border-radius:6px;
#                    background:linear-gradient(90deg,#b71c1c,#e53935,#ff7043);
#                    box-shadow:0 0 12px rgba(229,57,53,.6);
#                    transition:width .6s ease; }
# .pool-bar-sub    { display:flex; justify-content:space-between; margin-top:8px;
#                    font-family:'JetBrains Mono',monospace; font-size:.6rem; color:#546e7a; }

# /* ── timeline table ── */
# .tl-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:.72rem; }
# .tl-table th { color:#37474f; text-transform:uppercase; letter-spacing:2px;
#                font-size:.6rem; padding:8px 12px; border-bottom:1px solid #0e1822;
#                text-align:left; font-weight:400; }
# .tl-table td { padding:7px 12px; border-bottom:1px solid #080c13; vertical-align:middle; }
# .tl-table tr:hover td { background:#080c13; }
# .tl-table .ts   { color:#37474f; font-size:.65rem; }
# .tl-table .evt-offer { color:#ffca28; }
# .tl-table .evt-tx    { color:#42a5f5; }
# .tl-table .ip        { color:#4db6ac; }
# .tl-table .mac       { color:#7986cb; }
# .tl-table .num       { color:#e57373; font-weight:700; }
# .tl-badge {
#     display:inline-block; padding:1px 8px; border-radius:10px; font-size:.6rem;
#     font-weight:700; letter-spacing:1px;
# }
# .tl-badge.offer { background:rgba(255,202,40,.12); color:#ffca28; border:1px solid rgba(255,202,40,.2); }
# .tl-badge.tx    { background:rgba(66,165,245,.12);  color:#42a5f5; border:1px solid rgba(66,165,245,.2); }

# /* ── IP grid ── */
# .ip-grid { display:flex; flex-wrap:wrap; gap:8px; }
# .ip-tile {
#     background:#080c13; border:1px solid rgba(229,57,53,.2);
#     border-radius:6px; padding:6px 12px;
#     font-family:'JetBrains Mono',monospace; font-size:.7rem; color:#ef9a9a;
#     position:relative;
# }
# .ip-tile::before { content:'●'; color:#e53935; font-size:.5rem;
#                    margin-right:6px; vertical-align:middle; }

# /* ── session info ── */
# .sess-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
# .sess-row  { display:flex; justify-content:space-between; align-items:center;
#              padding:9px 14px; background:#080c13; border:1px solid #0e1822;
#              border-radius:6px; font-family:'JetBrains Mono',monospace; font-size:.7rem; }
# .sess-key  { color:#37474f; text-transform:uppercase; letter-spacing:1px; font-size:.62rem; }
# .sess-val  { color:#80cbc4; }

# /* ── log stream ── */
# .log-wrap  { background:#030507; border:1px solid #0e1822; border-radius:10px;
#              padding:14px 16px; height:320px; overflow-y:auto; }
# .log-line  { padding:2px 0; font-family:'JetBrains Mono',monospace;
#              font-size:.68rem; line-height:1.75; white-space:pre-wrap; word-break:break-all; }
# .log-ts    { color:#263238; }
# .log-lvl-w { color:#b71c1c; }
# .log-lvl-i { color:#1b5e20; }
# .log-offer { color:#f9a825; }
# .log-tx    { color:#1565c0; }
# .log-sum   { color:#4a148c; }
# .log-info  { color:#455a64; }

# /* hide streamlit chrome */
# #MainMenu,footer,header,[data-testid="stToolbar"] { visibility:hidden; }
# div[data-testid="stDecoration"] { display:none; }
# </style>
# """, unsafe_allow_html=True)


# # ══════════════════════════════════════════════════════════════════
# # PARSER  —  tuned to the exact log format from starvation.py
# # ══════════════════════════════════════════════════════════════════

# # strip ANSI escape codes  (e.g. [93m … [0m)
# _ANSI = re.compile(r'\x1b?\[\d+m|\[\d+m')

# # timestamp prefix  2026-04-12 10:09:05
# _TS = re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})')

# # log level
# _LVL = re.compile(r'\[(WARNING|INFO)\s*\]')

# # OFFER line
# _OFFER = re.compile(
#     r'\[OFFER\s*◀\]\s*server=([\d.]+)\s+offered_ip=(?:\[93m)?([\d.]+)(?:\[0m)?\s+'
#     r'pool_slots_consumed=(\d+)\s+total_offers=(\d+)'
# )

# # TX line
# _TX = re.compile(
#     r'\[TX\]\s+sent=(\d+)\s+last_mac=([\da-f:]+)\s+'
#     r'offers_back=(\d+)\s+unique_pool_slots_consumed=(\d+)'
# )

# # Session init line (interface / own MAC)
# _INIT = re.compile(r'Interface\s+:\s+(\S+)\s+\(own MAC:\s+([\da-f:]+)\)')
# _TARGET  = re.compile(r'Target\s+:\s+([\d.]+):(\d+)')
# _PCOUNT  = re.compile(r'Packet count:\s+(\d+)')
# _INTV    = re.compile(r'Interval\s+:\s+(\S+)')

# # Summary block
# _SUM_SENT   = re.compile(r'DISCOVERs sent\s+:\s+(\d+)')
# _SUM_OFFERS = re.compile(r'OFFERs received back\s+:\s+(\d+)')
# _SUM_SLOTS  = re.compile(r'Unique pool IPs consumed:\s+(\d+)')
# _SUM_IPS    = re.compile(r"Pool IPs seen\s+:\s+\[(.+)\]")


# def clean(line: str) -> str:
#     return _ANSI.sub('', line)


# def parse_log(path: str) -> dict:
#     d = dict(
#         # session meta
#         interface='—', own_mac='—', server_ip='—', server_port='67',
#         packet_count=0, interval='—', started_at='—',
#         # live counters
#         discovers_sent=0, offers_received=0, pool_consumed=0,
#         # series for charts
#         offer_series=[],   # {ts, ip, slots, total}
#         tx_series=[],      # {ts, sent, slots, mac}
#         # ip pool
#         offered_ips=[],
#         # summary (end-of-run block)
#         summary=None,
#         # raw lines for log stream
#         raw_lines=[],
#     )

#     if not os.path.exists(path):
#         return d

#     try:
#         with open(path, 'r', errors='replace') as f:
#             lines = f.readlines()
#     except Exception:
#         return d

#     d['raw_lines'] = lines

#     ip_set = []

#     for line in lines:
#         c = clean(line)

#         m = _TS.match(c.strip())
#         ts_str = m.group(1) if m else ''

#         # ── session info ──
#         mi = _INIT.search(c)
#         if mi:
#             d['interface'] = mi.group(1)
#             d['own_mac']   = mi.group(2)

#         mt = _TARGET.search(c)
#         if mt:
#             d['server_ip']   = mt.group(1)
#             d['server_port'] = mt.group(2)

#         mpc = _PCOUNT.search(c)
#         if mpc:
#             d['packet_count'] = int(mpc.group(1))

#         miv = _INTV.search(c)
#         if miv and 'Interval' in c:
#             d['interval'] = miv.group(1)

#         if 'Started:' in c:
#             m2 = re.search(r'Started:\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', c)
#             if m2:
#                 d['started_at'] = m2.group(1)

#         # ── OFFER ──
#         mo = _OFFER.search(c)
#         if mo:
#             ip    = mo.group(2)
#             slots = int(mo.group(3))
#             total = int(mo.group(4))
#             d['server_ip']      = mo.group(1)
#             d['offers_received'] = total
#             d['pool_consumed']  = max(d['pool_consumed'], slots)
#             if ip not in ip_set:
#                 ip_set.append(ip)
#             d['offer_series'].append(dict(ts=ts_str, ip=ip, slots=slots, total=total))
#             continue

#         # ── TX ──
#         mx = _TX.search(c)
#         if mx:
#             sent  = int(mx.group(1))
#             slots = int(mx.group(4))
#             d['discovers_sent'] = max(d['discovers_sent'], sent)
#             d['pool_consumed']  = max(d['pool_consumed'], slots)
#             d['tx_series'].append(dict(ts=ts_str, sent=sent, slots=slots, mac=mx.group(2)))
#             continue

#         # ── summary ──
#         ms  = _SUM_SENT.search(c)
#         mo2 = _SUM_OFFERS.search(c)
#         msl = _SUM_SLOTS.search(c)
#         mip = _SUM_IPS.search(c)

#         if ms:
#             d['discovers_sent'] = max(d['discovers_sent'], int(ms.group(1)))
#         if mo2:
#             d['offers_received'] = max(d['offers_received'], int(mo2.group(1)))
#         if msl:
#             d['pool_consumed']  = max(d['pool_consumed'], int(msl.group(1)))
#         if mip:
#             ip_list = [i.strip().strip("'") for i in mip.group(1).split(',')]
#             for ip in ip_list:
#                 if ip and ip not in ip_set:
#                     ip_set.append(ip)

#     d['offered_ips'] = ip_set

#     # derive attack efficiency
#     if d['discovers_sent']:
#         d['efficiency'] = round(d['pool_consumed'] / d['discovers_sent'] * 100, 1)
#     else:
#         d['efficiency'] = 0.0

#     # pool drain %  (assume /24 = 254 hosts if not known)
#     d['pool_total'] = d['packet_count'] or 254
#     d['drain_pct']  = min(round(d['pool_consumed'] / max(d['pool_total'],1) * 100, 1), 100)

#     return d


# # ══════════════════════════════════════════════════════════════════
# # CHART BUILDERS
# # ══════════════════════════════════════════════════════════════════

# _LAYOUT = dict(
#     paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
#     font=dict(family='JetBrains Mono', color='#546e7a', size=10),
#     margin=dict(l=48, r=16, t=36, b=40),
#     xaxis=dict(gridcolor='#0e1822', zerolinecolor='#0e1822', showgrid=True),
#     yaxis=dict(gridcolor='#0e1822', zerolinecolor='#0e1822', showgrid=True),
#     legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10)),
# )


# def chart_pool_drain(data):
#     series = data['offer_series']
#     fig = go.Figure()
#     if series:
#         df = pd.DataFrame(series)
#         fig.add_trace(go.Scatter(
#             x=list(range(len(df))), y=df['slots'],
#             mode='lines', name='IPs Consumed',
#             line=dict(color='#e53935', width=2.5),
#             fill='tozeroy', fillcolor='rgba(229,57,53,0.07)',
#         ))
#     fig.update_layout(
#         **_LAYOUT,
#         title=dict(text='POOL DRAIN — IPs Consumed Over Time',
#                    font=dict(size=11, color='#37474f'), x=0),
#         yaxis_title='IPs consumed', xaxis_title='OFFER event #',
#         height=260,
#     )
#     return fig


# def chart_discover_vs_pool(data):
#     tx = data['tx_series']
#     fig = go.Figure()
#     if tx:
#         df = pd.DataFrame(tx)
#         fig.add_trace(go.Scatter(
#             x=df['ts'], y=df['sent'],
#             mode='lines+markers', name='DISCOVERs Sent',
#             line=dict(color='#42a5f5', width=2),
#             marker=dict(size=4),
#         ))
#         fig.add_trace(go.Scatter(
#             x=df['ts'], y=df['slots'],
#             mode='lines+markers', name='Pool Slots Consumed',
#             line=dict(color='#e53935', width=2, dash='dot'),
#             marker=dict(size=4),
#         ))
#     fig.update_layout(
#         **_LAYOUT,
#         title=dict(text='DISCOVERs SENT vs POOL SLOTS CONSUMED',
#                    font=dict(size=11, color='#37474f'), x=0),
#         yaxis_title='count', xaxis_title='timestamp',
#         height=260,
#     )
#     fig.update_xaxes(tickangle=-30, tickfont=dict(size=8))
#     return fig


# def chart_offer_rate(data):
#     """Offers received per minute (binned)."""
#     series = data['offer_series']
#     fig = go.Figure()
#     if series:
#         df = pd.DataFrame(series)
#         df['t'] = pd.to_datetime(df['ts'], errors='coerce')
#         df = df.dropna(subset=['t'])
#         if not df.empty:
#             df = df.set_index('t').resample('1min').size().reset_index()
#             df.columns = ['minute', 'offers']
#             fig.add_trace(go.Bar(
#                 x=df['minute'].dt.strftime('%H:%M'),
#                 y=df['offers'],
#                 marker_color='#ffca28',
#                 name='Offers/min',
#             ))
#     fig.update_layout(
#         **_LAYOUT,
#         title=dict(text='OFFER RATE — OFFERs per Minute',
#                    font=dict(size=11, color='#37474f'), x=0),
#         yaxis_title='offers', xaxis_title='minute',
#         height=260,
#     )
#     return fig


# # ══════════════════════════════════════════════════════════════════
# # LOG STREAM RENDERER
# # ══════════════════════════════════════════════════════════════════

# def render_log(lines):
#     html = []
#     for line in reversed(lines[-300:]):
#         c = clean(line).rstrip()
#         if not c.strip():
#             continue

#         lvl_class = 'log-info'
#         txt_class  = 'log-info'

#         if '[WARNING' in c:
#             lvl_class = 'log-lvl-w'
#         elif '[INFO' in c:
#             lvl_class = 'log-lvl-i'

#         if '[OFFER' in c:
#             txt_class = 'log-offer'
#         elif '[TX]' in c:
#             txt_class = 'log-tx'
#         elif 'STARVATION ATTACK SUMMARY' in c or '══' in c or '──' in c:
#             txt_class = 'log-sum'

#         safe = (c.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))
#         html.append(f'<div class="log-line {txt_class}">{safe}</div>')

#     return '<div class="log-wrap">' + '\n'.join(html) + '</div>'


# # ══════════════════════════════════════════════════════════════════
# # TIMELINE TABLE
# # ══════════════════════════════════════════════════════════════════

# def render_timeline(data, n=30):
#     events = []
#     for o in data['offer_series']:
#         events.append(dict(ts=o['ts'], kind='OFFER', detail=f"IP offered: {o['ip']}", extra=f"slots={o['slots']}"))
#     for t in data['tx_series']:
#         events.append(dict(ts=t['ts'], kind='TX', detail=f"sent={t['sent']}", extra=f"mac={t['mac']}"))

#     # sort by ts
#     events.sort(key=lambda e: e['ts'])
#     events = events[-n:]   # last N

#     rows = []
#     for e in reversed(events):
#         kind  = e['kind']
#         badge = f'<span class="tl-badge {"offer" if kind=="OFFER" else "tx"}">{kind}</span>'
#         ts    = f'<span class="ts">{e["ts"]}</span>'
#         det   = e['detail']
#         ext   = e['extra']

#         if kind == 'OFFER':
#             det = f'<span class="evt-offer ip">{det}</span>'
#         else:
#             det = f'<span class="evt-tx">{det}</span>'

#         ext = f'<span class="mac">{ext}</span>'
#         rows.append(f'<tr><td>{ts}</td><td>{badge}</td><td>{det}</td><td>{ext}</td></tr>')

#     return f"""
#     <table class="tl-table">
#       <thead><tr>
#         <th>Timestamp</th><th>Event</th><th>Detail</th><th>Extra</th>
#       </tr></thead>
#       <tbody>{''.join(rows) if rows else '<tr><td colspan="4" style="color:#37474f;padding:16px">No events yet</td></tr>'}</tbody>
#     </table>"""


# # ══════════════════════════════════════════════════════════════════
# # SIDEBAR
# # ══════════════════════════════════════════════════════════════════

# def sidebar_ui(default_log):
#     with st.sidebar:
#         st.markdown("## ☠ DHCP Monitor")
#         st.markdown("---")
#         log_path = st.text_input("Log file path", value=default_log,
#                                   help="Path to starvation.py log output")
#         pool_size = st.number_input("Known pool size (for drain %)",
#                                      min_value=1, max_value=65534, value=254,
#                                      help="Set to your DHCP server's actual pool size")
#         refresh = st.slider("Auto-refresh (sec)", 1, 30, 3)
#         live    = st.toggle("Live mode (auto-refresh)", value=True)
#         st.markdown("---")
#         st.markdown(
#             "<small style='color:#263238;font-family:JetBrains Mono,monospace'>"
#             "⚠ LAB / EDUCATIONAL USE ONLY<br><br>"
#             "Reads the log produced by starvation.py and visualises pool drain in real-time."
#             "</small>", unsafe_allow_html=True)
#     return log_path, pool_size, refresh, live


# # ══════════════════════════════════════════════════════════════════
# # MAIN
# # ══════════════════════════════════════════════════════════════════

# def main():
#     parser = argparse.ArgumentParser(add_help=False)
#     parser.add_argument("--log", default="starvation.log")
#     args, _ = parser.parse_known_args()

#     log_path, pool_size, refresh_sec, live_mode = sidebar_ui(args.log)

#     data = parse_log(log_path)
#     data['pool_total'] = pool_size
#     data['drain_pct']  = min(round(data['pool_consumed'] / pool_size * 100, 1), 100)

#     # ── HERO ──────────────────────────────────────────────────────
#     file_ok  = os.path.exists(log_path)
#     dot_html = '<span class="pulse"></span>' if file_ok else '🔴'
#     status   = f'LIVE  ·  {log_path}' if file_ok else f'FILE NOT FOUND  ·  {log_path}'

#     st.markdown(f"""
#     <div class="hero">
#         <div class="hero-title">☠ DHCP STARVATION MONITOR</div>
#         <div class="hero-sub">Real-time pool drain visualiser  ·  Lab environment</div>
#         <div class="hero-badge">{dot_html}&nbsp;{status}</div>
#     </div>
#     """, unsafe_allow_html=True)

#     # ── KPI CARDS ─────────────────────────────────────────────────
#     st.markdown('<div class="sec-label">KEY METRICS</div>', unsafe_allow_html=True)
#     st.markdown(f"""
#     <div class="kpi-grid">
#         <div class="kpi-card red">
#             <div class="kpi-label">Pool IPs Consumed</div>
#             <div class="kpi-value red">{data['pool_consumed']}</div>
#             <div class="kpi-sub">of {pool_size} available</div>
#         </div>
#         <div class="kpi-card blue">
#             <div class="kpi-label">DISCOVERs Sent</div>
#             <div class="kpi-value blue">{data['discovers_sent']}</div>
#             <div class="kpi-sub">spoofed MACs</div>
#         </div>
#         <div class="kpi-card amber">
#             <div class="kpi-label">OFFERs Received</div>
#             <div class="kpi-value amber">{data['offers_received']}</div>
#             <div class="kpi-sub">server replies</div>
#         </div>
#         <div class="kpi-card teal">
#             <div class="kpi-label">Efficiency</div>
#             <div class="kpi-value teal">{data['efficiency']}%</div>
#             <div class="kpi-sub">offers / discovers</div>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # ── POOL DRAIN BAR ────────────────────────────────────────────
#     st.markdown('<div class="sec-label">POOL DRAIN STATUS</div>', unsafe_allow_html=True)
#     pct = data['drain_pct']
#     st.markdown(f"""
#     <div class="pool-bar-wrap">
#         <div class="pool-bar-header">
#             <span class="pool-bar-title">IP Pool Exhaustion</span>
#             <span class="pool-bar-pct">{pct}%</span>
#         </div>
#         <div class="pool-bar-bg">
#             <div class="pool-bar-fill" style="width:{pct}%"></div>
#         </div>
#         <div class="pool-bar-sub">
#             <span>{data['pool_consumed']} IPs consumed</span>
#             <span>{max(pool_size - data['pool_consumed'], 0)} IPs remaining</span>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # ── SESSION INFO ──────────────────────────────────────────────
#     st.markdown('<div class="sec-label">SESSION INFORMATION</div>', unsafe_allow_html=True)
#     st.markdown(f"""
#     <div class="sess-grid">
#         <div class="sess-row"><span class="sess-key">Interface</span><span class="sess-val">{data['interface']}</span></div>
#         <div class="sess-row"><span class="sess-key">Own MAC</span><span class="sess-val">{data['own_mac']}</span></div>
#         <div class="sess-row"><span class="sess-key">DHCP Server</span><span class="sess-val">{data['server_ip']}:{data['server_port']}</span></div>
#         <div class="sess-row"><span class="sess-key">Packet Count</span><span class="sess-val">{data['packet_count']}</span></div>
#         <div class="sess-row"><span class="sess-key">Interval</span><span class="sess-val">{data['interval']}</span></div>
#         <div class="sess-row"><span class="sess-key">Started At</span><span class="sess-val">{data['started_at']}</span></div>
#     </div>
#     """, unsafe_allow_html=True)

#     # ── CHARTS ────────────────────────────────────────────────────
#     st.markdown('<div class="sec-label">LIVE CHARTS</div>', unsafe_allow_html=True)
#     c1, c2 = st.columns(2)
#     with c1:
#         st.plotly_chart(chart_pool_drain(data),        use_container_width=True, config={"displayModeBar":False})
#     with c2:
#         st.plotly_chart(chart_discover_vs_pool(data),  use_container_width=True, config={"displayModeBar":False})

#     # st.plotly_chart(chart_offer_rate(data), use_container_width=True, config={"displayModeBar":False})

#     # ── EVENT TIMELINE ────────────────────────────────────────────
#     st.markdown('<div class="sec-label">EVENT TIMELINE  (last 30)</div>', unsafe_allow_html=True)
#     st.markdown(render_timeline(data), unsafe_allow_html=True)

#     # ── CONSUMED IP POOL ──────────────────────────────────────────
#     if data['offered_ips']:
#         st.markdown('<div class="sec-label">CONSUMED POOL IPs</div>', unsafe_allow_html=True)
#         tiles = ''.join(f'<div class="ip-tile">{ip}</div>' for ip in sorted(data['offered_ips']))
#         st.markdown(f'<div class="ip-grid">{tiles}</div>', unsafe_allow_html=True)

#     # ── RAW LOG STREAM ────────────────────────────────────────────
#     st.markdown('<div class="sec-label">RAW LOG STREAM  (newest first)</div>', unsafe_allow_html=True)
#     st.markdown(render_log(data['raw_lines']), unsafe_allow_html=True)

#     # ── AUTO REFRESH ──────────────────────────────────────────────
#     if live_mode:
#         time.sleep(refresh_sec)
#         st.rerun()


# if __name__ == '__main__':
#     main()


#!/usr/bin/env python3
"""
dashboard.py  —  DHCP Starvation Live Dashboard
================================================
Usage:
    streamlit run dashboard.py -- --log starvation.log
"""

import re, os, time, signal, argparse, subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DHCP Starvation Monitor",
    page_icon="☠",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
        ["sudo", "python3", "starvation.py"],
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


# ══════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Exo+2:wght@300;600;900&display=swap');

html, body, [class*="css"]  { background:#05080d !important; color:#b0bec5; }
*, *::before, *::after      { box-sizing:border-box; }

section[data-testid="stSidebar"] {
    background:#080c13 !important;
    border-right:1px solid #0e1822;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span { color:#546e7a !important; font-family:'JetBrains Mono',monospace !important; font-size:0.72rem !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2   { color:#e53935 !important; font-family:'Exo 2',sans-serif !important; }

.hero {
    position:relative; padding:28px 32px 20px;
    background:linear-gradient(135deg,#0a0f1a 0%,#0d1520 60%,#120a0a 100%);
    border:1px solid #1a2332; border-radius:12px;
    margin-bottom:28px; overflow:hidden;
}
.hero::before {
    content:''; position:absolute; inset:0;
    background:radial-gradient(ellipse 60% 80% at 80% 50%, rgba(229,57,53,.07) 0%, transparent 70%);
}
.hero-title {
    font-family:'Exo 2',sans-serif; font-weight:900;
    font-size:2.1rem; letter-spacing:5px; text-transform:uppercase;
    color:#e53935; text-shadow:0 0 30px rgba(229,57,53,.5);
    margin:0 0 4px;
}
.hero-sub {
    font-family:'JetBrains Mono',monospace; font-size:.7rem;
    color:#37474f; letter-spacing:3px; text-transform:uppercase;
}
.hero-badge {
    display:inline-flex; align-items:center; gap:8px;
    background:rgba(229,57,53,.08); border:1px solid rgba(229,57,53,.2);
    border-radius:20px; padding:4px 14px; margin-top:14px;
    font-family:'JetBrains Mono',monospace; font-size:.7rem; color:#e57373;
}
.pulse { width:8px; height:8px; border-radius:50%; background:#e53935;
         box-shadow:0 0 6px #e53935; animation:pulse 1.4s ease-in-out infinite; }
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

/* ── section labels ── */
.sec-label {
    font-family:'JetBrains Mono',monospace; font-size:.65rem;
    color:#37474f; letter-spacing:3px; text-transform:uppercase;
    border-bottom:1px solid #0e1822; padding-bottom:8px; margin:28px 0 14px;
    display:flex; align-items:center; gap:10px;
}
.sec-label::before { content:'▶'; color:#e53935; font-size:.55rem; }

/* ── metric cards ── */
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:4px; }
.kpi-card {
    background:#080c13; border:1px solid #0e1822;
    border-radius:10px; padding:20px 22px 16px;
    position:relative; overflow:hidden;
    transition:border-color .25s;
}
.kpi-card:hover { border-color:#1a2332; }
.kpi-card::after {
    content:''; position:absolute; bottom:0; left:0; right:0; height:2px;
}
.kpi-card.red::after   { background:linear-gradient(90deg,transparent,#e53935,transparent); }
.kpi-card.blue::after  { background:linear-gradient(90deg,transparent,#1565c0,transparent); }
.kpi-card.amber::after { background:linear-gradient(90deg,transparent,#f57f17,transparent); }
.kpi-card.teal::after  { background:linear-gradient(90deg,transparent,#00695c,transparent); }

.kpi-label { font-family:'JetBrains Mono',monospace; font-size:.62rem;
             color:#37474f; letter-spacing:2px; text-transform:uppercase; margin-bottom:10px; }
.kpi-value { font-family:'Exo 2',sans-serif; font-weight:900; font-size:2.4rem;
             line-height:1; margin-bottom:6px; }
.kpi-value.red   { color:#e53935; text-shadow:0 0 20px rgba(229,57,53,.4); }
.kpi-value.blue  { color:#42a5f5; text-shadow:0 0 20px rgba(66,165,245,.3); }
.kpi-value.amber { color:#ffca28; text-shadow:0 0 20px rgba(255,202,40,.3); }
.kpi-value.teal  { color:#4db6ac; text-shadow:0 0 20px rgba(77,182,172,.3); }
.kpi-sub  { font-family:'JetBrains Mono',monospace; font-size:.62rem; color:#546e7a; }

.pool-bar-wrap { background:#080c13; border:1px solid #0e1822; border-radius:10px; padding:20px 24px; }
.pool-bar-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
.pool-bar-title  { font-family:'JetBrains Mono',monospace; font-size:.65rem; color:#37474f; letter-spacing:2px; text-transform:uppercase; }
.pool-bar-pct    { font-family:'Exo 2',sans-serif; font-weight:900; font-size:1.6rem; color:#e53935; }
.pool-bar-bg     { height:12px; background:#0e1822; border-radius:6px; overflow:hidden; }
.pool-bar-fill   { height:100%; border-radius:6px;
                   background:linear-gradient(90deg,#b71c1c,#e53935,#ff7043);
                   box-shadow:0 0 12px rgba(229,57,53,.6);
                   transition:width .6s ease; }
.pool-bar-sub    { display:flex; justify-content:space-between; margin-top:8px;
                   font-family:'JetBrains Mono',monospace; font-size:.6rem; color:#546e7a; }

.tl-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:.72rem; }
.tl-table th { color:#37474f; text-transform:uppercase; letter-spacing:2px;
               font-size:.6rem; padding:8px 12px; border-bottom:1px solid #0e1822;
               text-align:left; font-weight:400; }
.tl-table td { padding:7px 12px; border-bottom:1px solid #080c13; vertical-align:middle; }
.tl-table tr:hover td { background:#080c13; }
.tl-table .ts   { color:#37474f; font-size:.65rem; }
.tl-table .evt-offer { color:#ffca28; }
.tl-table .evt-tx    { color:#42a5f5; }
.tl-table .ip        { color:#4db6ac; }
.tl-table .mac       { color:#7986cb; }
.tl-table .num       { color:#e57373; font-weight:700; }
.tl-badge {
    display:inline-block; padding:1px 8px; border-radius:10px; font-size:.6rem;
    font-weight:700; letter-spacing:1px;
}
.tl-badge.offer { background:rgba(255,202,40,.12); color:#ffca28; border:1px solid rgba(255,202,40,.2); }
.tl-badge.tx    { background:rgba(66,165,245,.12);  color:#42a5f5; border:1px solid rgba(66,165,245,.2); }

.ip-grid { display:flex; flex-wrap:wrap; gap:8px; }
.ip-tile {
    background:#080c13; border:1px solid rgba(229,57,53,.2);
    border-radius:6px; padding:6px 12px;
    font-family:'JetBrains Mono',monospace; font-size:.7rem; color:#ef9a9a;
    position:relative;
}
.ip-tile::before { content:'●'; color:#e53935; font-size:.5rem;
                   margin-right:6px; vertical-align:middle; }

.sess-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.sess-row  { display:flex; justify-content:space-between; align-items:center;
             padding:9px 14px; background:#080c13; border:1px solid #0e1822;
             border-radius:6px; font-family:'JetBrains Mono',monospace; font-size:.7rem; }
.sess-key  { color:#37474f; text-transform:uppercase; letter-spacing:1px; font-size:.62rem; }
.sess-val  { color:#80cbc4; }

.log-wrap  { background:#030507; border:1px solid #0e1822; border-radius:10px;
             padding:14px 16px; height:320px; overflow-y:auto; }
.log-line  { padding:2px 0; font-family:'JetBrains Mono',monospace;
             font-size:.68rem; line-height:1.75; white-space:pre-wrap; word-break:break-all; }
.log-ts    { color:#263238; }
.log-lvl-w { color:#b71c1c; }
.log-lvl-i { color:#1b5e20; }
.log-offer { color:#f9a825; }
.log-tx    { color:#1565c0; }
.log-sum   { color:#4a148c; }
.log-info  { color:#455a64; }

#MainMenu,footer,header,[data-testid="stToolbar"] { visibility:hidden; }
div[data-testid="stDecoration"] { display:none; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# PARSER
# ══════════════════════════════════════════════════════════════════

_ANSI  = re.compile(r'\x1b?\[\d+m|\[\d+m')
_TS    = re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})')
_LVL   = re.compile(r'\[(WARNING|INFO)\s*\]')
_OFFER = re.compile(
    r'\[OFFER\s*◀\]\s*server=([\d.]+)\s+offered_ip=(?:\[93m)?([\d.]+)(?:\[0m)?\s+'
    r'pool_slots_consumed=(\d+)\s+total_offers=(\d+)'
)
_TX    = re.compile(
    r'\[TX\]\s+sent=(\d+)\s+last_mac=([\da-f:]+)\s+'
    r'offers_back=(\d+)\s+unique_pool_slots_consumed=(\d+)'
)
_INIT    = re.compile(r'Interface\s+:\s+(\S+)\s+\(own MAC:\s+([\da-f:]+)\)')
_TARGET  = re.compile(r'Target\s+:\s+([\d.]+):(\d+)')
_PCOUNT  = re.compile(r'Packet count:\s+(\d+)')
_INTV    = re.compile(r'Interval\s+:\s+(\S+)')
_SUM_SENT   = re.compile(r'DISCOVERs sent\s+:\s+(\d+)')
_SUM_OFFERS = re.compile(r'OFFERs received back\s+:\s+(\d+)')
_SUM_SLOTS  = re.compile(r'Unique pool IPs consumed:\s+(\d+)')
_SUM_IPS    = re.compile(r"Pool IPs seen\s+:\s+\[(.+)\]")


def clean(line: str) -> str:
    return _ANSI.sub('', line)


def parse_log(path: str) -> dict:
    d = dict(
        interface='—', own_mac='—', server_ip='—', server_port='67',
        packet_count=0, interval='—', started_at='—',
        discovers_sent=0, offers_received=0, pool_consumed=0,
        offer_series=[], tx_series=[], offered_ips=[],
        summary=None, raw_lines=[],
    )
    if not os.path.exists(path):
        return d
    try:
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        return d

    d['raw_lines'] = lines
    ip_set = []

    for line in lines:
        c = clean(line)
        m = _TS.match(c.strip())
        ts_str = m.group(1) if m else ''

        mi = _INIT.search(c)
        if mi:
            d['interface'] = mi.group(1); d['own_mac'] = mi.group(2)

        mt = _TARGET.search(c)
        if mt:
            d['server_ip'] = mt.group(1); d['server_port'] = mt.group(2)

        mpc = _PCOUNT.search(c)
        if mpc:
            d['packet_count'] = int(mpc.group(1))

        miv = _INTV.search(c)
        if miv and 'Interval' in c:
            d['interval'] = miv.group(1)

        if 'Started:' in c:
            m2 = re.search(r'Started:\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', c)
            if m2:
                d['started_at'] = m2.group(1)

        mo = _OFFER.search(c)
        if mo:
            ip = mo.group(2); slots = int(mo.group(3)); total = int(mo.group(4))
            d['server_ip'] = mo.group(1); d['offers_received'] = total
            d['pool_consumed'] = max(d['pool_consumed'], slots)
            if ip not in ip_set:
                ip_set.append(ip)
            d['offer_series'].append(dict(ts=ts_str, ip=ip, slots=slots, total=total))
            continue

        mx = _TX.search(c)
        if mx:
            sent = int(mx.group(1)); slots = int(mx.group(4))
            d['discovers_sent'] = max(d['discovers_sent'], sent)
            d['pool_consumed']  = max(d['pool_consumed'], slots)
            d['tx_series'].append(dict(ts=ts_str, sent=sent, slots=slots, mac=mx.group(2)))
            continue

        ms  = _SUM_SENT.search(c)
        mo2 = _SUM_OFFERS.search(c)
        msl = _SUM_SLOTS.search(c)
        mip = _SUM_IPS.search(c)

        if ms:  d['discovers_sent']  = max(d['discovers_sent'],  int(ms.group(1)))
        if mo2: d['offers_received'] = max(d['offers_received'], int(mo2.group(1)))
        if msl: d['pool_consumed']   = max(d['pool_consumed'],   int(msl.group(1)))
        if mip:
            for ip in [i.strip().strip("'") for i in mip.group(1).split(',')]:
                if ip and ip not in ip_set:
                    ip_set.append(ip)

    d['offered_ips'] = ip_set
    d['efficiency']  = round(d['pool_consumed'] / d['discovers_sent'] * 100, 1) if d['discovers_sent'] else 0.0
    d['pool_total']  = d['packet_count'] or 254
    d['drain_pct']   = min(round(d['pool_consumed'] / max(d['pool_total'], 1) * 100, 1), 100)
    return d


# ══════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════

_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='JetBrains Mono', color='#546e7a', size=10),
    margin=dict(l=48, r=16, t=36, b=40),
    xaxis=dict(gridcolor='#0e1822', zerolinecolor='#0e1822', showgrid=True),
    yaxis=dict(gridcolor='#0e1822', zerolinecolor='#0e1822', showgrid=True),
    legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10)),
)

def chart_pool_drain(data):
    series = data['offer_series']
    fig = go.Figure()
    if series:
        df = pd.DataFrame(series)
        fig.add_trace(go.Scatter(
            x=list(range(len(df))), y=df['slots'],
            mode='lines', name='IPs Consumed',
            line=dict(color='#e53935', width=2.5),
            fill='tozeroy', fillcolor='rgba(229,57,53,0.07)',
        ))
    fig.update_layout(**_LAYOUT,
        title=dict(text='POOL DRAIN — IPs Consumed Over Time',
                   font=dict(size=11, color='#37474f'), x=0),
        yaxis_title='IPs consumed', xaxis_title='OFFER event #', height=260)
    return fig

def chart_discover_vs_pool(data):
    tx = data['tx_series']
    fig = go.Figure()
    if tx:
        df = pd.DataFrame(tx)
        fig.add_trace(go.Scatter(x=df['ts'], y=df['sent'],
            mode='lines+markers', name='DISCOVERs Sent',
            line=dict(color='#42a5f5', width=2), marker=dict(size=4)))
        fig.add_trace(go.Scatter(x=df['ts'], y=df['slots'],
            mode='lines+markers', name='Pool Slots Consumed',
            line=dict(color='#e53935', width=2, dash='dot'), marker=dict(size=4)))
    fig.update_layout(**_LAYOUT,
        title=dict(text='DISCOVERs SENT vs POOL SLOTS CONSUMED',
                   font=dict(size=11, color='#37474f'), x=0),
        yaxis_title='count', xaxis_title='timestamp', height=260)
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=8))
    return fig


# ══════════════════════════════════════════════════════════════════
# LOG STREAM
# ══════════════════════════════════════════════════════════════════

def render_log(lines):
    html = []
    for line in reversed(lines[-300:]):
        c = clean(line).rstrip()
        if not c.strip():
            continue
        lvl_class = 'log-info'; txt_class = 'log-info'
        if '[WARNING' in c: lvl_class = 'log-lvl-w'
        elif '[INFO'   in c: lvl_class = 'log-lvl-i'
        if   '[OFFER'  in c: txt_class = 'log-offer'
        elif '[TX]'    in c: txt_class = 'log-tx'
        elif 'STARVATION ATTACK SUMMARY' in c or '══' in c or '──' in c: txt_class = 'log-sum'
        safe = c.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        html.append(f'<div class="log-line {txt_class}">{safe}</div>')
    return '<div class="log-wrap">' + '\n'.join(html) + '</div>'


# ══════════════════════════════════════════════════════════════════
# TIMELINE TABLE
# ══════════════════════════════════════════════════════════════════

def render_timeline(data, n=30):
    events = []
    for o in data['offer_series']:
        events.append(dict(ts=o['ts'], kind='OFFER', detail=f"IP offered: {o['ip']}", extra=f"slots={o['slots']}"))
    for t in data['tx_series']:
        events.append(dict(ts=t['ts'], kind='TX', detail=f"sent={t['sent']}", extra=f"mac={t['mac']}"))
    events.sort(key=lambda e: e['ts'])
    events = events[-n:]
    rows = []
    for e in reversed(events):
        kind  = e['kind']
        badge = f'<span class="tl-badge {"offer" if kind=="OFFER" else "tx"}">{kind}</span>'
        ts    = f'<span class="ts">{e["ts"]}</span>'
        det   = f'<span class="evt-offer ip">{e["detail"]}</span>' if kind == 'OFFER' else f'<span class="evt-tx">{e["detail"]}</span>'
        ext   = f'<span class="mac">{e["extra"]}</span>'
        rows.append(f'<tr><td>{ts}</td><td>{badge}</td><td>{det}</td><td>{ext}</td></tr>')
    return f"""
    <table class="tl-table">
      <thead><tr><th>Timestamp</th><th>Event</th><th>Detail</th><th>Extra</th></tr></thead>
      <tbody>{''.join(rows) if rows else '<tr><td colspan="4" style="color:#37474f;padding:16px">No events yet</td></tr>'}</tbody>
    </table>"""


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════

def sidebar_ui(default_log):
    with st.sidebar:
        st.markdown("## ☠ DHCP Monitor")
        st.markdown("---")
        log_path  = st.text_input("Log file path", value=default_log,
                                   help="Path to starvation.py log output")
        pool_size = st.number_input("Known pool size (for drain %)",
                                     min_value=1, max_value=65534, value=254)
        refresh   = st.slider("Auto-refresh (sec)", 1, 30, 3)
        live      = st.toggle("Live mode (auto-refresh)", value=True)
        st.markdown("---")
        st.markdown(
            "<small style='color:#263238;font-family:JetBrains Mono,monospace'>"
            "⚠ LAB / EDUCATIONAL USE ONLY<br><br>"
            "Reads the log produced by starvation.py and visualises pool drain in real-time."
            "</small>", unsafe_allow_html=True)
    return log_path, pool_size, refresh, live


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
                <div class="{lbl_class}">starvation.py — {status_txt}</div>
                <div class="ctrl-meta">sudo python3 starvation.py 2&gt;&amp;1 | tee {log_path}</div>
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
    parser.add_argument("--log", default="starvation.log")
    args, _ = parser.parse_known_args()

    log_path, pool_size, refresh_sec, live_mode = sidebar_ui(args.log)

    data = parse_log(log_path)
    data['pool_total'] = pool_size
    data['drain_pct']  = min(round(data['pool_consumed'] / pool_size * 100, 1), 100)

    # ── HERO ──────────────────────────────────────────────────────
    file_ok  = os.path.exists(log_path)
    dot_html = '<span class="pulse"></span>' if file_ok else '🔴'
    status   = f'LIVE  ·  {log_path}' if file_ok else f'FILE NOT FOUND  ·  {log_path}'

    st.markdown(f"""
    <div class="hero">
        <div class="hero-title">☠ DHCP STARVATION MONITOR</div>
        <div class="hero-sub">Real-time pool drain visualiser  ·  Lab environment</div>
        <div class="hero-badge">{dot_html}&nbsp;{status}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── ATTACK CONTROL PANEL ──────────────────────────────────────
    st.markdown('<div class="sec-label">ATTACK CONTROL</div>', unsafe_allow_html=True)
    render_control_panel(log_path)

    # ── KPI CARDS ─────────────────────────────────────────────────
    st.markdown('<div class="sec-label">KEY METRICS</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card red">
            <div class="kpi-label">Pool IPs Consumed</div>
            <div class="kpi-value red">{data['pool_consumed']}</div>
            <div class="kpi-sub">of {pool_size} available</div>
        </div>
        <div class="kpi-card blue">
            <div class="kpi-label">DISCOVERs Sent</div>
            <div class="kpi-value blue">{data['discovers_sent']}</div>
            <div class="kpi-sub">spoofed MACs</div>
        </div>
        <div class="kpi-card amber">
            <div class="kpi-label">OFFERs Received</div>
            <div class="kpi-value amber">{data['offers_received']}</div>
            <div class="kpi-sub">server replies</div>
        </div>
        <div class="kpi-card teal">
            <div class="kpi-label">Efficiency</div>
            <div class="kpi-value teal">{data['efficiency']}%</div>
            <div class="kpi-sub">offers / discovers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── POOL DRAIN BAR ────────────────────────────────────────────
    st.markdown('<div class="sec-label">POOL DRAIN STATUS</div>', unsafe_allow_html=True)
    pct = data['drain_pct']
    st.markdown(f"""
    <div class="pool-bar-wrap">
        <div class="pool-bar-header">
            <span class="pool-bar-title">IP Pool Exhaustion</span>
            <span class="pool-bar-pct">{pct}%</span>
        </div>
        <div class="pool-bar-bg">
            <div class="pool-bar-fill" style="width:{pct}%"></div>
        </div>
        <div class="pool-bar-sub">
            <span>{data['pool_consumed']} IPs consumed</span>
            <span>{max(pool_size - data['pool_consumed'], 0)} IPs remaining</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SESSION INFO ──────────────────────────────────────────────
    st.markdown('<div class="sec-label">SESSION INFORMATION</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sess-grid">
        <div class="sess-row"><span class="sess-key">Interface</span><span class="sess-val">{data['interface']}</span></div>
        <div class="sess-row"><span class="sess-key">Own MAC</span><span class="sess-val">{data['own_mac']}</span></div>
        <div class="sess-row"><span class="sess-key">DHCP Server</span><span class="sess-val">{data['server_ip']}:{data['server_port']}</span></div>
        <div class="sess-row"><span class="sess-key">Packet Count</span><span class="sess-val">{data['packet_count']}</span></div>
        <div class="sess-row"><span class="sess-key">Interval</span><span class="sess-val">{data['interval']}</span></div>
        <div class="sess-row"><span class="sess-key">Started At</span><span class="sess-val">{data['started_at']}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── CHARTS ────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">LIVE CHARTS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_pool_drain(data),       use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(chart_discover_vs_pool(data), use_container_width=True, config={"displayModeBar": False})

    # ── EVENT TIMELINE ────────────────────────────────────────────
    st.markdown('<div class="sec-label">EVENT TIMELINE  (last 30)</div>', unsafe_allow_html=True)
    st.markdown(render_timeline(data), unsafe_allow_html=True)

    # ── CONSUMED IP POOL ──────────────────────────────────────────
    if data['offered_ips']:
        st.markdown('<div class="sec-label">CONSUMED POOL IPs</div>', unsafe_allow_html=True)
        tiles = ''.join(f'<div class="ip-tile">{ip}</div>' for ip in sorted(data['offered_ips']))
        st.markdown(f'<div class="ip-grid">{tiles}</div>', unsafe_allow_html=True)

    # ── RAW LOG STREAM ────────────────────────────────────────────
    st.markdown('<div class="sec-label">RAW LOG STREAM  (newest first)</div>', unsafe_allow_html=True)
    st.markdown(render_log(data['raw_lines']), unsafe_allow_html=True)

    # ── AUTO REFRESH ──────────────────────────────────────────────
    if live_mode:
        time.sleep(refresh_sec)
        st.rerun()


if __name__ == '__main__':
    main()