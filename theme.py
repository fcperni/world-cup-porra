"""Identidad visual de "Pa porra la mía" — estética de retransmisión/marcador.

Inyecta tipografías (Big Shoulders Display · Hanken Grotesk · Spline Sans Mono),
paleta de tinta de estadio con acento lima, fondo con grano y focos, y re-estiliza
los componentes nativos de Streamlit. Se llama desde ``ui_common.configure_page``.
"""

from __future__ import annotations

import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@500;600;700;800;900&family=Hanken+Grotesk:wght@400;500;600;700;800&family=Spline+Sans+Mono:wght@400;500;600;700&display=swap');

:root{
  --ink:#0a0e13; --ink2:#0c1118;
  --surface:#141c25; --surface2:#1b2632; --line:#27333f;
  --text:#eaf1f3; --muted:#8a99a6;
  --lime:#c2f23c; --lime-dim:#9ec62f;
  --coral:#ff5a3c; --gold:#f3c44b;
  --shadow:0 22px 48px -26px rgba(0,0,0,.85);
}

/* ---------- fondo: tinta + focos + grano ---------- */
.stApp{
  background:
    radial-gradient(1100px 560px at 82% -12%, rgba(194,242,60,.11), transparent 58%),
    radial-gradient(820px 460px at -5% 0%, rgba(255,90,60,.07), transparent 55%),
    linear-gradient(180deg,#0a0e13 0%, #0b1016 100%);
  color:var(--text);
}
.stApp::before{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:.045;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
[data-testid="stHeader"]{ background:transparent; }
.block-container{ position:relative; z-index:1; padding-top:2.4rem; }

/* ---------- tipografía ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"]{
  font-family:'Hanken Grotesk','Segoe UI',sans-serif;
}
.stApp h1, .stApp h2, .stApp h3{
  font-family:'Big Shoulders Display','Hanken Grotesk',sans-serif;
  text-transform:uppercase; letter-spacing:.012em; line-height:.98;
}
.stApp h1{ font-weight:800; font-size:2.5rem; }
.stApp h2{ font-weight:700; }
.stApp h3{ font-weight:700; letter-spacing:.03em; }
[data-testid="stMarkdownContainer"] p{ color:var(--text); }
[data-testid="stCaptionContainer"], .stCaption{ color:var(--muted) !important; }

/* ---------- métricas como fichas de marcador ---------- */
[data-testid="stMetric"]{
  background:linear-gradient(165deg,var(--surface) 0%, var(--ink2) 100%);
  border:1px solid var(--line); border-radius:14px; padding:16px 18px 14px;
  box-shadow:var(--shadow); overflow:hidden; position:relative;
}
[data-testid="stMetric"]::before{
  content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--lime);
}
[data-testid="stMetricLabel"] p{
  text-transform:uppercase; letter-spacing:.1em; font-size:.7rem; font-weight:700; color:var(--muted);
}
[data-testid="stMetricValue"]{
  font-family:'Spline Sans Mono',monospace; font-weight:600; letter-spacing:-.02em;
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#0c131b 0%, #090d12 100%);
  border-right:1px solid var(--line);
}
[data-testid="stSidebarNav"] li a span{
  font-family:'Big Shoulders Display',sans-serif; text-transform:uppercase;
  letter-spacing:.04em; font-size:1.02rem; font-weight:600;
}
[data-testid="stSidebarNav"] li a:hover{ background:rgba(194,242,60,.08); }

/* ---------- botones ---------- */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:11px; font-family:'Big Shoulders Display',sans-serif; font-weight:700;
  text-transform:uppercase; letter-spacing:.05em; font-size:1.05rem; padding:.55rem 1.2rem;
  min-height:44px;  /* objetivo táctil cómodo en móvil */
  transition:transform .14s ease, box-shadow .14s ease, filter .14s ease, border-color .14s ease;
}
/* primario: lima con texto tinta (alto contraste) */
button[kind*="primary"], button[data-testid*="primary"]{ background:var(--lime) !important; border:0 !important; }
button[kind*="primary"] *, button[data-testid*="primary"] *{ color:#0a0e13 !important; }
button[kind*="primary"]:hover, button[data-testid*="primary"]:hover{ box-shadow:0 12px 26px -10px rgba(194,242,60,.55); filter:brightness(1.05); }
/* secundario: fantasma oscuro con texto claro (legible) */
button[kind*="secondary"], button[data-testid*="secondary"]{ background:var(--surface) !important; border:1px solid var(--line) !important; }
button[kind*="secondary"] *, button[data-testid*="secondary"] *{ color:var(--text) !important; }
button[kind*="secondary"]:hover, button[data-testid*="secondary"]:hover{ border-color:var(--lime) !important; background:var(--surface2) !important; }
button[kind*="secondary"]:hover *, button[data-testid*="secondary"]:hover *{ color:var(--lime) !important; }
.stButton>button:hover, .stFormSubmitButton>button:hover, .stDownloadButton>button:hover{ transform:translateY(-2px); }
.stButton>button:active, .stFormSubmitButton>button:active{ transform:translateY(0); }

/* ---------- pestañas (estilo pastilla/segmento, bien separadas) ---------- */
.stTabs [data-baseweb="tab-list"]{
  gap:10px; flex-wrap:wrap; border-bottom:0; margin-bottom:.5rem; background:transparent;
}
.stTabs [data-baseweb="tab"]{
  font-family:'Big Shoulders Display',sans-serif; text-transform:uppercase;
  letter-spacing:.06em; font-size:1.02rem; color:var(--muted);
  background:var(--surface); border:1px solid var(--line); border-radius:10px;
  padding:.45rem 1.05rem; height:auto; transition:color .14s ease, background .14s ease, border-color .14s ease;
}
.stTabs [data-baseweb="tab"]:hover{ color:var(--text); border-color:var(--lime-dim); background:var(--surface2); }
.stTabs [data-baseweb="tab"][aria-selected="true"]{ background:var(--lime); border-color:var(--lime); }
.stTabs [data-baseweb="tab"][aria-selected="true"], .stTabs [data-baseweb="tab"][aria-selected="true"] *{ color:#0a0e13 !important; }
.stTabs [data-baseweb="tab-highlight"]{ background:transparent !important; height:0 !important; }
.stTabs [data-baseweb="tab-border"]{ background:transparent !important; height:0 !important; }

/* ---------- tablas / inputs ---------- */
[data-testid="stDataFrame"], [data-testid="stTable"]{
  border:1px solid var(--line); border-radius:12px; overflow:hidden;
}
[data-testid="stTable"] table{ font-variant-numeric:tabular-nums; }
[data-baseweb="select"]>div, .stTextInput input, .stNumberInput input{
  border-radius:10px !important; border-color:var(--line) !important;
}
[data-testid="stAlert"]{ border-radius:12px; border:1px solid var(--line); }

/* ---------- componentes propios (home) ---------- */
.hero{ position:relative; padding:.4rem 0 1.6rem; }
.hero-kicker{
  font-family:'Spline Sans Mono',monospace; font-size:.8rem; letter-spacing:.22em;
  text-transform:uppercase; color:var(--lime); margin-bottom:.5rem;
}
.hero-title{
  font-family:'Big Shoulders Display',sans-serif; font-weight:900; text-transform:uppercase;
  font-size:clamp(3.2rem,9vw,6.2rem); line-height:.84; letter-spacing:.005em; margin:0;
  color:var(--text); text-shadow:0 2px 0 rgba(0,0,0,.25);
}
.hero-title .acc{ color:var(--lime); -webkit-text-stroke:0; }
.hero-sub{ color:var(--muted); margin-top:.7rem; font-size:1.02rem; max-width:46ch; }
.hero-rule{ height:3px; width:120px; background:linear-gradient(90deg,var(--lime),transparent); margin-top:1rem; border-radius:3px; }

.board{ display:flex; flex-direction:column; gap:8px; margin-top:.3rem; }
.board-row{
  display:grid; grid-template-columns:46px 1fr 130px; align-items:center; gap:14px;
  background:linear-gradient(165deg,var(--surface) 0%, var(--ink2) 100%);
  border:1px solid var(--line); border-radius:13px; padding:13px 18px;
  animation:rise .5s cubic-bezier(.2,.7,.2,1) both;
}
.board-row .rank{
  font-family:'Spline Sans Mono',monospace; font-weight:600; font-size:1.15rem;
  color:var(--muted); text-align:center;
}
.board-row .who{
  font-family:'Big Shoulders Display',sans-serif; font-weight:700; text-transform:uppercase;
  font-size:1.5rem; letter-spacing:.02em;
}
.board-row .meta{ display:flex; flex-direction:column; gap:6px; }
.board-row .barwrap{ height:5px; background:rgba(255,255,255,.06); border-radius:4px; overflow:hidden; }
.board-row .bar{ display:block; height:100%; background:linear-gradient(90deg,var(--lime-dim),var(--lime)); border-radius:4px; }
.board-row .pts{ font-family:'Spline Sans Mono',monospace; font-weight:600; font-size:1.35rem; text-align:right; }
.board-row .pts small{ color:var(--muted); font-size:.7rem; font-weight:500; margin-left:3px; }
.board-row.r1{ border-color:rgba(243,196,75,.5); box-shadow:0 0 0 1px rgba(243,196,75,.18), var(--shadow); }
.board-row.r1 .rank{ color:var(--gold); } .board-row.r1 .pts{ color:var(--gold); }
.board-row.r1 .bar{ background:linear-gradient(90deg,#caa23a,var(--gold)); }
.board-row.r2 .rank{ color:#cdd6dd; } .board-row.r3 .rank{ color:#d6925a; }

.medal{ font-size:1.1rem; }
@keyframes rise{ from{ opacity:0; transform:translateY(14px); } to{ opacity:1; transform:none; } }

.empty-card{
  background:linear-gradient(165deg,var(--surface) 0%, var(--ink2) 100%);
  border:1px solid var(--line); border-left:3px solid var(--lime); border-radius:14px;
  padding:1.4rem 1.6rem; box-shadow:var(--shadow);
}
.empty-card .big{ font-family:'Big Shoulders Display',sans-serif; text-transform:uppercase; font-size:1.6rem; font-weight:800; }
.empty-card .sub{ color:var(--muted); margin-top:.3rem; }

.navgrid{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin-top:.4rem; }
.navcard{
  background:linear-gradient(165deg,var(--surface) 0%, var(--ink2) 100%);
  border:1px solid var(--line); border-radius:14px; padding:1.1rem 1.2rem;
  transition:transform .15s ease, border-color .15s ease; box-shadow:var(--shadow);
}
.navcard:hover{ transform:translateY(-3px); border-color:rgba(194,242,60,.45); }
.navcard .ico{ font-size:1.5rem; }
.navcard .t{ font-family:'Big Shoulders Display',sans-serif; text-transform:uppercase; font-weight:700; font-size:1.25rem; margin-top:.3rem; }
.navcard .d{ color:var(--muted); font-size:.9rem; margin-top:.2rem; line-height:1.35; }

.section-label{
  font-family:'Spline Sans Mono',monospace; text-transform:uppercase; letter-spacing:.2em;
  font-size:.75rem; color:var(--muted); margin:1.6rem 0 .6rem; display:flex; align-items:center; gap:10px;
}
.section-label::after{ content:''; flex:1; height:1px; background:var(--line); }

/* ---------- lista de partidos (Calendario) ---------- */
.fx{ display:flex; flex-direction:column; gap:7px; }
.fx-day{
  font-family:'Spline Sans Mono',monospace; text-transform:uppercase; letter-spacing:.18em;
  font-size:.72rem; color:var(--lime); margin:1.3rem 0 .35rem;
}
.fx-row{
  display:grid; grid-template-columns:96px 1fr 78px 1fr; align-items:center; gap:12px;
  background:linear-gradient(165deg,var(--surface) 0%, var(--ink2) 100%);
  border:1px solid var(--line); border-radius:11px; padding:9px 15px;
}
.fx-tag{ font-family:'Spline Sans Mono',monospace; font-size:.66rem; letter-spacing:.05em;
  color:var(--muted); text-transform:uppercase; }
.fx-team{ font-family:'Big Shoulders Display',sans-serif; text-transform:uppercase;
  font-size:1.2rem; letter-spacing:.01em; display:flex; align-items:center; gap:9px; min-width:0; }
.fx-team.home{ justify-content:flex-end; text-align:right; }
.fx-team .fl{ font-size:1.3rem; line-height:1; }
.fx-team .nm{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.fx-team.ph .nm{ color:var(--muted); font-size:.92rem; font-family:'Spline Sans Mono',monospace; text-transform:none; }
.fx-score{ font-family:'Spline Sans Mono',monospace; font-weight:600; text-align:center;
  border-radius:8px; padding:5px 0; font-size:1.02rem; }
.fx-score.played{ background:var(--lime); color:#0a0e13; }
.fx-score.pending{ color:var(--muted); border:1px solid var(--line); font-size:.78rem; padding:4px 0; }
.fx-score .pen{ display:block; font-size:.58rem; letter-spacing:.04em; }
@media (max-width:640px){
  .fx-row{ grid-template-columns:1fr 58px 1fr; gap:8px; padding:8px 11px; }
  .fx-tag{ display:none; }
  .fx-team{ font-size:1rem; } .fx-team .fl{ font-size:1.05rem; }
}

/* ---------- móvil ---------- */
@media (max-width:820px){
  /* las columnas de Streamlit se apilan a ancho completo (legible en móvil) */
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap; gap:.55rem; }
  [data-testid="stColumn"]{ flex:1 1 100% !important; min-width:100% !important; }
}
@media (max-width:640px){
  .block-container{ padding:1.3rem .9rem 3rem; }
  .stApp h1{ font-size:2rem; }
  .hero{ padding-bottom:1rem; }
  .hero-title{ font-size:clamp(2.7rem,16vw,3.6rem); }
  .hero-kicker{ font-size:.68rem; letter-spacing:.16em; }
  .hero-sub{ font-size:.95rem; }
  .board-row{ grid-template-columns:30px 1fr 78px; gap:10px; padding:11px 13px; }
  .board-row .who{ font-size:1.18rem; }
  .board-row .pts{ font-size:1.05rem; }
  .board-row .pts small{ display:block; margin:0; line-height:1; }
  .navgrid{ grid-template-columns:1fr; }
  [data-testid="stMetric"]{ padding:13px 14px 11px; }
  [data-testid="stMetricValue"]{ font-size:1.5rem; }
  .stTabs [data-baseweb="tab"]{ font-size:.95rem; letter-spacing:.03em; }
  /* tablas: permitir scroll horizontal sin romper el layout */
  [data-testid="stDataFrame"]{ overflow-x:auto; }
}
"""


def inject_theme() -> None:
    st.markdown("<style>" + _CSS + "</style>", unsafe_allow_html=True)
