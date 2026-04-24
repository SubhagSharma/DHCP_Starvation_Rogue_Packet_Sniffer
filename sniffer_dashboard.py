# """
# mitm_dashboard.py — MITM Traffic Analysis Dashboard
# Run with: streamlit run mitm_dashboard.py [-- --log /path/to/mitm_capture.log]
# """

# import re
# import sys
# import os
# import time
# import argparse
# from datetime import datetime
# from collections import defaultdict
# from io import StringIO
# from pathlib import Path

# import pandas as pd
# import streamlit as st
# import plotly.express as px
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots

# # ─────────────────────────────────────────────────────────────
# # PAGE CONFIG
# # ─────────────────────────────────────────────────────────────
# st.set_page_config(
#     page_title="MITM Traffic Analyzer",
#     page_icon="🕵️",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # ─────────────────────────────────────────────────────────────
# # CUSTOM THEME  (dark cyberpunk / terminal aesthetic)
# # ─────────────────────────────────────────────────────────────
# st.markdown("""
# <style>
# @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600&display=swap');

# /* Root palette */
# :root {
#     --bg:       #060b14;
#     --panel:    #0d1826;
#     --border:   #1a3a5c;
#     --accent1:  #00d4ff;
#     --accent2:  #ff4060;
#     --accent3:  #39ff14;
#     --accent4:  #ff9f1c;
#     --text:     #c8dde8;
#     --muted:    #4a7090;
# }

# /* Global */
# html, body, [class*="css"] {
#     background-color: var(--bg) !important;
#     color: var(--text) !important;
#     font-family: 'Exo 2', sans-serif !important;
# }

# /* Hide Streamlit chrome */
# #MainMenu, footer, header { visibility: hidden; }
# .block-container { padding-top: 1rem !important; }

# /* Sidebar */
# [data-testid="stSidebar"] {
#     background: var(--panel) !important;
#     border-right: 1px solid var(--border) !important;
# }
# [data-testid="stSidebar"] * { color: var(--text) !important; }

# /* Metric cards */
# [data-testid="metric-container"] {
#     background: var(--panel);
#     border: 1px solid var(--border);
#     border-radius: 8px;
#     padding: 1rem;
#     box-shadow: 0 0 16px rgba(0,212,255,0.07);
# }
# [data-testid="stMetricValue"] {
#     font-family: 'Orbitron', monospace !important;
#     font-size: 1.9rem !important;
#     color: var(--accent1) !important;
# }
# [data-testid="stMetricLabel"] {
#     font-family: 'Share Tech Mono', monospace !important;
#     color: var(--muted) !important;
#     font-size: 0.7rem !important;
#     letter-spacing: 0.1em;
#     text-transform: uppercase;
# }
# [data-testid="stMetricDelta"] { color: var(--accent3) !important; }

# /* Dataframe */
# [data-testid="stDataFrame"] {
#     border: 1px solid var(--border) !important;
#     border-radius: 6px;
# }

# /* Tabs */
# [data-testid="stTabs"] button {
#     font-family: 'Share Tech Mono', monospace !important;
#     color: var(--muted) !important;
#     font-size: 0.78rem;
#     letter-spacing: 0.08em;
#     text-transform: uppercase;
# }
# [data-testid="stTabs"] button[aria-selected="true"] {
#     color: var(--accent1) !important;
#     border-bottom: 2px solid var(--accent1) !important;
# }

# /* Headers */
# h1 { font-family: 'Orbitron', monospace !important; color: var(--accent1) !important; letter-spacing: 0.06em; }
# h2, h3 { font-family: 'Exo 2', sans-serif !important; color: var(--text) !important; }

# /* Selectbox & widgets */
# [data-testid="stSelectbox"], [data-testid="stMultiSelect"] {
#     background: var(--panel) !important;
# }
# .stSelectbox > div > div, .stMultiSelect > div > div {
#     background: var(--panel) !important;
#     border: 1px solid var(--border) !important;
#     color: var(--text) !important;
# }

# /* Banner pulse */
# @keyframes pulse-border {
#     0%, 100% { box-shadow: 0 0 6px rgba(0,212,255,0.3); }
#     50%       { box-shadow: 0 0 22px rgba(0,212,255,0.7); }
# }
# .banner {
#     background: linear-gradient(135deg, #060b14 0%, #0a1a2e 50%, #060b14 100%);
#     border: 1px solid var(--accent1);
#     border-radius: 10px;
#     padding: 1.4rem 2rem;
#     margin-bottom: 1.5rem;
#     animation: pulse-border 3s ease-in-out infinite;
#     display: flex;
#     align-items: center;
#     gap: 1.5rem;
# }
# .banner-title {
#     font-family: 'Orbitron', monospace;
#     font-size: 1.6rem;
#     font-weight: 900;
#     color: var(--accent1);
#     letter-spacing: 0.08em;
#     line-height: 1.1;
# }
# .banner-sub {
#     font-family: 'Share Tech Mono', monospace;
#     font-size: 0.72rem;
#     color: var(--muted);
#     letter-spacing: 0.12em;
#     text-transform: uppercase;
#     margin-top: 0.3rem;
# }
# .edu-badge {
#     background: rgba(57,255,20,0.1);
#     border: 1px solid var(--accent3);
#     color: var(--accent3);
#     font-family: 'Share Tech Mono', monospace;
#     font-size: 0.65rem;
#     letter-spacing: 0.1em;
#     padding: 0.25rem 0.7rem;
#     border-radius: 4px;
#     text-transform: uppercase;
#     white-space: nowrap;
# }

# /* Tag pills */
# .tag-dns  { background: rgba(0,212,255,0.15); color:#00d4ff; border:1px solid #00d4ff33; }
# .tag-http { background: rgba(255,159,28,0.15); color:#ff9f1c; border:1px solid #ff9f1c33; }
# .tag-cred { background: rgba(255,64,96,0.18);  color:#ff4060; border:1px solid #ff406033; }
# .tag {
#     display: inline-block;
#     padding: 0.15rem 0.55rem;
#     border-radius: 4px;
#     font-family: 'Share Tech Mono', monospace;
#     font-size: 0.7rem;
#     letter-spacing: 0.08em;
#     text-transform: uppercase;
#     font-weight: 600;
# }

# /* Alert box */
# .alert-cred {
#     background: rgba(255,64,96,0.1);
#     border-left: 3px solid var(--accent2);
#     padding: 0.6rem 1rem;
#     border-radius: 0 6px 6px 0;
#     font-family: 'Share Tech Mono', monospace;
#     font-size: 0.8rem;
#     color: var(--accent2);
#     margin: 0.3rem 0;
# }
# .ip-card {
#     background: var(--panel);
#     border: 1px solid var(--border);
#     border-radius: 8px;
#     padding: 1rem 1.2rem;
#     margin: 0.4rem 0;
# }
# .mono { font-family: 'Share Tech Mono', monospace; }
# </style>
# """, unsafe_allow_html=True)

# # ─────────────────────────────────────────────────────────────
# # LOG PARSER
# # ─────────────────────────────────────────────────────────────

# LOG_RE = re.compile(
#     r"\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+"
#     r"\[(?P<category>[A-Z]+)\s*\]\s+"
#     r"(?P<message>.+)"
# )

# SAMPLE_LOG = """\
# 2026-04-12 11:52:03  [INFO    ]  MITM-SNIFFER          [MITM] IP forwarding enabled
# 2026-04-12 11:52:23  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:52:23]  [HTTP  ]  192.168.1.141 → 163.70.146.175  POST /chat HTTP/1.1  Host: c.whatsapp.net
# 2026-04-12 11:52:43  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:52:43]  [HTTP  ]  192.168.1.140 → 146.190.62.39  GET /css/style.min.css HTTP/1.1  Host: httpforever.com
# 2026-04-12 11:52:45  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:52:45]  [HTTP  ]  192.168.1.140 → 146.190.62.39  GET /css/images/header-major-on-light.svg HTTP/1.1  Host: httpforever.com
# 2026-04-12 11:53:12  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:12]  [DNS   ]  192.168.1.141  queried  connectivitycheck.gstatic.com
# 2026-04-12 11:53:12  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:12]  [DNS   ]  192.168.1.141  queried  www.google.com
# 2026-04-12 11:53:13  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:13]  [HTTP  ]  192.168.1.141 → 142.251.43.99  GET /generate_204 HTTP/1.1  Host: connectivitycheck.gstatic.com
# 2026-04-12 11:53:29  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:29]  [DNS   ]  192.168.1.142  queried  connectivitycheck.platform.hicloud.com
# 2026-04-12 11:53:30  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:30]  [DNS   ]  192.168.1.142  queried  mtalk.google.com
# 2026-04-12 11:53:31  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:31]  [HTTP  ]  192.168.1.142 → 98.98.40.14  GET /generate_204_424c9cb5-9742-4522-a759-9d99f8a3a7d8 HTTP/1.1  Host: connectivitycheck.platform.hicloud.com
# 2026-04-12 11:53:44  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:44]  [HTTP  ]  192.168.1.141 → 163.70.146.175  POST /chat HTTP/1.1  Host: c.whatsapp.net
# 2026-04-12 11:54:14  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:54:14]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.120.109.88.10.in-addr.arpa
# 2026-04-12 11:54:14  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:54:14]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.0.1.168.192.in-addr.arpa
# 2026-04-12 11:54:38  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:54:38]  [DNS   ]  192.168.1.142  queried  test-gateway.instagram.com
# 2026-04-12 11:55:04  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:55:04]  [DNS   ]  192.168.1.142  queried  connectivitycheck.platform.hicloud.com
# 2026-04-12 11:55:55  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:55:55]  [HTTP  ]  192.168.1.141 → 142.251.43.99  GET /generate_204 HTTP/1.1  Host: connectivitycheck.gstatic.com
# 2026-04-12 11:56:21  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:21]  [DNS   ]  192.168.1.141  queried  www.google.com
# 2026-04-12 11:56:24  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:24]  [DNS   ]  192.168.1.141  queried  play.googleapis.com
# 2026-04-12 11:56:25  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:25]  [HTTP  ]  192.168.1.141 → 216.239.32.223  GET /generate_204 HTTP/1.1  Host: play.googleapis.com
# 2026-04-12 11:56:57  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:57]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.151.74.90.100.in-addr.arpa
# 2026-04-12 11:56:57  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:57]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.0.1.168.192.in-addr.arpa
# 2026-04-12 11:57:10  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:57:10]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.120.109.88.10.in-addr.arpa
# 2026-04-12 11:58:06  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:58:06]  [DNS   ]  192.168.1.140  queried  dns.google
# 2026-04-12 11:59:15  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:59:15]  [DNS   ]  192.168.1.141  queried  connectivitycheck.gstatic.com
# 2026-04-12 11:59:15  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:59:15]  [HTTP  ]  192.168.1.141 → 142.251.43.99  GET /generate_204 HTTP/1.1  Host: connectivitycheck.gstatic.com
# 2026-04-12 12:01:17  [INFO    ]  MITM-SNIFFER          [2026-04-12 12:01:17]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.0.1.168.192.in-addr.arpa
# """

# # ─── inner-log line parser ───
# INNER_RE = re.compile(
#     r"\[(?P<ts2>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+"
#     r"\[(?P<cat>[A-Z]+)\s*\]\s+"
#     r"(?P<body>.+)"
# )
# HTTP_RE = re.compile(
#     r"(?P<src>\d+\.\d+\.\d+\.\d+)\s*[→>]\s*(?P<dst>\d+\.\d+\.\d+\.\d+)\s+"
#     r"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD)\s+(?P<path>\S+)\s+HTTP/[\d.]+\s+Host:\s*(?P<host>\S+)"
# )
# DNS_RE  = re.compile(
#     r"(?P<src>\d+\.\d+\.\d+\.\d+)\s+queried\s+(?P<domain>\S+)"
# )
# CRED_RE = re.compile(
#     r"CREDENTIAL FOUND\s+(?P<src>\d+\.\d+\.\d+\.\d+)\s*[→>]\s*(?P<dst>\d+\.\d+\.\d+\.\d+)\s+"
#     r"(?P<field>\S+)\s*=\s*(?P<value>.+)"
# )


# def parse_log(text: str) -> pd.DataFrame:
#     rows = []
#     for raw_line in text.splitlines():
#         raw_line = raw_line.strip()
#         if not raw_line:
#             continue
#         # Try inner-format first (from the log file itself)
#         m = INNER_RE.search(raw_line)
#         if not m:
#             continue
#         ts_str = m.group("ts2")
#         cat    = m.group("cat").strip()
#         body   = m.group("body").strip()

#         try:
#             ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
#         except ValueError:
#             continue

#         row = {"timestamp": ts, "category": cat, "raw": body,
#                "src_ip": None, "dst_ip": None, "method": None,
#                "path": None, "host": None, "domain": None,
#                "cred_field": None, "cred_value": None}

#         if cat == "HTTP":
#             hm = HTTP_RE.search(body)
#             if hm:
#                 row.update({"src_ip": hm.group("src"), "dst_ip": hm.group("dst"),
#                             "method": hm.group("method"), "path": hm.group("path"),
#                             "host": hm.group("host")})
#         elif cat == "DNS":
#             dm = DNS_RE.search(body)
#             if dm:
#                 row.update({"src_ip": dm.group("src"), "domain": dm.group("domain")})
#         elif cat == "CREDS":
#             cm = CRED_RE.search(body)
#             if cm:
#                 row.update({"src_ip": cm.group("src"), "dst_ip": cm.group("dst"),
#                             "cred_field": cm.group("field"), "cred_value": cm.group("value")})
#         rows.append(row)

#     return pd.DataFrame(rows) if rows else pd.DataFrame()


# # ─────────────────────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────────────────────

# PLOTLY_THEME = dict(
#     paper_bgcolor="rgba(0,0,0,0)",
#     plot_bgcolor="rgba(0,0,0,0)",
#     font=dict(family="Share Tech Mono, monospace", color="#c8dde8", size=11),
#     margin=dict(l=10, r=10, t=30, b=10),
#     xaxis=dict(gridcolor="#1a3a5c", zerolinecolor="#1a3a5c", color="#4a7090"),
#     yaxis=dict(gridcolor="#1a3a5c", zerolinecolor="#1a3a5c", color="#4a7090"),
# )

# # Default legend style — merge into update_layout calls that don't override legend
# _LEGEND = dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1a3a5c")

# def theme(**kwargs):
#     """Return PLOTLY_THEME merged with a default legend + any overrides."""
#     merged = {**PLOTLY_THEME, "legend": _LEGEND, **kwargs}
#     return merged

# CAT_COLORS = {"DNS": "#00d4ff", "HTTP": "#ff9f1c", "CREDS": "#ff4060", "COOKIE": "#a78bfa"}

# def cat_color(cat):
#     return CAT_COLORS.get(cat.upper(), "#c8dde8")

# def classify_domain(domain: str) -> str:
#     d = domain.lower()
#     if "google" in d or "gstatic" in d or "googleapis" in d:  return "Google"
#     if "whatsapp" in d or "wa.me" in d:                        return "WhatsApp"
#     if "instagram" in d or "fb.com" in d or "facebook" in d:  return "Meta"
#     if "hicloud" in d or "huawei" in d:                        return "Huawei"
#     if "in-addr.arpa" in d:                                    return "Reverse DNS"
#     if "dns.google" in d:                                      return "DNS-over-HTTPS"
#     return "Other"

# # ─────────────────────────────────────────────────────────────
# # SIDEBAR
# # ─────────────────────────────────────────────────────────────

# with st.sidebar:
#     st.markdown("### 🕵️ **MITM ANALYZER**")
#     st.markdown("---")

#     # ── Log Source ──
#     log_source = st.radio(
#         "Log Source",
#         ["Use built-in sample", "Live log file (auto-refresh)", "Upload log file", "Paste log text"],
#         index=0
#     )

#     raw_text = SAMPLE_LOG
#     live_mode = False
#     live_path = None

#     if log_source == "Live log file (auto-refresh)":
#         live_mode = True
#         default_path = "/tmp/mitm_capture.log"
#         live_path = st.text_input("Log file path", value=default_path,
#                                   placeholder="/tmp/mitm_capture.log")
#         refresh_interval = st.selectbox(
#             "Auto-refresh every", [3, 5, 10, 30, 60],
#             index=1, format_func=lambda x: f"{x} seconds"
#         )
#         tail_lines = st.number_input("Show last N lines (0 = all)", min_value=0, value=0, step=100)

#         if live_path and Path(live_path).exists():
#             try:
#                 with open(live_path, "r", errors="replace") as f:
#                     lines = f.readlines()
#                 if tail_lines > 0:
#                     lines = lines[-int(tail_lines):]
#                 raw_text = "".join(lines)
#                 file_size = Path(live_path).stat().st_size
#                 mtime     = datetime.fromtimestamp(Path(live_path).stat().st_mtime)
#                 st.success(f"✅ Watching: `{live_path}`")
#                 st.caption(f"Size: {file_size/1024:.1f} KB  |  Modified: {mtime.strftime('%H:%M:%S')}")
#             except Exception as e:
#                 st.error(f"Cannot read file: {e}")
#         else:
#             if live_path:
#                 st.warning(f"File not found:\n`{live_path}`\n\nSniffer may not have started yet.")
#             else:
#                 st.info("Enter the path to your live log file.")

#     elif log_source == "Upload log file":
#         uploaded = st.file_uploader("Upload mitm_capture.log", type=["log", "txt"])
#         if uploaded:
#             raw_text = uploaded.read().decode("utf-8", errors="replace")
#         else:
#             st.info("Using sample data until file uploaded.")

#     elif log_source == "Paste log text":
#         pasted = st.text_area("Paste log content here", height=200)
#         if pasted.strip():
#             raw_text = pasted

#     # ── Live mode status bar ──
#     if live_mode and live_path and Path(live_path).exists():
#         st.markdown("---")
#         st.markdown("""
#         <div style="background:rgba(57,255,20,0.08);border:1px solid #39ff14;
#                     border-radius:6px;padding:0.5rem 0.8rem;
#                     font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#39ff14">
#           🟢 LIVE MODE ACTIVE<br>
#           <span style="color:#4a7090">Dashboard refreshes automatically</span>
#         </div>""", unsafe_allow_html=True)

#     st.markdown("---")
#     st.markdown("##### 🔍 Filters")

#     df_all = parse_log(raw_text)
#     if df_all.empty:
#         st.warning("No parseable data found.")

#     all_ips = sorted(set(
#         list(df_all["src_ip"].dropna().unique()) +
#         list(df_all["dst_ip"].dropna().unique())
#     )) if not df_all.empty else []

#     sel_ips = st.multiselect("Filter by IP", ["All"] + all_ips, default=["All"])
#     sel_cats = st.multiselect(
#         "Traffic type",
#         ["DNS", "HTTP", "CREDS"],
#         default=["DNS", "HTTP", "CREDS"]
#     )

#     st.markdown("---")
#     st.markdown(
#         "<span class='edu-badge'>⚠ Educational / Lab Use Only</span>",
#         unsafe_allow_html=True
#     )
#     st.markdown("<br>", unsafe_allow_html=True)
#     st.caption("Built for authorized local network analysis.")

# # ─────────────────────────────────────────────────────────────
# # FILTER
# # ─────────────────────────────────────────────────────────────

# df = df_all.copy()
# if not df.empty:
#     if sel_cats:
#         df = df[df["category"].isin(sel_cats)]
#     if sel_ips and "All" not in sel_ips:
#         df = df[
#             df["src_ip"].isin(sel_ips) | df["dst_ip"].isin(sel_ips)
#         ]

# # ─────────────────────────────────────────────────────────────
# # BANNER
# # ─────────────────────────────────────────────────────────────

# st.markdown(f"""
# <div class="banner">
#   <div style="font-size:2.8rem">🕵️</div>
#   <div>
#     <div class="banner-title">MITM TRAFFIC ANALYZER</div>
#     <div class="banner-sub">Network Interception Dashboard · Educational Lab Environment
#       {'&nbsp;·&nbsp; <span style="color:#39ff14">⬤ LIVE</span>' if live_mode and live_path and Path(live_path).exists() else ''}
#     </div>
#   </div>
#   <div style="margin-left:auto">
#     <span class="edu-badge">🔒 Lab Use Only</span>
#   </div>
# </div>
# """, unsafe_allow_html=True)

# if df_all.empty:
#     st.error("No data to display. Check your log input.")
#     st.stop()

# # ─────────────────────────────────────────────────────────────
# # TOP METRICS
# # ─────────────────────────────────────────────────────────────

# total       = len(df)
# dns_count   = (df["category"] == "DNS").sum()
# http_count  = (df["category"] == "HTTP").sum()
# cred_count  = (df["category"] == "CREDS").sum()
# unique_ips  = df["src_ip"].dropna().nunique()
# unique_hosts = df["host"].dropna().nunique()

# c1, c2, c3, c4, c5, c6 = st.columns(6)
# c1.metric("Total Events",     total)
# c2.metric("DNS Queries",      dns_count,   delta=f"{dns_count/max(total,1)*100:.0f}%")
# c3.metric("HTTP Requests",    http_count,  delta=f"{http_count/max(total,1)*100:.0f}%")
# c4.metric("🚨 Credentials",   cred_count,  delta="ALERT" if cred_count > 0 else None,
#           delta_color="inverse" if cred_count == 0 else "normal")
# c5.metric("Unique Src IPs",   unique_ips)
# c6.metric("Unique Hosts",     unique_hosts)

# st.markdown("<br>", unsafe_allow_html=True)

# # ─────────────────────────────────────────────────────────────
# # CREDENTIAL ALERT BANNER
# # ─────────────────────────────────────────────────────────────

# if cred_count > 0:
#     st.markdown(f"""
#     <div style="background:rgba(255,64,96,0.12);border:1px solid #ff4060;
#                 border-radius:8px;padding:0.8rem 1.2rem;margin-bottom:1rem;
#                 font-family:'Share Tech Mono',monospace;">
#       🚨 <strong style="color:#ff4060">CREDENTIALS DETECTED</strong> —
#       {cred_count} credential capture event(s) found in the log.
#       Review the <strong>CREDS</strong> tab immediately.
#     </div>
#     """, unsafe_allow_html=True)

# # ─────────────────────────────────────────────────────────────
# # TABS
# # ─────────────────────────────────────────────────────────────

# tabs = st.tabs([
#     "📊 Overview",
#     "🌐 DNS Analysis",
#     "🔗 HTTP Analysis",
#     "🖥️ Per-IP Profile",
#     "📋 Raw Log",
#     "⚠️ Threat Summary",
# ])

# # ─────────────────────────────────────────────────────────────
# # TAB 0 — OVERVIEW
# # ─────────────────────────────────────────────────────────────
# with tabs[0]:
#     left, right = st.columns([3, 2])
    
#     with left:
#         st.markdown("#### Traffic Volume Over Time")
#         if not df.empty and "timestamp" in df.columns:
#             ts_df = df.copy()
#             ts_df["minute"] = ts_df["timestamp"].dt.floor("1min")
#             tl = ts_df.groupby(["minute","category"]).size().reset_index(name="count")
#             fig = px.bar(
#                 tl, x="minute", y="count", color="category",
#                 color_discrete_map=CAT_COLORS,
#                 labels={"minute":"Time","count":"Events","category":"Type"},
#             )
#             fig.update_layout(**theme(barmode="stack",
#                               legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)")))
#             st.plotly_chart(fig, use_container_width=True)

#     with right:
#         st.markdown("#### Event Distribution")
#         pie_data = df["category"].value_counts().reset_index()
#         pie_data.columns = ["category","count"]
#         fig2 = px.pie(pie_data, names="category", values="count",
#                       color="category", color_discrete_map=CAT_COLORS,
#                       hole=0.55)
#         fig2.update_traces(textfont_family="Share Tech Mono",
#                            textfont_color="#c8dde8")
#         fig2.update_layout(**theme())
#         st.plotly_chart(fig2, use_container_width=True)

#     st.markdown("#### Top Source IPs by Activity")
#     ip_activity = df.groupby(["src_ip","category"]).size().reset_index(name="count")
#     ip_activity = ip_activity[ip_activity["src_ip"].notna()]
#     fig3 = px.bar(ip_activity, x="src_ip", y="count", color="category",
#                   color_discrete_map=CAT_COLORS, barmode="group",
#                   labels={"src_ip":"Source IP","count":"Events"})
#     fig3.update_layout(**theme())
#     st.plotly_chart(fig3, use_container_width=True)

# # ─────────────────────────────────────────────────────────────
# # TAB 1 — DNS
# # ─────────────────────────────────────────────────────────────
# with tabs[1]:
#     dns_df = df[df["category"] == "DNS"].copy()
    
#     if dns_df.empty:
#         st.info("No DNS events in current filter.")
#     else:
#         dns_df["service"] = dns_df["domain"].apply(
#             lambda x: classify_domain(str(x)) if pd.notna(x) else "Unknown"
#         )
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.markdown("#### Top Queried Domains")
#             top_domains = dns_df["domain"].value_counts().head(20).reset_index()
#             top_domains.columns = ["domain","queries"]
#             fig = px.bar(top_domains, x="queries", y="domain", orientation="h",
#                          color="queries",
#                          color_continuous_scale=["#0d1826","#00d4ff"],
#                          labels={"domain":"Domain","queries":"Query Count"})
#             fig.update_layout(**theme(coloraxis_showscale=False,
#                               yaxis=dict(autorange="reversed",gridcolor="#1a3a5c",color="#4a7090")))
#             st.plotly_chart(fig, use_container_width=True)
        
#         with col2:
#             st.markdown("#### Queries by Service Category")
#             svc = dns_df["service"].value_counts().reset_index()
#             svc.columns = ["service","count"]
#             SVCCOLORS = {
#                 "Google":"#4285F4","WhatsApp":"#25D366","Meta":"#0080FF",
#                 "Huawei":"#CF0A2C","Reverse DNS":"#888888","DNS-over-HTTPS":"#ff9f1c","Other":"#a78bfa"
#             }
#             fig2 = px.pie(svc, names="service", values="count",
#                           color="service", color_discrete_map=SVCCOLORS, hole=0.5)
#             fig2.update_layout(**theme())
#             st.plotly_chart(fig2, use_container_width=True)
        
#         st.markdown("#### DNS Query Timeline per Device")
#         dns_tl = dns_df.copy()
#         dns_tl["minute"] = dns_tl["timestamp"].dt.floor("30s")
#         dtl = dns_tl.groupby(["minute","src_ip"]).size().reset_index(name="queries")
#         fig3 = px.line(dtl, x="minute", y="queries", color="src_ip",
#                        markers=True,
#                        color_discrete_sequence=["#00d4ff","#ff9f1c","#ff4060","#39ff14"],
#                        labels={"minute":"Time","queries":"DNS Queries","src_ip":"Device IP"})
#         fig3.update_layout(**theme())
#         st.plotly_chart(fig3, use_container_width=True)
        
#         # Suspicious DNS patterns
#         st.markdown("#### 🔎 Notable DNS Observations")
#         suspicious = dns_df[dns_df["domain"].str.contains("in-addr.arpa", na=False)]
#         doh = dns_df[dns_df["domain"].str.contains("dns.google", na=False)]
        
#         nc1, nc2 = st.columns(2)
#         with nc1:
#             st.markdown(f"""
#             <div class="ip-card">
#               <div class="mono" style="color:#ff9f1c;font-size:0.75rem;letter-spacing:.1em">REVERSE DNS LOOKUPS</div>
#               <div style="font-size:2rem;font-family:'Orbitron',monospace;color:#c8dde8">{len(suspicious)}</div>
#               <div style="color:#4a7090;font-size:0.75rem">Device discovery / mDNS probes detected</div>
#             </div>""", unsafe_allow_html=True)
#         with nc2:
#             st.markdown(f"""
#             <div class="ip-card">
#               <div class="mono" style="color:#ff9f1c;font-size:0.75rem;letter-spacing:.1em">DNS-OVER-HTTPS ATTEMPTS</div>
#               <div style="font-size:2rem;font-family:'Orbitron',monospace;color:#c8dde8">{len(doh)}</div>
#               <div style="color:#4a7090;font-size:0.75rem">Queries to dns.google — bypass attempts</div>
#             </div>""", unsafe_allow_html=True)
        
#         st.markdown("#### Full DNS Log")
#         st.dataframe(
#             dns_df[["timestamp","src_ip","domain","service"]].sort_values("timestamp"),
#             use_container_width=True, hide_index=True
#         )

# # ─────────────────────────────────────────────────────────────
# # TAB 2 — HTTP
# # ─────────────────────────────────────────────────────────────
# with tabs[2]:
#     http_df = df[df["category"] == "HTTP"].copy()
    
#     if http_df.empty:
#         st.info("No HTTP events in current filter.")
#     else:
#         col1, col2, col3 = st.columns(3)
#         col1.metric("GET requests",  (http_df["method"]=="GET").sum())
#         col2.metric("POST requests", (http_df["method"]=="POST").sum())
#         col3.metric("Unique Hosts",  http_df["host"].nunique())
        
#         st.markdown("#### Top HTTP Hosts")
#         top_hosts = http_df["host"].value_counts().head(15).reset_index()
#         top_hosts.columns = ["host","requests"]
#         fig = px.bar(top_hosts, x="requests", y="host", orientation="h",
#                      color="requests",
#                      color_continuous_scale=["#0d1826","#ff9f1c"],
#                      labels={"host":"Host","requests":"Requests"})
#         fig.update_layout(**theme(coloraxis_showscale=False,
#                           yaxis=dict(autorange="reversed", gridcolor="#1a3a5c", color="#4a7090")))
#         st.plotly_chart(fig, use_container_width=True)
        
#         col_a, col_b = st.columns(2)
#         with col_a:
#             st.markdown("#### HTTP Methods")
#             method_counts = http_df["method"].value_counts().reset_index()
#             method_counts.columns = ["method","count"]
#             method_colors = {"GET":"#00d4ff","POST":"#ff4060","PUT":"#ff9f1c","DELETE":"#a78bfa"}
#             fig2 = px.pie(method_counts, names="method", values="count",
#                           color="method", color_discrete_map=method_colors, hole=0.4)
#             fig2.update_layout(**theme())
#             st.plotly_chart(fig2, use_container_width=True)
        
#         with col_b:
#             st.markdown("#### Requests per Source IP")
#             ip_req = http_df["src_ip"].value_counts().reset_index()
#             ip_req.columns = ["ip","requests"]
#             fig3 = px.bar(ip_req, x="ip", y="requests",
#                           color="requests",
#                           color_continuous_scale=["#0d1826","#00d4ff"])
#             fig3.update_layout(**theme(), coloraxis_showscale=False)
#             st.plotly_chart(fig3, use_container_width=True)
        
#         # POST body highlight
#         post_df = http_df[http_df["method"] == "POST"]
#         if len(post_df) > 0:
#             st.markdown("#### 🔴 POST Requests (Potential Data Exfiltration)")
#             for _, row in post_df.iterrows():
#                 st.markdown(f"""
#                 <div class="alert-cred">
#                   ▸ {row['timestamp']}  |  {row['src_ip']} → {row['dst_ip']}
#                     POST {row['path']}  Host: {row['host']}
#                 </div>""", unsafe_allow_html=True)
        
#         st.markdown("#### Full HTTP Log")
#         st.dataframe(
#             http_df[["timestamp","src_ip","dst_ip","method","host","path"]].sort_values("timestamp"),
#             use_container_width=True, hide_index=True
#         )

# # ─────────────────────────────────────────────────────────────
# # TAB 3 — PER-IP PROFILE
# # ─────────────────────────────────────────────────────────────
# with tabs[3]:
#     st.markdown("#### Select Device to Profile")
#     all_src = sorted(df["src_ip"].dropna().unique())
    
#     if not all_src:
#         st.info("No source IPs in filtered data.")
#     else:
#         chosen_ip = st.selectbox("Device IP", all_src)
#         ip_df = df[df["src_ip"] == chosen_ip]
        
#         ip_dns  = ip_df[ip_df["category"] == "DNS"]
#         ip_http = ip_df[ip_df["category"] == "HTTP"]
#         ip_cred = ip_df[ip_df["category"] == "CREDS"]
        
#         c1, c2, c3, c4 = st.columns(4)
#         c1.metric("Total Events",    len(ip_df))
#         c2.metric("DNS Queries",     len(ip_dns))
#         c3.metric("HTTP Requests",   len(ip_http))
#         c4.metric("🚨 Credentials",  len(ip_cred))
        
#         # Activity timeline
#         if not ip_df.empty:
#             st.markdown("#### Activity Timeline")
#             ip_tl = ip_df.copy()
#             ip_tl["minute"] = ip_tl["timestamp"].dt.floor("30s")
#             tl = ip_tl.groupby(["minute","category"]).size().reset_index(name="count")
#             fig = px.bar(tl, x="minute", y="count", color="category",
#                          color_discrete_map=CAT_COLORS, barmode="stack")
#             fig.update_layout(**theme())
#             st.plotly_chart(fig, use_container_width=True)
        
#         col_left, col_right = st.columns(2)
        
#         with col_left:
#             if not ip_dns.empty:
#                 st.markdown("#### Queried Domains")
#                 dom_counts = ip_dns["domain"].value_counts().reset_index()
#                 dom_counts.columns = ["domain","count"]
#                 fig2 = px.bar(dom_counts.head(10), x="count", y="domain", orientation="h",
#                               color="count",
#                               color_continuous_scale=["#0d1826","#00d4ff"])
#                 fig2.update_layout(**theme(coloraxis_showscale=False,
#                                    yaxis=dict(autorange="reversed",gridcolor="#1a3a5c",color="#4a7090")))
#                 st.plotly_chart(fig2, use_container_width=True)
        
#         with col_right:
#             if not ip_http.empty:
#                 st.markdown("#### HTTP Hosts Contacted")
#                 host_c = ip_http["host"].value_counts().reset_index()
#                 host_c.columns = ["host","count"]
#                 fig3 = px.bar(host_c.head(10), x="count", y="host", orientation="h",
#                               color="count",
#                               color_continuous_scale=["#0d1826","#ff9f1c"])
#                 fig3.update_layout(**theme(coloraxis_showscale=False,
#                                    yaxis=dict(autorange="reversed",gridcolor="#1a3a5c",color="#4a7090")))
#                 st.plotly_chart(fig3, use_container_width=True)
        
#         if not ip_cred.empty:
#             st.markdown("#### 🚨 Captured Credentials")
#             for _, row in ip_cred.iterrows():
#                 st.markdown(f"""
#                 <div class="alert-cred">
#                   🔑  {row['timestamp']}  |  {row['src_ip']} → {row['dst_ip']}
#                   <br>&nbsp;&nbsp;&nbsp;&nbsp;Field: <strong>{row['cred_field']}</strong>
#                   &nbsp;|&nbsp; Value: <strong>{row['cred_value']}</strong>
#                 </div>""", unsafe_allow_html=True)
        
#         # App fingerprint
#         if not ip_dns.empty:
#             st.markdown("#### 📱 Inferred App Activity")
#             domains_seen = " ".join(ip_dns["domain"].dropna().str.lower().tolist())
#             apps = []
#             if "whatsapp" in domains_seen:  apps.append("💬 WhatsApp")
#             if "google" in domains_seen or "googleapis" in domains_seen: apps.append("🔍 Google Services / Android")
#             if "instagram" in domains_seen: apps.append("📸 Instagram")
#             if "hicloud" in domains_seen:   apps.append("📱 Huawei Device")
#             if "play.google" in domains_seen: apps.append("🎮 Google Play Store")
#             if apps:
#                 for a in apps:
#                     st.markdown(f"<div class='ip-card' style='padding:.6rem 1rem'>{a}</div>",
#                                 unsafe_allow_html=True)
#             else:
#                 st.info("No recognizable app signatures in DNS queries.")

# # ─────────────────────────────────────────────────────────────
# # TAB 4 — RAW LOG
# # ─────────────────────────────────────────────────────────────
# with tabs[4]:
#     st.markdown("#### Raw Parsed Events")
    
#     search_term = st.text_input("🔍 Search events", placeholder="e.g. whatsapp, POST, 192.168.1.141 ...")
    
#     display_df = df.copy()
#     if search_term:
#         mask = display_df.apply(
#             lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1
#         )
#         display_df = display_df[mask]
    
#     st.caption(f"Showing {len(display_df)} of {len(df)} events")
    
#     def color_category(val):
#         colors = {"DNS":"color:#00d4ff","HTTP":"color:#ff9f1c","CREDS":"color:#ff4060"}
#         return colors.get(val, "")
    
#     st.dataframe(
#         display_df[["timestamp","category","src_ip","dst_ip","host","domain","method","path","raw"]]
#                  .sort_values("timestamp").reset_index(drop=True),
#         use_container_width=True,
#         hide_index=True,
#     )
    
#     csv = display_df.to_csv(index=False)
#     st.download_button(
#         "⬇️ Download Filtered CSV",
#         data=csv,
#         file_name="mitm_filtered_export.csv",
#         mime="text/csv"
#     )

# # ─────────────────────────────────────────────────────────────
# # TAB 5 — THREAT SUMMARY
# # ─────────────────────────────────────────────────────────────
# with tabs[5]:
#     st.markdown("#### 🔎 Automated Threat & Insight Summary")
    
#     # ── Finding 1: Credentials
#     st.markdown("---")
#     has_creds = cred_count > 0
#     st.markdown(f"""
#     <div class="ip-card" style="border-color:{'#ff4060' if has_creds else '#1a3a5c'}">
#       <span style="font-family:'Orbitron';font-size:0.85rem;color:{'#ff4060' if has_creds else '#39ff14'}">
#         {'🚨 CRITICAL' if has_creds else '✅ CLEAR'} — Credential Capture
#       </span><br>
#       <span style="color:#c8dde8">
#         {'Found ' + str(cred_count) + ' credential event(s) in plaintext HTTP traffic.' if has_creds
#          else 'No credentials detected in this log.'}
#       </span>
#     </div>""", unsafe_allow_html=True)
    
#     # ── Finding 2: Plaintext HTTP POST to known apps
#     post_sensitive = df[(df["category"]=="HTTP") & (df["method"]=="POST") &
#                         (df["host"].str.contains("whatsapp|facebook|instagram|gmail|yahoo",
#                                                   na=False, case=False))]
#     has_sensitive_post = len(post_sensitive) > 0
#     st.markdown(f"""
#     <div class="ip-card" style="border-color:{'#ff9f1c' if has_sensitive_post else '#1a3a5c'}">
#       <span style="font-family:'Orbitron';font-size:0.85rem;color:{'#ff9f1c' if has_sensitive_post else '#39ff14'}">
#         {'⚠ WARNING' if has_sensitive_post else '✅ CLEAR'} — Sensitive App POST Requests
#       </span><br>
#       <span style="color:#c8dde8">
#         {'Detected ' + str(len(post_sensitive)) + ' POST request(s) to sensitive services over plaintext HTTP.' if has_sensitive_post
#          else 'No sensitive app POST requests on plaintext HTTP.'}
#       </span>
#     </div>""", unsafe_allow_html=True)
    
#     # ── Finding 3: DoH bypass
#     doh_df = df[(df["category"]=="DNS") & (df["domain"].str.contains("dns.google", na=False))]
#     has_doh = len(doh_df) > 0
#     st.markdown(f"""
#     <div class="ip-card" style="border-color:{'#ff9f1c' if has_doh else '#1a3a5c'}">
#       <span style="font-family:'Orbitron';font-size:0.85rem;color:{'#ff9f1c' if has_doh else '#39ff14'}">
#         {'⚠ INFO' if has_doh else '✅ CLEAR'} — DNS-over-HTTPS Probe
#       </span><br>
#       <span style="color:#c8dde8">
#         {'Device queried dns.google — possible attempt to bypass local DNS snooping.' if has_doh
#          else 'No DoH bypass attempts detected.'}
#       </span>
#     </div>""", unsafe_allow_html=True)
    
#     # ── Finding 4: Most active IP
#     if not df["src_ip"].dropna().empty:
#         top_ip = df["src_ip"].value_counts().idxmax()
#         top_ip_count = df["src_ip"].value_counts().max()
#         st.markdown(f"""
#         <div class="ip-card">
#           <span style="font-family:'Orbitron';font-size:0.85rem;color:#00d4ff">📡 Most Active Device</span><br>
#           <span style="color:#c8dde8">
#             <strong style="color:#00d4ff">{top_ip}</strong> generated {top_ip_count} captured events.
#           </span>
#         </div>""", unsafe_allow_html=True)
    
#     # ── Finding 5: Device fingerprints
#     st.markdown("#### 📱 Device & OS Fingerprinting (via DNS)")
#     dns_df2 = df[df["category"] == "DNS"]
    
#     fingerprints = []
#     for ip in df["src_ip"].dropna().unique():
#         ip_dns2 = dns_df2[dns_df2["src_ip"] == ip]["domain"].str.lower().str.cat(sep=" ")
#         hints = []
#         if "hicloud" in ip_dns2 or "huawei" in ip_dns2:  hints.append("Huawei Android")
#         if "gstatic" in ip_dns2 or "googleapis" in ip_dns2: hints.append("Android / Google")
#         if "whatsapp" in ip_dns2:      hints.append("WhatsApp installed")
#         if "instagram" in ip_dns2:     hints.append("Instagram installed")
#         if "mtalk.google" in ip_dns2:  hints.append("Google Firebase (push notifications)")
#         if "in-addr.arpa" in ip_dns2:  hints.append("mDNS / local service discovery")
#         if hints:
#             fingerprints.append({"IP": ip, "Inferred Profile": ", ".join(hints)})
    
#     if fingerprints:
#         st.dataframe(pd.DataFrame(fingerprints), use_container_width=True, hide_index=True)
#     else:
#         st.info("Insufficient DNS data for device fingerprinting.")
    
#     # ── Session summary
#     if not df["timestamp"].dropna().empty:
#         session_start = df["timestamp"].min()
#         session_end   = df["timestamp"].max()
#         duration      = (session_end - session_start).seconds
#         st.markdown(f"""
#         <div class="ip-card" style="margin-top:1rem">
#           <span style="font-family:'Orbitron';font-size:0.85rem;color:#a78bfa">📅 Session Summary</span><br>
#           <span class="mono" style="color:#c8dde8">
#             Start: {session_start} &nbsp;|&nbsp; End: {session_end}
#             &nbsp;|&nbsp; Duration: {duration // 60}m {duration % 60}s
#             &nbsp;|&nbsp; Avg rate: {total / max(duration, 1) * 60:.1f} events/min
#           </span>
#         </div>""", unsafe_allow_html=True)

# # ─────────────────────────────────────────────────────────────
# # LIVE AUTO-REFRESH
# # ─────────────────────────────────────────────────────────────

# if live_mode and live_path and Path(live_path).exists():
#     st.markdown("---")
#     last_col, next_col = st.columns([3, 1])
#     with last_col:
#         mtime = datetime.fromtimestamp(Path(live_path).stat().st_mtime)
#         st.caption(f"🕒 Last refresh: {datetime.now().strftime('%H:%M:%S')}  "
#                    f"|  Log last modified: {mtime.strftime('%H:%M:%S')}  "
#                    f"|  Total events parsed: {len(df_all)}")
#     with next_col:
#         if st.button("🔄 Refresh Now"):
#             st.rerun()

#     # Auto-rerun after the selected interval
#     time.sleep(refresh_interval)
#     st.rerun()



"""
mitm_dashboard.py — MITM Traffic Analysis Dashboard
Run with: streamlit run mitm_dashboard.py [-- --log /path/to/mitm_capture.log]
"""

import re
import sys
import os
import time
import argparse
import subprocess
from datetime import datetime
from collections import defaultdict
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

log_path = "./sniffer.log"

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MITM Traffic Analyzer",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)



#══════════════════════════════════════════════════════════════════
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
        ["sudo", "python3", "mitm_sniffer.py"],
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

# ─────────────────────────────────────────────────────────────
# CUSTOM THEME  (dark cyberpunk / terminal aesthetic)
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600&display=swap');

/* Root palette */
:root {
    --bg:       #060b14;
    --panel:    #0d1826;
    --border:   #1a3a5c;
    --accent1:  #00d4ff;
    --accent2:  #ff4060;
    --accent3:  #39ff14;
    --accent4:  #ff9f1c;
    --text:     #c8dde8;
    --muted:    #4a7090;
}

/* Global */
html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Exo 2', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--panel) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 0 16px rgba(0,212,255,0.07);
}
[data-testid="stMetricValue"] {
    font-family: 'Orbitron', monospace !important;
    font-size: 1.9rem !important;
    color: var(--accent1) !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--muted) !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
[data-testid="stMetricDelta"] { color: var(--accent3) !important; }

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 6px;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--muted) !important;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent1) !important;
    border-bottom: 2px solid var(--accent1) !important;
}

/* Headers */
h1 { font-family: 'Orbitron', monospace !important; color: var(--accent1) !important; letter-spacing: 0.06em; }
h2, h3 { font-family: 'Exo 2', sans-serif !important; color: var(--text) !important; }

/* Selectbox & widgets */
[data-testid="stSelectbox"], [data-testid="stMultiSelect"] {
    background: var(--panel) !important;
}
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

/* Banner pulse */
@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 6px rgba(0,212,255,0.3); }
    50%       { box-shadow: 0 0 22px rgba(0,212,255,0.7); }
}
.banner {
    background: linear-gradient(135deg, #060b14 0%, #0a1a2e 50%, #060b14 100%);
    border: 1px solid var(--accent1);
    border-radius: 10px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.5rem;
    animation: pulse-border 3s ease-in-out infinite;
    display: flex;
    align-items: center;
    gap: 1.5rem;
}
.banner-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.6rem;
    font-weight: 900;
    color: var(--accent1);
    letter-spacing: 0.08em;
    line-height: 1.1;
}
.banner-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}
.edu-badge {
    background: rgba(57,255,20,0.1);
    border: 1px solid var(--accent3);
    color: var(--accent3);
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    padding: 0.25rem 0.7rem;
    border-radius: 4px;
    text-transform: uppercase;
    white-space: nowrap;
}


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

/* Tag pills */
.tag-dns  { background: rgba(0,212,255,0.15); color:#00d4ff; border:1px solid #00d4ff33; }
.tag-http { background: rgba(255,159,28,0.15); color:#ff9f1c; border:1px solid #ff9f1c33; }
.tag-cred { background: rgba(255,64,96,0.18);  color:#ff4060; border:1px solid #ff406033; }
.tag {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 4px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600;
}

/* Alert box */
.alert-cred {
    background: rgba(255,64,96,0.1);
    border-left: 3px solid var(--accent2);
    padding: 0.6rem 1rem;
    border-radius: 0 6px 6px 0;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: var(--accent2);
    margin: 0.3rem 0;
}
.ip-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.4rem 0;
}
.mono { font-family: 'Share Tech Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LOG PARSER
# ─────────────────────────────────────────────────────────────

LOG_RE = re.compile(
    r"\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+"
    r"\[(?P<category>[A-Z]+)\s*\]\s+"
    r"(?P<message>.+)"
)

SAMPLE_LOG = """\
2026-04-12 11:52:03  [INFO    ]  MITM-SNIFFER          [MITM] IP forwarding enabled
2026-04-12 11:52:23  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:52:23]  [HTTP  ]  192.168.1.141 → 163.70.146.175  POST /chat HTTP/1.1  Host: c.whatsapp.net
2026-04-12 11:52:43  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:52:43]  [HTTP  ]  192.168.1.140 → 146.190.62.39  GET /css/style.min.css HTTP/1.1  Host: httpforever.com
2026-04-12 11:52:45  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:52:45]  [HTTP  ]  192.168.1.140 → 146.190.62.39  GET /css/images/header-major-on-light.svg HTTP/1.1  Host: httpforever.com
2026-04-12 11:53:12  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:12]  [DNS   ]  192.168.1.141  queried  connectivitycheck.gstatic.com
2026-04-12 11:53:12  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:12]  [DNS   ]  192.168.1.141  queried  www.google.com
2026-04-12 11:53:13  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:13]  [HTTP  ]  192.168.1.141 → 142.251.43.99  GET /generate_204 HTTP/1.1  Host: connectivitycheck.gstatic.com
2026-04-12 11:53:29  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:29]  [DNS   ]  192.168.1.142  queried  connectivitycheck.platform.hicloud.com
2026-04-12 11:53:30  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:30]  [DNS   ]  192.168.1.142  queried  mtalk.google.com
2026-04-12 11:53:31  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:31]  [HTTP  ]  192.168.1.142 → 98.98.40.14  GET /generate_204_424c9cb5-9742-4522-a759-9d99f8a3a7d8 HTTP/1.1  Host: connectivitycheck.platform.hicloud.com
2026-04-12 11:53:44  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:53:44]  [HTTP  ]  192.168.1.141 → 163.70.146.175  POST /chat HTTP/1.1  Host: c.whatsapp.net
2026-04-12 11:54:14  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:54:14]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.120.109.88.10.in-addr.arpa
2026-04-12 11:54:14  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:54:14]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.0.1.168.192.in-addr.arpa
2026-04-12 11:54:38  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:54:38]  [DNS   ]  192.168.1.142  queried  test-gateway.instagram.com
2026-04-12 11:55:04  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:55:04]  [DNS   ]  192.168.1.142  queried  connectivitycheck.platform.hicloud.com
2026-04-12 11:55:55  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:55:55]  [HTTP  ]  192.168.1.141 → 142.251.43.99  GET /generate_204 HTTP/1.1  Host: connectivitycheck.gstatic.com
2026-04-12 11:56:21  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:21]  [DNS   ]  192.168.1.141  queried  www.google.com
2026-04-12 11:56:24  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:24]  [DNS   ]  192.168.1.141  queried  play.googleapis.com
2026-04-12 11:56:25  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:25]  [HTTP  ]  192.168.1.141 → 216.239.32.223  GET /generate_204 HTTP/1.1  Host: play.googleapis.com
2026-04-12 11:56:57  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:57]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.151.74.90.100.in-addr.arpa
2026-04-12 11:56:57  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:56:57]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.0.1.168.192.in-addr.arpa
2026-04-12 11:57:10  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:57:10]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.120.109.88.10.in-addr.arpa
2026-04-12 11:58:06  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:58:06]  [DNS   ]  192.168.1.140  queried  dns.google
2026-04-12 11:59:15  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:59:15]  [DNS   ]  192.168.1.141  queried  connectivitycheck.gstatic.com
2026-04-12 11:59:15  [INFO    ]  MITM-SNIFFER          [2026-04-12 11:59:15]  [HTTP  ]  192.168.1.141 → 142.251.43.99  GET /generate_204 HTTP/1.1  Host: connectivitycheck.gstatic.com
2026-04-12 12:01:17  [INFO    ]  MITM-SNIFFER          [2026-04-12 12:01:17]  [DNS   ]  192.168.1.140  queried  lb._dns-sd._udp.0.1.168.192.in-addr.arpa
"""

# ─── inner-log line parser ───
INNER_RE = re.compile(
    r"\[(?P<ts2>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+"
    r"\[(?P<cat>[A-Z]+)\s*\]\s+"
    r"(?P<body>.+)"
)
HTTP_RE = re.compile(
    r"(?P<src>\d+\.\d+\.\d+\.\d+)\s*[→>]\s*(?P<dst>\d+\.\d+\.\d+\.\d+)\s+"
    r"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD)\s+(?P<path>\S+)\s+HTTP/[\d.]+\s+Host:\s*(?P<host>\S+)"
)
DNS_RE  = re.compile(
    r"(?P<src>\d+\.\d+\.\d+\.\d+)\s+queried\s+(?P<domain>\S+)"
)
CRED_RE = re.compile(
    r"CREDENTIAL FOUND\s+(?P<src>\d+\.\d+\.\d+\.\d+)\s*[→>]\s*(?P<dst>\d+\.\d+\.\d+\.\d+)\s+"
    r"(?P<field>\S+)\s*=\s*(?P<value>.+)"
)


def parse_log(text: str) -> pd.DataFrame:
    rows = []
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        # Try inner-format first (from the log file itself)
        m = INNER_RE.search(raw_line)
        if not m:
            continue
        ts_str = m.group("ts2")
        cat    = m.group("cat").strip()
        body   = m.group("body").strip()

        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        row = {"timestamp": ts, "category": cat, "raw": body,
               "src_ip": None, "dst_ip": None, "method": None,
               "path": None, "host": None, "domain": None,
               "cred_field": None, "cred_value": None}

        if cat == "HTTP":
            hm = HTTP_RE.search(body)
            if hm:
                row.update({"src_ip": hm.group("src"), "dst_ip": hm.group("dst"),
                            "method": hm.group("method"), "path": hm.group("path"),
                            "host": hm.group("host")})
        elif cat == "DNS":
            dm = DNS_RE.search(body)
            if dm:
                row.update({"src_ip": dm.group("src"), "domain": dm.group("domain")})
        elif cat == "CREDS":
            cm = CRED_RE.search(body)
            if cm:
                row.update({"src_ip": cm.group("src"), "dst_ip": cm.group("dst"),
                            "cred_field": cm.group("field"), "cred_value": cm.group("value")})
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Share Tech Mono, monospace", color="#c8dde8", size=11),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="#1a3a5c", zerolinecolor="#1a3a5c", color="#4a7090"),
    yaxis=dict(gridcolor="#1a3a5c", zerolinecolor="#1a3a5c", color="#4a7090"),
)

# Default legend style — merge into update_layout calls that don't override legend
_LEGEND = dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1a3a5c")

def theme(**kwargs):
    """Return PLOTLY_THEME merged with a default legend + any overrides."""
    merged = {**PLOTLY_THEME, "legend": _LEGEND, **kwargs}
    return merged

CAT_COLORS = {"DNS": "#00d4ff", "HTTP": "#ff9f1c", "CREDS": "#ff4060", "COOKIE": "#a78bfa"}

def cat_color(cat):
    return CAT_COLORS.get(cat.upper(), "#c8dde8")

def classify_domain(domain: str) -> str:
    d = domain.lower()
    if "google" in d or "gstatic" in d or "googleapis" in d:  return "Google"
    if "whatsapp" in d or "wa.me" in d:                        return "WhatsApp"
    if "instagram" in d or "fb.com" in d or "facebook" in d:  return "Meta"
    if "hicloud" in d or "huawei" in d:                        return "Huawei"
    if "in-addr.arpa" in d:                                    return "Reverse DNS"
    if "dns.google" in d:                                      return "DNS-over-HTTPS"
    return "Other"

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🕵️ **MITM ANALYZER**")
    st.markdown("---")

    # ── Log Source ──
    log_source = st.radio(
        "Log Source",
        ["Use built-in sample", "Live log file (auto-refresh)", "Upload log file", "Paste log text"],
        index=0
    )

    raw_text = SAMPLE_LOG
    live_mode = False
    live_path = None

    if log_source == "Live log file (auto-refresh)":
        live_mode = True
        default_path = "./sniffer.log"
        live_path = st.text_input("Log file path", value=default_path,
                                  placeholder="/tmp/mitm_capture.log")
        refresh_interval = st.selectbox(
            "Auto-refresh every", [3, 5, 10, 30, 60],
            index=1, format_func=lambda x: f"{x} seconds"
        )
        tail_lines = st.number_input("Show last N lines (0 = all)", min_value=0, value=0, step=100)

        if live_path and Path(live_path).exists():
            try:
                with open(live_path, "r", errors="replace") as f:
                    lines = f.readlines()
                if tail_lines > 0:
                    lines = lines[-int(tail_lines):]
                raw_text = "".join(lines)
                file_size = Path(live_path).stat().st_size
                mtime     = datetime.fromtimestamp(Path(live_path).stat().st_mtime)
                st.success(f"✅ Watching: `{live_path}`")
                st.caption(f"Size: {file_size/1024:.1f} KB  |  Modified: {mtime.strftime('%H:%M:%S')}")
            except Exception as e:
                st.error(f"Cannot read file: {e}")
        else:
            if live_path:
                st.warning(f"File not found:\n`{live_path}`\n\nSniffer may not have started yet.")
            else:
                st.info("Enter the path to your live log file.")

    elif log_source == "Upload log file":
        uploaded = st.file_uploader("Upload mitm_capture.log", type=["log", "txt"])
        if uploaded:
            raw_text = uploaded.read().decode("utf-8", errors="replace")
        else:
            st.info("Using sample data until file uploaded.")

    elif log_source == "Paste log text":
        pasted = st.text_area("Paste log content here", height=200)
        if pasted.strip():
            raw_text = pasted

    # ── Live mode status bar ──
    if live_mode and live_path and Path(live_path).exists():
        st.markdown("---")
        st.markdown("""
        <div style="background:rgba(57,255,20,0.08);border:1px solid #39ff14;
                    border-radius:6px;padding:0.5rem 0.8rem;
                    font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#39ff14">
          🟢 LIVE MODE ACTIVE<br>
          <span style="color:#4a7090">Dashboard refreshes automatically</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### 🔍 Filters")

    df_all = parse_log(raw_text)
    if df_all.empty:
        st.warning("No parseable data found.")

    all_ips = sorted(set(
        list(df_all["src_ip"].dropna().unique()) +
        list(df_all["dst_ip"].dropna().unique())
    )) if not df_all.empty else []

    sel_ips = st.multiselect("Filter by IP", ["All"] + all_ips, default=["All"])
    sel_cats = st.multiselect(
        "Traffic type",
        ["DNS", "HTTP", "CREDS"],
        default=["DNS", "HTTP", "CREDS"]
    )

    st.markdown("---")
    st.markdown(
        "<span class='edu-badge'>⚠ Educational / Lab Use Only</span>",
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Built for authorized local network analysis.")

# ─────────────────────────────────────────────────────────────
# FILTER
# ─────────────────────────────────────────────────────────────

df = df_all.copy()
if not df.empty:
    if sel_cats:
        df = df[df["category"].isin(sel_cats)]
    if sel_ips and "All" not in sel_ips:
        df = df[
            df["src_ip"].isin(sel_ips) | df["dst_ip"].isin(sel_ips)
        ]

# ─────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="banner">
  <div style="font-size:2.8rem">🕵️</div>
  <div>
    <div class="banner-title">MITM TRAFFIC ANALYZER</div>
    <div class="banner-sub">Network Interception Dashboard · Educational Lab Environment
      {'&nbsp;·&nbsp; <span style="color:#39ff14">⬤ LIVE</span>' if live_mode and live_path and Path(live_path).exists() else ''}
    </div>
  </div>
  <div style="margin-left:auto">
    <span class="edu-badge">🔒 Lab Use Only</span>
  </div>
</div>
""", unsafe_allow_html=True)

if df_all.empty:
    st.error("No data to display. Check your log input.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# TOP METRICS
# ─────────────────────────────────────────────────────────────

total       = len(df)
dns_count   = (df["category"] == "DNS").sum()
http_count  = (df["category"] == "HTTP").sum()
cred_count  = (df["category"] == "CREDS").sum()
unique_ips  = df["src_ip"].dropna().nunique()
unique_hosts = df["host"].dropna().nunique()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Events",     total)
c2.metric("DNS Queries",      dns_count,   delta=f"{dns_count/max(total,1)*100:.0f}%")
c3.metric("HTTP Requests",    http_count,  delta=f"{http_count/max(total,1)*100:.0f}%")
c4.metric("🚨 Credentials",   cred_count,  delta="ALERT" if cred_count > 0 else None,
          delta_color="inverse" if cred_count == 0 else "normal")
c5.metric("Unique Src IPs",   unique_ips)
c6.metric("Unique Hosts",     unique_hosts)

st.markdown("<br>", unsafe_allow_html=True)


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
                <div class="{lbl_class}">mitm_sniffer.py — {status_txt}</div>
                <div class="ctrl-meta">sudo python3 mitm_sniffer.py </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_start, col_stop, col_spacer = st.columns([1, 1, 5])

    with col_start:
        if st.button(
            "▶  START SNIFFER",
            disabled=alive,
            use_container_width=True,
            type="primary",
        ):
            start_attack(log_path)
            st.rerun()

    with col_stop:
        if st.button(
            "■  STOP SNIFFER",
            disabled=not alive,
            use_container_width=True,
            type="secondary",
        ):
            stop_attack()
            st.rerun()


# ── ATTACK CONTROL PANEL ──────────────────────────────────────
st.markdown('<div class="sec-label">MITM SNIFFER CONTROL</div>', unsafe_allow_html=True)
render_control_panel(log_path)

# ─────────────────────────────────────────────────────────────
# CREDENTIAL ALERT BANNER
# ─────────────────────────────────────────────────────────────

if cred_count > 0:
    st.markdown(f"""
    <div style="background:rgba(255,64,96,0.12);border:1px solid #ff4060;
                border-radius:8px;padding:0.8rem 1.2rem;margin-bottom:1rem;
                font-family:'Share Tech Mono',monospace;">
      🚨 <strong style="color:#ff4060">CREDENTIALS DETECTED</strong> —
      {cred_count} credential capture event(s) found in the log.
      Review the <strong>CREDS</strong> tab immediately.
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────

tabs = st.tabs([
    "📊 Overview",
    "🌐 DNS Analysis",
    "🔗 HTTP Analysis",
    "🖥️ Per-IP Profile",
    "📋 Raw Log",
    "⚠️ Threat Summary",
])

# ─────────────────────────────────────────────────────────────
# TAB 0 — OVERVIEW
# ─────────────────────────────────────────────────────────────
with tabs[0]:
    left, right = st.columns([3, 2])
    
    with left:
        st.markdown("#### Traffic Volume Over Time")
        if not df.empty and "timestamp" in df.columns:
            ts_df = df.copy()
            ts_df["minute"] = ts_df["timestamp"].dt.floor("1min")
            tl = ts_df.groupby(["minute","category"]).size().reset_index(name="count")
            fig = px.bar(
                tl, x="minute", y="count", color="category",
                color_discrete_map=CAT_COLORS,
                labels={"minute":"Time","count":"Events","category":"Type"},
            )
            fig.update_layout(**theme(barmode="stack",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)")))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Event Distribution")
        pie_data = df["category"].value_counts().reset_index()
        pie_data.columns = ["category","count"]
        fig2 = px.pie(pie_data, names="category", values="count",
                      color="category", color_discrete_map=CAT_COLORS,
                      hole=0.55)
        fig2.update_traces(textfont_family="Share Tech Mono",
                           textfont_color="#c8dde8")
        fig2.update_layout(**theme())
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### Top Source IPs by Activity")
    ip_activity = df.groupby(["src_ip","category"]).size().reset_index(name="count")
    ip_activity = ip_activity[ip_activity["src_ip"].notna()]
    fig3 = px.bar(ip_activity, x="src_ip", y="count", color="category",
                  color_discrete_map=CAT_COLORS, barmode="group",
                  labels={"src_ip":"Source IP","count":"Events"})
    fig3.update_layout(**theme())
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# TAB 1 — DNS
# ─────────────────────────────────────────────────────────────
with tabs[1]:
    dns_df = df[df["category"] == "DNS"].copy()
    
    if dns_df.empty:
        st.info("No DNS events in current filter.")
    else:
        dns_df["service"] = dns_df["domain"].apply(
            lambda x: classify_domain(str(x)) if pd.notna(x) else "Unknown"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Top Queried Domains")
            top_domains = dns_df["domain"].value_counts().head(20).reset_index()
            top_domains.columns = ["domain","queries"]
            fig = px.bar(top_domains, x="queries", y="domain", orientation="h",
                         color="queries",
                         color_continuous_scale=["#0d1826","#00d4ff"],
                         labels={"domain":"Domain","queries":"Query Count"})
            fig.update_layout(**theme(coloraxis_showscale=False,
                              yaxis=dict(autorange="reversed",gridcolor="#1a3a5c",color="#4a7090")))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Queries by Service Category")
            svc = dns_df["service"].value_counts().reset_index()
            svc.columns = ["service","count"]
            SVCCOLORS = {
                "Google":"#4285F4","WhatsApp":"#25D366","Meta":"#0080FF",
                "Huawei":"#CF0A2C","Reverse DNS":"#888888","DNS-over-HTTPS":"#ff9f1c","Other":"#a78bfa"
            }
            fig2 = px.pie(svc, names="service", values="count",
                          color="service", color_discrete_map=SVCCOLORS, hole=0.5)
            fig2.update_layout(**theme())
            st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("#### DNS Query Timeline per Device")
        dns_tl = dns_df.copy()
        dns_tl["minute"] = dns_tl["timestamp"].dt.floor("30s")
        dtl = dns_tl.groupby(["minute","src_ip"]).size().reset_index(name="queries")
        fig3 = px.line(dtl, x="minute", y="queries", color="src_ip",
                       markers=True,
                       color_discrete_sequence=["#00d4ff","#ff9f1c","#ff4060","#39ff14"],
                       labels={"minute":"Time","queries":"DNS Queries","src_ip":"Device IP"})
        fig3.update_layout(**theme())
        st.plotly_chart(fig3, use_container_width=True)
        
        # Suspicious DNS patterns
        st.markdown("#### 🔎 Notable DNS Observations")
        suspicious = dns_df[dns_df["domain"].str.contains("in-addr.arpa", na=False)]
        doh = dns_df[dns_df["domain"].str.contains("dns.google", na=False)]
        
        nc1, nc2 = st.columns(2)
        with nc1:
            st.markdown(f"""
            <div class="ip-card">
              <div class="mono" style="color:#ff9f1c;font-size:0.75rem;letter-spacing:.1em">REVERSE DNS LOOKUPS</div>
              <div style="font-size:2rem;font-family:'Orbitron',monospace;color:#c8dde8">{len(suspicious)}</div>
              <div style="color:#4a7090;font-size:0.75rem">Device discovery / mDNS probes detected</div>
            </div>""", unsafe_allow_html=True)
        with nc2:
            st.markdown(f"""
            <div class="ip-card">
              <div class="mono" style="color:#ff9f1c;font-size:0.75rem;letter-spacing:.1em">DNS-OVER-HTTPS ATTEMPTS</div>
              <div style="font-size:2rem;font-family:'Orbitron',monospace;color:#c8dde8">{len(doh)}</div>
              <div style="color:#4a7090;font-size:0.75rem">Queries to dns.google — bypass attempts</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("#### Full DNS Log")
        st.dataframe(
            dns_df[["timestamp","src_ip","domain","service"]].sort_values("timestamp"),
            use_container_width=True, hide_index=True
        )

# ─────────────────────────────────────────────────────────────
# TAB 2 — HTTP
# ─────────────────────────────────────────────────────────────
with tabs[2]:
    http_df = df[df["category"] == "HTTP"].copy()
    
    if http_df.empty:
        st.info("No HTTP events in current filter.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("GET requests",  (http_df["method"]=="GET").sum())
        col2.metric("POST requests", (http_df["method"]=="POST").sum())
        col3.metric("Unique Hosts",  http_df["host"].nunique())
        
        st.markdown("#### Top HTTP Hosts")
        top_hosts = http_df["host"].value_counts().head(15).reset_index()
        top_hosts.columns = ["host","requests"]
        fig = px.bar(top_hosts, x="requests", y="host", orientation="h",
                     color="requests",
                     color_continuous_scale=["#0d1826","#ff9f1c"],
                     labels={"host":"Host","requests":"Requests"})
        fig.update_layout(**theme(coloraxis_showscale=False,
                          yaxis=dict(autorange="reversed", gridcolor="#1a3a5c", color="#4a7090")))
        st.plotly_chart(fig, use_container_width=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### HTTP Methods")
            method_counts = http_df["method"].value_counts().reset_index()
            method_counts.columns = ["method","count"]
            method_colors = {"GET":"#00d4ff","POST":"#ff4060","PUT":"#ff9f1c","DELETE":"#a78bfa"}
            fig2 = px.pie(method_counts, names="method", values="count",
                          color="method", color_discrete_map=method_colors, hole=0.4)
            fig2.update_layout(**theme())
            st.plotly_chart(fig2, use_container_width=True)
        
        with col_b:
            st.markdown("#### Requests per Source IP")
            ip_req = http_df["src_ip"].value_counts().reset_index()
            ip_req.columns = ["ip","requests"]
            fig3 = px.bar(ip_req, x="ip", y="requests",
                          color="requests",
                          color_continuous_scale=["#0d1826","#00d4ff"])
            fig3.update_layout(**theme(), coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)
        
        # POST body highlight
        post_df = http_df[http_df["method"] == "POST"]
        if len(post_df) > 0:
            st.markdown("#### 🔴 POST Requests (Potential Data Exfiltration)")
            for _, row in post_df.iterrows():
                st.markdown(f"""
                <div class="alert-cred">
                  ▸ {row['timestamp']}  |  {row['src_ip']} → {row['dst_ip']}
                    POST {row['path']}  Host: {row['host']}
                </div>""", unsafe_allow_html=True)
        
        st.markdown("#### Full HTTP Log")
        st.dataframe(
            http_df[["timestamp","src_ip","dst_ip","method","host","path"]].sort_values("timestamp"),
            use_container_width=True, hide_index=True
        )

# ─────────────────────────────────────────────────────────────
# TAB 3 — PER-IP PROFILE
# ─────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown("#### Select Device to Profile")
    all_src = sorted(df["src_ip"].dropna().unique())
    
    if not all_src:
        st.info("No source IPs in filtered data.")
    else:
        chosen_ip = st.selectbox("Device IP", all_src)
        ip_df = df[df["src_ip"] == chosen_ip]
        
        ip_dns  = ip_df[ip_df["category"] == "DNS"]
        ip_http = ip_df[ip_df["category"] == "HTTP"]
        ip_cred = ip_df[ip_df["category"] == "CREDS"]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Events",    len(ip_df))
        c2.metric("DNS Queries",     len(ip_dns))
        c3.metric("HTTP Requests",   len(ip_http))
        c4.metric("🚨 Credentials",  len(ip_cred))
        
        # Activity timeline
        if not ip_df.empty:
            st.markdown("#### Activity Timeline")
            ip_tl = ip_df.copy()
            ip_tl["minute"] = ip_tl["timestamp"].dt.floor("30s")
            tl = ip_tl.groupby(["minute","category"]).size().reset_index(name="count")
            fig = px.bar(tl, x="minute", y="count", color="category",
                         color_discrete_map=CAT_COLORS, barmode="stack")
            fig.update_layout(**theme())
            st.plotly_chart(fig, use_container_width=True)
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            if not ip_dns.empty:
                st.markdown("#### Queried Domains")
                dom_counts = ip_dns["domain"].value_counts().reset_index()
                dom_counts.columns = ["domain","count"]
                fig2 = px.bar(dom_counts.head(10), x="count", y="domain", orientation="h",
                              color="count",
                              color_continuous_scale=["#0d1826","#00d4ff"])
                fig2.update_layout(**theme(coloraxis_showscale=False,
                                   yaxis=dict(autorange="reversed",gridcolor="#1a3a5c",color="#4a7090")))
                st.plotly_chart(fig2, use_container_width=True)
        
        with col_right:
            if not ip_http.empty:
                st.markdown("#### HTTP Hosts Contacted")
                host_c = ip_http["host"].value_counts().reset_index()
                host_c.columns = ["host","count"]
                fig3 = px.bar(host_c.head(10), x="count", y="host", orientation="h",
                              color="count",
                              color_continuous_scale=["#0d1826","#ff9f1c"])
                fig3.update_layout(**theme(coloraxis_showscale=False,
                                   yaxis=dict(autorange="reversed",gridcolor="#1a3a5c",color="#4a7090")))
                st.plotly_chart(fig3, use_container_width=True)
        
        if not ip_cred.empty:
            st.markdown("#### 🚨 Captured Credentials")
            for _, row in ip_cred.iterrows():
                st.markdown(f"""
                <div class="alert-cred">
                  🔑  {row['timestamp']}  |  {row['src_ip']} → {row['dst_ip']}
                  <br>&nbsp;&nbsp;&nbsp;&nbsp;Field: <strong>{row['cred_field']}</strong>
                  &nbsp;|&nbsp; Value: <strong>{row['cred_value']}</strong>
                </div>""", unsafe_allow_html=True)
        
        # ── Rich dynamic app fingerprinting ──
        if not ip_dns.empty or not ip_http.empty:
            st.markdown("#### 📱 Inferred App & Device Activity")

            # Collect all unique domains + HTTP hosts for THIS IP only
            dns_domains  = set(ip_dns["domain"].dropna().str.lower().tolist())
            http_hosts   = set(ip_http["host"].dropna().str.lower().tolist()) if not ip_http.empty else set()
            all_observed = dns_domains | http_hosts

            # ── Signature database ──
            # Keywords are EXACT suffix matches (domain ends with keyword)
            # so "google.com" won't match "notgoogle.com" etc.
            SIGNATURES = [
                # ── Messaging ──
                ("💬", "WhatsApp",              "Messaging",   "High",   ["whatsapp.net","whatsapp.com","wa.me"]),
                ("📨", "Telegram",              "Messaging",   "High",   ["telegram.org","t.me","telegram.me","tgcnt.ru","telegra.ph"]),
                ("💙", "Facebook Messenger",    "Messaging",   "High",   ["messenger.com","fbcdn.net","facebook.com","fb.com"]),
                ("🐦", "Twitter / X",           "Messaging",   "High",   ["twitter.com","t.co","twimg.com","x.com","twitch.tv"]),
                ("💼", "LinkedIn",              "Messaging",   "High",   ["linkedin.com","licdn.com"]),
                ("🎮", "Discord",               "Messaging",   "High",   ["discord.com","discordapp.com","discord.gg","discordcdn.com"]),
                ("📱", "Signal",                "Messaging",   "High",   ["signal.org","signal.me","whispersystems.org"]),
                ("🟦", "Skype / Teams",         "Messaging",   "High",   ["skype.com","teams.microsoft.com","lync.com","skypeassets.com"]),
                ("📲", "Viber",                 "Messaging",   "High",   ["viber.com","vibe.com","viberlab.com"]),
                ("🟢", "Line",                  "Messaging",   "High",   ["line.me","line-scdn.net","lin.ee"]),
                # ── Social Media ──
                ("📸", "Instagram",             "Social",      "High",   ["instagram.com","cdninstagram.com","test-gateway.instagram.com"]),
                ("🎵", "TikTok",                "Social",      "High",   ["tiktok.com","tiktokcdn.com","musical.ly","byteoversea.com","sgsnssdk.com"]),
                ("👻", "Snapchat",              "Social",      "High",   ["snapchat.com","snap.com","snapcdn.com","snapkit.com"]),
                ("📌", "Pinterest",             "Social",      "High",   ["pinterest.com","pinimg.com"]),
                ("🎤", "Reddit",                "Social",      "High",   ["reddit.com","redd.it","redditmedia.com","redditstatic.com"]),
                ("👽", "Tumblr",                "Social",      "Medium", ["tumblr.com"]),
                # ── Streaming ──
                ("🎬", "YouTube",               "Streaming",   "High",   ["youtube.com","youtu.be","googlevideo.com","ytimg.com","yt3.ggpht.com"]),
                ("🎧", "Spotify",               "Streaming",   "High",   ["spotify.com","scdn.co","spotifycdn.com","audio-sp-sto.pscdn.co"]),
                ("📺", "Netflix",               "Streaming",   "High",   ["netflix.com","nflxvideo.net","nflximg.net","nflxext.com"]),
                ("🍎", "Apple Music / iCloud",  "Streaming",   "High",   ["apple.com","icloud.com","mzstatic.com","aaplimg.com","itunes.apple.com"]),
                ("🎮", "Twitch",                "Streaming",   "High",   ["jtvnw.net","twitchsvc.net","twitchapps.com"]),
                ("🎵", "Gaana / JioSaavn",      "Streaming",   "High",   ["gaana.com","jiosaavn.com","saavn.com"]),
                ("🎬", "Hotstar / Disney+",     "Streaming",   "High",   ["hotstar.com","hotostar.com","media.jio.com"]),
                ("📺", "Amazon Prime Video",    "Streaming",   "High",   ["primevideo.com","aiv-cdn.net"]),
                # ── OS / Device ──
                ("🤖", "Android Device",        "OS/Platform", "High",   ["connectivitycheck.gstatic.com","connectivitycheck.android.com","android.googleapis.com","clients3.google.com"]),
                ("🍏", "iOS / macOS Device",    "OS/Platform", "High",   ["captive.apple.com","appleiphonecell.com","airport.us","mesu.apple.com","xp.apple.com"]),
                ("🪟", "Windows Device",        "OS/Platform", "High",   ["msftconnecttest.com","msftncsi.com","windowsupdate.com","ctldl.windowsupdate.com"]),
                ("📱", "Huawei / HarmonyOS",    "OS/Platform", "High",   ["hicloud.com","huawei.com","hihonorcloud.com","connectivitycheck.platform.hicloud.com"]),
                ("🐧", "Linux / Ubuntu",        "OS/Platform", "High",   ["connectivity-check.ubuntu.com","nmcheck.gnome.org","fedoraproject.org","archlinux.org"]),
                # ── Google ──
                ("🔍", "Google Chrome / Search","Google",      "High",   ["google.com","gstatic.com","googlesyndication.com","googleusercontent.com","ggpht.com"]),
                ("📧", "Gmail",                 "Google",      "High",   ["gmail.com","mail.google.com"]),
                ("🗺️", "Google Maps",           "Google",      "High",   ["maps.google.com","maps.googleapis.com","maps.gstatic.com"]),
                ("🎮", "Google Play Store",     "Google",      "High",   ["play.googleapis.com","play.google.com","market.android.com"]),
                ("☁️", "Google Drive / Docs",   "Google",      "High",   ["drive.google.com","docs.google.com","sheets.google.com","slides.google.com"]),
                ("🔔", "Firebase Push (GCM)",   "Google",      "High",   ["mtalk.google.com","fcm.googleapis.com","fcmtoken.googleapis.com","firebaseio.com"]),
                ("📹", "Google Meet",           "Google",      "High",   ["meet.google.com","meet.googleapis.com"]),
                ("🛡️", "Google SafeBrowsing",  "Google",      "Medium", ["safebrowsing.googleapis.com","safebrowsing.google.com"]),
                # ── Microsoft ──
                ("📧", "Outlook / Hotmail",     "Microsoft",   "High",   ["outlook.com","hotmail.com","live.com","office365.com","office.com"]),
                ("☁️", "OneDrive / SharePoint", "Microsoft",   "High",   ["onedrive.live.com","sharepoint.com","1drv.ms"]),
                ("🪟", "Windows Update",        "Microsoft",   "High",   ["windowsupdate.com","update.microsoft.com","wustat.windows.com","download.windowsupdate.com"]),
                ("🤖", "Bing / Copilot",        "Microsoft",   "High",   ["bing.com","bingapis.com","bingsandbox.com"]),
                # ── Security / Privacy ──
                ("🔒", "VPN Activity",          "Security",    "Medium", ["nordvpn.com","expressvpn.com","protonvpn.com","mullvad.net","surfshark.com","openvpn.net","hidemyass.com"]),
                ("🛡️", "DNS-over-HTTPS (DoH)",  "Security",    "High",   ["dns.google","cloudflare-dns.com","doh.opendns.com","mozilla.cloudflare-dns.com","doh.cleanbrowsing.org"]),
                ("🧅", "Tor / Anonymizer",      "Security",    "High",   ["torproject.org","tor2web.org","onion.to"]),
                ("🦠", "Antivirus / Security",  "Security",    "Medium", ["kaspersky.com","avast.com","norton.com","mcafee.com","malwarebytes.com","avira.com"]),
                # ── Finance / Shopping ──
                ("🛒", "Amazon Shopping",       "Shopping",    "High",   ["amazon.com","amazon.in","ssl-images-amazon.com","images-amazon.com"]),
                ("💳", "PayPal",                "Finance",     "High",   ["paypal.com","paypalobjects.com"]),
                ("💰", "Google Pay / GPay",     "Finance",     "High",   ["pay.google.com","gpay.app"]),
                ("🏦", "SBI / HDFC / ICICI",    "Finance",     "High",   ["sbi.co.in","hdfcbank.com","icicibank.com","axisbank.com","kotak.com","paytm.com","phonepe.com"]),
                ("🛍️", "Flipkart / Meesho",     "Shopping",    "High",   ["flipkart.com","fkcdn.com","meesho.com"]),
                # ── Dev / Cloud ──
                ("🐙", "GitHub",                "Dev Tools",   "High",   ["github.com","githubusercontent.com","githubassets.com","github.io"]),
                ("🐋", "Docker",                "Dev Tools",   "High",   ["docker.com","dockerhub.io","registry-1.docker.io"]),
                ("☁️", "AWS",                   "Cloud",       "High",   ["amazonaws.com","aws.amazon.com","cloudfront.net","awsstatic.com"]),
                ("☁️", "Cloudflare",            "Cloud",       "High",   ["cloudflare.com","cloudflare-dns.com","cf-cdn.com","workers.dev"]),
                ("☁️", "Google Cloud",          "Cloud",       "High",   ["cloud.google.com","appspot.com","cloudfunctions.net","run.app"]),
                # ── Network / Infra ──
                ("📡", "mDNS / Device Discovery","Network",    "High",   ["in-addr.arpa","_dns-sd._udp","_tcp.local","_udp.local","local.arpa"]),
                ("🌐", "HTTP-only (No TLS)",    "Security",    "High",   ["httpforever.com","neverssl.com","http.badssl.com"]),
                # ── Indian Services ──
                ("📺", "Jio / JioTV",           "Indian Apps", "High",   ["jio.com","jiocinema.com","jiosaavn.com","jiocloud.com"]),
                ("🚖", "Ola / Uber",            "Indian Apps", "High",   ["olacabs.com","uber.com","ubereats.com"]),
                ("🍕", "Zomato / Swiggy",       "Indian Apps", "High",   ["zomato.com","swiggy.com","swiggycdn.com"]),
                ("📰", "NDTV / Times of India", "News",        "Medium", ["ndtv.com","timesofindia.com","hindustantimes.com","thehindu.com","indiatimes.com"]),
                ("📰", "BBC / CNN",             "News",        "Medium", ["bbc.com","bbc.co.uk","cnn.com","reuters.com","apnews.com"]),
            ]

            # ── Strict suffix-based matching ──
            matched = []
            matched_domains = set()  # track which domains were claimed by a signature

            for emoji, label, category, confidence, keywords in SIGNATURES:
                triggers = []
                for kw in keywords:
                    for d in all_observed:
                        # Exact suffix match: domain ends with the keyword
                        if d == kw or d.endswith("." + kw) or d.endswith(kw):
                            triggers.append(d)
                if triggers:
                    matched_domains.update(triggers)
                    # deduplicate triggers
                    triggers = sorted(set(triggers))
                    matched.append({
                        "emoji": emoji, "label": label,
                        "category": category, "confidence": confidence,
                        "trigger_domains": triggers,
                        "count": sum(
                            (ip_dns["domain"].str.lower() == d).sum() +
                            (ip_http["host"].str.lower() == d).sum() if not ip_http.empty
                            else (ip_dns["domain"].str.lower() == d).sum()
                            for d in triggers
                        )
                    })

            # Deduplicate by label
            seen_labels = set()
            unique_matched = []
            for m in matched:
                if m["label"] not in seen_labels:
                    seen_labels.add(m["label"])
                    unique_matched.append(m)

            # ── Unmatched / unknown domains ──
            unmatched_domains = sorted(all_observed - matched_domains)
            # filter out empty strings
            unmatched_domains = [d for d in unmatched_domains if d and len(d) > 3]

            CONF_COLOR = {"High": "#39ff14", "Medium": "#ff9f1c", "Low": "#4a7090"}

            if unique_matched:
                by_cat = defaultdict(list)
                for m in unique_matched:
                    by_cat[m["category"]].append(m)

                for cat, items in sorted(by_cat.items()):
                    st.markdown(
                        f"<div style='font-family:\"Share Tech Mono\",monospace;"
                        f"font-size:0.7rem;color:#4a7090;letter-spacing:.1em;"
                        f"text-transform:uppercase;margin:.8rem 0 .3rem'>"
                        f"── {cat} ──</div>", unsafe_allow_html=True
                    )
                    cols = st.columns(min(len(items), 3))
                    for i, item in enumerate(items):
                        trigger_str = ", ".join(item["trigger_domains"][:3])
                        if len(item["trigger_domains"]) > 3:
                            trigger_str += f"  +{len(item['trigger_domains'])-3} more"
                        conf_color = CONF_COLOR.get(item["confidence"], "#4a7090")
                        with cols[i % 3]:
                            st.markdown(f"""
                            <div class="ip-card" style="padding:.6rem .9rem;margin:.2rem 0">
                              <div style="font-size:1.3rem">{item['emoji']}</div>
                              <div style="font-family:'Exo 2',sans-serif;font-weight:600;
                                          color:#c8dde8;font-size:0.85rem">{item['label']}</div>
                              <div style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;
                                          color:{conf_color};margin:.2rem 0">
                                ● {item['confidence']} · {item['count']} events</div>
                              <div style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;
                                          color:#4a7090;word-break:break-all">{trigger_str}</div>
                            </div>""", unsafe_allow_html=True)
            else:
                st.info("No recognizable app/service signatures found for this IP.")

            # ── Show unmatched domains ──
            if unmatched_domains:
                st.markdown("---")
                st.markdown(
                    "<div style='font-family:\"Share Tech Mono\",monospace;"
                    "font-size:0.7rem;color:#ff9f1c;letter-spacing:.1em;"
                    "text-transform:uppercase;margin:.8rem 0 .3rem'>"
                    "── ❓ Unrecognised / Unknown Domains ──</div>",
                    unsafe_allow_html=True
                )
                st.caption("These domains were seen for this IP but didn't match any known signature. "
                           "Could be unknown apps, custom services, or miscellaneous traffic.")
                rows_html = "".join([
                    f"<div style='font-family:\"Share Tech Mono\",monospace;font-size:0.75rem;"
                    f"color:#c8dde8;padding:.25rem .5rem;border-left:2px solid #1a3a5c;"
                    f"margin:.2rem 0'>{d}</div>"
                    for d in unmatched_domains
                ])
                st.markdown(
                    f"<div style='max-height:200px;overflow-y:auto;background:#0d1826;"
                    f"border:1px solid #1a3a5c;border-radius:6px;padding:.5rem'>"
                    f"{rows_html}</div>",
                    unsafe_allow_html=True
                )

# ─────────────────────────────────────────────────────────────
# TAB 4 — RAW LOG
# ─────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown("#### Raw Parsed Events")
    
    search_term = st.text_input("🔍 Search events", placeholder="e.g. whatsapp, POST, 192.168.1.141 ...")
    
    display_df = df.copy()
    if search_term:
        mask = display_df.apply(
            lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1
        )
        display_df = display_df[mask]
    
    st.caption(f"Showing {len(display_df)} of {len(df)} events")
    
    def color_category(val):
        colors = {"DNS":"color:#00d4ff","HTTP":"color:#ff9f1c","CREDS":"color:#ff4060"}
        return colors.get(val, "")
    
    st.dataframe(
        display_df[["timestamp","category","src_ip","dst_ip","host","domain","method","path","raw"]]
                 .sort_values("timestamp").reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )
    
    csv = display_df.to_csv(index=False)
    st.download_button(
        "⬇️ Download Filtered CSV",
        data=csv,
        file_name="mitm_filtered_export.csv",
        mime="text/csv"
    )

# ─────────────────────────────────────────────────────────────
# TAB 5 — THREAT SUMMARY
# ─────────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown("#### 🔎 Automated Threat & Insight Summary")
    
    # ── Finding 1: Credentials
    st.markdown("---")
    has_creds = cred_count > 0
    st.markdown(f"""
    <div class="ip-card" style="border-color:{'#ff4060' if has_creds else '#1a3a5c'}">
      <span style="font-family:'Orbitron';font-size:0.85rem;color:{'#ff4060' if has_creds else '#39ff14'}">
        {'🚨 CRITICAL' if has_creds else '✅ CLEAR'} — Credential Capture
      </span><br>
      <span style="color:#c8dde8">
        {'Found ' + str(cred_count) + ' credential event(s) in plaintext HTTP traffic.' if has_creds
         else 'No credentials detected in this log.'}
      </span>
    </div>""", unsafe_allow_html=True)
    
    # ── Finding 2: Plaintext HTTP POST to known apps
    post_sensitive = df[(df["category"]=="HTTP") & (df["method"]=="POST") &
                        (df["host"].str.contains("whatsapp|facebook|instagram|gmail|yahoo",
                                                  na=False, case=False))]
    has_sensitive_post = len(post_sensitive) > 0
    st.markdown(f"""
    <div class="ip-card" style="border-color:{'#ff9f1c' if has_sensitive_post else '#1a3a5c'}">
      <span style="font-family:'Orbitron';font-size:0.85rem;color:{'#ff9f1c' if has_sensitive_post else '#39ff14'}">
        {'⚠ WARNING' if has_sensitive_post else '✅ CLEAR'} — Sensitive App POST Requests
      </span><br>
      <span style="color:#c8dde8">
        {'Detected ' + str(len(post_sensitive)) + ' POST request(s) to sensitive services over plaintext HTTP.' if has_sensitive_post
         else 'No sensitive app POST requests on plaintext HTTP.'}
      </span>
    </div>""", unsafe_allow_html=True)
    
    # ── Finding 3: DoH bypass
    doh_df = df[(df["category"]=="DNS") & (df["domain"].str.contains("dns.google", na=False))]
    has_doh = len(doh_df) > 0
    st.markdown(f"""
    <div class="ip-card" style="border-color:{'#ff9f1c' if has_doh else '#1a3a5c'}">
      <span style="font-family:'Orbitron';font-size:0.85rem;color:{'#ff9f1c' if has_doh else '#39ff14'}">
        {'⚠ INFO' if has_doh else '✅ CLEAR'} — DNS-over-HTTPS Probe
      </span><br>
      <span style="color:#c8dde8">
        {'Device queried dns.google — possible attempt to bypass local DNS snooping.' if has_doh
         else 'No DoH bypass attempts detected.'}
      </span>
    </div>""", unsafe_allow_html=True)
    
    # ── Finding 4: Most active IP
    if not df["src_ip"].dropna().empty:
        top_ip = df["src_ip"].value_counts().idxmax()
        top_ip_count = df["src_ip"].value_counts().max()
        st.markdown(f"""
        <div class="ip-card">
          <span style="font-family:'Orbitron';font-size:0.85rem;color:#00d4ff">📡 Most Active Device</span><br>
          <span style="color:#c8dde8">
            <strong style="color:#00d4ff">{top_ip}</strong> generated {top_ip_count} captured events.
          </span>
        </div>""", unsafe_allow_html=True)
    
    # ── Finding 5: Per-IP fingerprint table using full signature DB ──
    st.markdown("#### 📱 Device & App Fingerprinting (all IPs)")
    dns_df2 = df[df["category"] == "DNS"]
    http_df2 = df[df["category"] == "HTTP"]

    # Reuse same SIGNATURES defined in per-IP tab
    summary_rows = []
    for ip in sorted(df["src_ip"].dropna().unique()):
        ip_doms  = set(dns_df2[dns_df2["src_ip"]==ip]["domain"].dropna().str.lower())
        ip_hosts = set(http_df2[http_df2["src_ip"]==ip]["host"].dropna().str.lower())
        all_obs  = ip_doms | ip_hosts
        matched_labels = []
        for emoji, label, category, confidence, keywords in SIGNATURES:
            for kw in keywords:
                if any(kw in d for d in all_obs):
                    matched_labels.append(f"{emoji} {label}")
                    break
        if matched_labels:
            summary_rows.append({
                "IP Address": ip,
                "Detected Apps / Services": "  ·  ".join(matched_labels),
                "Total Signatures": len(matched_labels),
            })

    if summary_rows:
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Insufficient data for device fingerprinting.")
    
    # ── Session summary
    if not df["timestamp"].dropna().empty:
        session_start = df["timestamp"].min()
        session_end   = df["timestamp"].max()
        duration      = (session_end - session_start).seconds
        st.markdown(f"""
        <div class="ip-card" style="margin-top:1rem">
          <span style="font-family:'Orbitron';font-size:0.85rem;color:#a78bfa">📅 Session Summary</span><br>
          <span class="mono" style="color:#c8dde8">
            Start: {session_start} &nbsp;|&nbsp; End: {session_end}
            &nbsp;|&nbsp; Duration: {duration // 60}m {duration % 60}s
            &nbsp;|&nbsp; Avg rate: {total / max(duration, 1) * 60:.1f} events/min
          </span>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LIVE AUTO-REFRESH
# ─────────────────────────────────────────────────────────────

if live_mode and live_path and Path(live_path).exists():
    st.markdown("---")
    last_col, next_col = st.columns([3, 1])
    with last_col:
        mtime = datetime.fromtimestamp(Path(live_path).stat().st_mtime)
        st.caption(f"🕒 Last refresh: {datetime.now().strftime('%H:%M:%S')}  "
                   f"|  Log last modified: {mtime.strftime('%H:%M:%S')}  "
                   f"|  Total events parsed: {len(df_all)}")
    with next_col:
        if st.button("🔄 Refresh Now"):
            st.rerun()

    # Auto-rerun after the selected interval
    time.sleep(refresh_interval)
    st.rerun()