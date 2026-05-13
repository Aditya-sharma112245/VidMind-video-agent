"""
VidMind AI  ·  app.py  — ULTRA PREMIUM UI EDITION v2
Cinematic aurora + morphing color Streamlit frontend.
FIXED: action items / key decisions / questions counts now use _lines()
       so "No X found." placeholder text doesn't inflate the count.

Run:
    pip install yt-dlp streamlit langchain-community langchain-mistralai \
                langchain-text-splitters sentence-transformers chromadb \
                openai-whisper python-dotenv
    streamlit run app.py
"""

import sys, time, traceback, re
import streamlit as st

st.set_page_config(
    page_title="VidMind AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── dependency check ────────────────────────────────────────────────────────
REQUIRED = {
    "yt_dlp": "yt-dlp",
    "whisper": "openai-whisper",
    "langchain_community": "langchain-community",
    "langchain_mistralai": "langchain-mistralai",
    "chromadb": "chromadb",
    "sentence_transformers": "sentence-transformers",
    "dotenv": "python-dotenv",
}
missing = []
for mod, pkg in REQUIRED.items():
    try:
        __import__(mod)
    except ImportError:
        missing.append(pkg)

if missing:
    st.error(f"Missing deps — run: pip install {' '.join(missing)}")
    st.stop()

from dotenv import load_dotenv
load_dotenv()

def _lazy_pipeline():
    from utils.audio_processor import process_input
    from core.transcriber      import transcribe_all
    from core.summarizer       import summarize, generate_title
    from core.extractor        import (extract_action_items,
                                       extract_key_decisions,
                                       extract_questions)
    from core.rag_engine       import build_rag_chain, ask_question
    return (process_input, transcribe_all,
            summarize, generate_title,
            extract_action_items, extract_key_decisions, extract_questions,
            build_rag_chain, ask_question)

# ────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS  — Cinematic Aurora UI v2
# ────────────────────────────────────────────────────────────────────────────
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&family=Manrope:wght@300;400;500;600;700&display=swap');

:root {
  --void:    #02020d;
  --ink:     #06061a;
  --glass:   rgba(255,255,255,.045);
  --rim:     rgba(255,255,255,.09);
  --glow1:   #7c3aed;
  --glow2:   #06b6d4;
  --glow3:   #f472b6;
  --glow4:   #10b981;
  --glow5:   #f59e0b;
  --txt:     #e2e8f8;
  --muted:   rgba(226,232,248,.45);
  --mono:    'DM Mono', monospace;
  --head:    'Syne', sans-serif;
  --body:    'Manrope', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
  background: var(--void) !important;
  color: var(--txt) !important;
  font-family: var(--body) !important;
}

/* ── Living aurora background ── */
[data-testid="stAppViewContainer"] { position: relative; overflow: hidden; }
[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after {
  content: ''; position: fixed; border-radius: 50%;
  filter: blur(130px); pointer-events: none; z-index: 0;
}
[data-testid="stAppViewContainer"]::before {
  width: 1000px; height: 800px; top: -250px; left: -250px;
  background: radial-gradient(ellipse, rgba(124,58,237,.3) 0%, rgba(6,182,212,.18) 50%, transparent 70%);
  animation: aurora1 16s ease-in-out infinite alternate;
}
[data-testid="stAppViewContainer"]::after {
  width: 800px; height: 700px; bottom: -200px; right: -200px;
  background: radial-gradient(ellipse, rgba(244,114,182,.25) 0%, rgba(16,185,129,.16) 50%, transparent 70%);
  animation: aurora2 20s ease-in-out infinite alternate;
}

@keyframes aurora1 {
  0%   { transform: translate(0,0) scale(1);     opacity:.7; }
  33%  { transform: translate(140px,100px) scale(1.18); opacity:1; }
  66%  { transform: translate(-70px,180px) scale(.9);   opacity:.6; }
  100% { transform: translate(90px,-70px) scale(1.12);  opacity:.9; }
}
@keyframes aurora2 {
  0%   { transform: translate(0,0) scale(1);      opacity:.6; }
  40%  { transform: translate(-120px,-90px) scale(1.25); opacity:.95; }
  75%  { transform: translate(70px,110px) scale(.88);    opacity:.7; }
  100% { transform: translate(-50px,70px) scale(1.08);   opacity:.85; }
}

[data-testid="stAppViewBlockContainer"] { position: relative; z-index: 1; }
[data-testid="stAppViewBlockContainer"]::before {
  content: ''; position: fixed;
  width: 600px; height: 600px; top: 40%; left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(234,179,8,.07) 0%, rgba(124,58,237,.05) 50%, transparent 70%);
  filter: blur(90px); pointer-events: none; z-index: 0;
  animation: aurora3 24s ease-in-out infinite alternate;
}
@keyframes aurora3 {
  0%   { opacity:.4; transform:translate(-50%,-50%) scale(1); }
  50%  { opacity:.9; transform:translate(-40%,-60%) scale(1.4); }
  100% { opacity:.5; transform:translate(-60%,-45%) scale(.85); }
}

/* ── Streamlit cleanup ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { visibility: hidden !important; display: none !important; }

.block-container { padding: 1.2rem 2.5rem 6rem !important; max-width: 1380px !important; position: relative; z-index:1; }

/* ── Noise grain overlay ── */
.block-container::after {
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.025'/%3E%3C/svg%3E");
  opacity:.45;
}

/* ══════════════════════════════════════════════
   HERO
══════════════════════════════════════════════ */
.vm-hero { text-align:center; padding:4rem 1rem 2.5rem; position:relative; }

/* Animated ring halo behind title */
.vm-hero-ring {
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  width:600px; height:600px; border-radius:50%; pointer-events:none;
  background: conic-gradient(from 0deg,
    transparent 0%, rgba(124,58,237,.08) 20%,
    rgba(6,182,212,.1) 40%, transparent 60%,
    rgba(244,114,182,.06) 80%, transparent 100%);
  animation: spin 22s linear infinite;
  filter: blur(2px);
  z-index:0;
}
.vm-hero-ring2 {
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  width:420px; height:420px; border-radius:50%; pointer-events:none;
  border: 1px solid rgba(124,58,237,.12);
  animation: ringPulse 5s ease-in-out infinite;
  z-index:0;
}
.vm-hero-ring3 {
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  width:280px; height:280px; border-radius:50%; pointer-events:none;
  border: 1px solid rgba(6,182,212,.1);
  animation: ringPulse 5s ease-in-out infinite .8s;
  z-index:0;
}
@keyframes ringPulse {
  0%,100% { opacity:.4; transform:translate(-50%,-50%) scale(1); }
  50%      { opacity:.9; transform:translate(-50%,-50%) scale(1.04); }
}

.vm-badge {
  position:relative; z-index:1;
  display:inline-flex; align-items:center; gap:.6rem;
  background: rgba(255,255,255,.05);
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 999px; padding:.4rem 1.2rem;
  font-family:var(--mono); font-size:.68rem; letter-spacing:.16em; text-transform:uppercase;
  color: var(--muted); margin-bottom: 2rem;
  animation: fadeUp .7s ease both;
  backdrop-filter: blur(10px);
}
.vm-badge-dot {
  width:7px; height:7px; border-radius:50%;
  background: conic-gradient(from 0deg, #7c3aed, #06b6d4, #f472b6, #10b981, #7c3aed);
  animation: spin 3s linear infinite;
  flex-shrink:0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.vm-title {
  position:relative; z-index:1;
  font-family: var(--head) !important;
  font-size: clamp(3.8rem,9vw,7rem) !important;
  font-weight: 800 !important;
  letter-spacing: -.045em !important;
  line-height: 1 !important;
  background: linear-gradient(135deg,
    #fff 0%, #c4b5fd 20%, #67e8f9 40%, #f9a8d4 60%, #6ee7b7 80%, #fcd34d 100%);
  background-size: 400% 400%;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  animation: fadeUp .7s .1s ease both, chromaShift 9s ease infinite;
  /* subtle text glow via drop-shadow filter */
  filter: drop-shadow(0 0 60px rgba(124,58,237,.35));
}

/* Tagline emoji icon */
.vm-icon {
  position:relative; z-index:1;
  font-size:2.8rem; margin-bottom:.5rem; display:block;
  animation: fadeUp .7s .05s ease both, iconFloat 4s ease-in-out infinite;
}
@keyframes iconFloat {
  0%,100% { transform:translateY(0) rotate(-2deg); }
  50%      { transform:translateY(-8px) rotate(2deg); }
}

@keyframes chromaShift {
  0%, 100% { background-position: 0% 50%; }
  50%       { background-position: 100% 50%; }
}

.vm-sub {
  position:relative; z-index:1;
  margin-top: 1.2rem; font-size: 1.05rem; font-weight: 300;
  color: var(--muted); max-width: 540px;
  margin-left: auto; margin-right: auto; line-height: 1.75;
  animation: fadeUp .7s .25s ease both;
}

/* Pill chips below sub */
.vm-chips {
  position:relative; z-index:1;
  display:flex; justify-content:center; flex-wrap:wrap; gap:.5rem;
  margin-top:1.2rem; animation: fadeUp .7s .35s ease both;
}
.vm-chip {
  display:inline-flex; align-items:center; gap:.4rem;
  background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.1);
  border-radius:999px; padding:.28rem .9rem;
  font-size:.72rem; font-family:var(--mono); color:var(--muted);
  letter-spacing:.08em;
  transition:all .25s;
}
.vm-chip:hover {
  background:rgba(124,58,237,.15); border-color:rgba(124,58,237,.4);
  color:#c4b5fd; transform:translateY(-1px);
}
.vm-chip-dot {
  width:5px; height:5px; border-radius:50%;
  display:inline-block;
}

@keyframes fadeUp {
  from { opacity:0; transform:translateY(20px); }
  to   { opacity:1; transform:none; }
}

/* Shimmering divider */
.vm-hr {
  height: 1px; margin: 2.2rem 0; position: relative; overflow: visible;
  background: linear-gradient(90deg, transparent, rgba(124,58,237,.55), rgba(6,182,212,.55), rgba(244,114,182,.45), transparent);
}
.vm-hr::after {
  content: ''; position: absolute; top: -3px; left: 0; right: 0; height: 7px;
  background: inherit; filter: blur(5px); opacity:.5;
}
/* Moving shimmer particle on divider */
.vm-hr::before {
  content:''; position:absolute; top:-3px; left:-5%; width:10%;
  height:7px; border-radius:4px;
  background: linear-gradient(90deg, transparent, #fff, transparent);
  animation: hrShimmer 4s ease-in-out infinite;
  filter:blur(2px); opacity:.6;
}
@keyframes hrShimmer {
  0%   { left:-10%; opacity:0; }
  10%  { opacity:.6; }
  90%  { opacity:.6; }
  100% { left:105%; opacity:0; }
}

/* ── Input labels ── */
.vm-label {
  font-family: var(--mono); font-size: .65rem; letter-spacing: .18em;
  text-transform: uppercase; color: var(--muted); margin-bottom: .45rem;
  display: block;
}

/* ── Inputs override ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
  background: rgba(255,255,255,.04) !important;
  border: 1px solid var(--rim) !important;
  border-radius: 16px !important;
  color: var(--txt) !important;
  font-family: var(--body) !important;
  font-size: .95rem !important;
  padding: .85rem 1.15rem !important;
  transition: border-color .25s, box-shadow .25s !important;
  backdrop-filter: blur(10px) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: rgba(124,58,237,.75) !important;
  box-shadow: 0 0 0 3px rgba(124,58,237,.18), 0 0 24px rgba(124,58,237,.14) !important;
  outline: none !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label { color: var(--muted) !important; font-size:.82rem !important; }

/* Selectbox */
[data-baseweb="select"] > div {
  background: rgba(255,255,255,.04) !important;
  border: 1px solid var(--rim) !important;
  border-radius: 16px !important;
  color: var(--txt) !important;
  backdrop-filter: blur(10px) !important;
}
[data-baseweb="popover"] li { background: #0c0c22 !important; color: var(--txt) !important; }
[data-baseweb="popover"] li:hover { background: rgba(124,58,237,.2) !important; }

/* ── Main CTA button ── */
.stButton > button {
  position: relative; overflow: hidden;
  background: transparent !important;
  border: 1px solid rgba(124,58,237,.65) !important;
  border-radius: 16px !important;
  color: #fff !important;
  font-family: var(--head) !important;
  font-size: .9rem !important;
  font-weight: 700 !important;
  letter-spacing: .07em !important;
  padding: .78rem 2.2rem !important;
  transition: all .28s !important;
  z-index: 1;
}
.stButton > button::before {
  content: ''; position: absolute; inset: 0; z-index: -1;
  background: linear-gradient(135deg, rgba(124,58,237,.65), rgba(6,182,212,.45));
  opacity: 0; transition: opacity .28s;
}
.stButton > button::after {
  content: ''; position: absolute; inset: -1px; border-radius: 16px;
  background: linear-gradient(135deg, #7c3aed, #06b6d4, #f472b6, #10b981);
  background-size: 300% 300%;
  animation: chromaShift 5s ease infinite;
  z-index: -2; padding: 1px;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
}
.stButton > button:hover::before { opacity: 1; }
.stButton > button:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 14px 44px rgba(124,58,237,.45), 0 0 24px rgba(6,182,212,.22) !important;
  border-color: transparent !important;
}
.stButton > button:active { transform: translateY(0) scale(.97) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(255,255,255,.025) !important;
  border: 1px solid var(--rim) !important;
  border-radius: 18px !important;
  padding: 5px 6px !important; gap: 3px !important;
  backdrop-filter: blur(14px) !important;
  flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 13px !important; color: var(--muted) !important;
  font-family: var(--body) !important; font-size: .84rem !important;
  font-weight: 500 !important; padding: .52rem 1.2rem !important;
  border: none !important; background: transparent !important;
  transition: all .2s !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg,rgba(124,58,237,.6),rgba(6,182,212,.35)) !important;
  color: #fff !important;
  box-shadow: 0 2px 18px rgba(124,58,237,.4) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 2rem !important; }

/* ── Progress ── */
.stProgress > div > div > div > div {
  background: linear-gradient(90deg,#7c3aed,#06b6d4,#f472b6,#10b981) !important;
  background-size: 300% 100% !important;
  border-radius: 999px !important;
  animation: progressShimmer 2.5s linear infinite !important;
  transition: width .4s ease !important;
}
@keyframes progressShimmer {
  0%   { background-position: 100% 0; }
  100% { background-position:   0% 0; }
}

/* ── Glass card ── */
.vm-card {
  background: rgba(255,255,255,.035);
  border: 1px solid var(--rim);
  border-radius: 24px;
  padding: 1.8rem 2rem;
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  position: relative; overflow: hidden;
  transition: border-color .3s, box-shadow .3s;
}
.vm-card::before {
  content: ''; position: absolute; inset: 0; border-radius: 24px;
  background: linear-gradient(135deg, rgba(255,255,255,.07) 0%, transparent 55%);
  pointer-events: none;
}
.vm-card:hover { border-color: rgba(124,58,237,.35); box-shadow: 0 8px 52px rgba(124,58,237,.13); }

/* ── Step tracker ── */
.vm-steps { display:flex; flex-direction:column; gap:.7rem; }
.vm-step  { display:flex; align-items:center; gap:.9rem; }
.vm-node  {
  width:28px; height:28px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:.62rem; font-weight:700; transition:all .35s;
}
.vm-node.idle   { background:rgba(255,255,255,.04); border:1px solid var(--rim); }
.vm-node.active {
  background: conic-gradient(from 0deg, #7c3aed, #06b6d4, #f472b6, #10b981, #7c3aed);
  animation: spin 1.3s linear infinite, pulseNode 1.3s ease infinite;
  border: none;
}
.vm-node.done {
  background: linear-gradient(135deg,rgba(16,185,129,.35),rgba(6,182,212,.22));
  border: 1px solid rgba(16,185,129,.65); color:#34d399;
}
@keyframes pulseNode {
  0%,100% { box-shadow:0 0 8px rgba(124,58,237,.55); }
  50%      { box-shadow:0 0 22px rgba(6,182,212,.75); }
}
.vm-step-label { font-size:.84rem; transition:color .3s; font-family:var(--body); }
.vm-step-label.idle   { color:var(--muted); }
.vm-step-label.active { color:#a5b4fc; font-weight:600; }
.vm-step-label.done   { color:#34d399; }

/* ── Spinner ── */
.vm-spinner {
  width:72px; height:72px; margin:0 auto 1.2rem; border-radius:50%; position:relative;
  background: conic-gradient(from 0deg, transparent 65%, #7c3aed 78%, #06b6d4 88%, #f472b6 96%, transparent 100%);
  animation: spin 1s linear infinite;
}
.vm-spinner::before {
  content:''; position:absolute; inset:5px; border-radius:50%; background:var(--void);
}
.vm-spinner::after {
  content:''; position:absolute; inset:-3px; border-radius:50%;
  background: conic-gradient(from 180deg, transparent 65%, rgba(244,114,182,.3) 80%, transparent 100%);
  animation: spin 1.8s linear infinite reverse;
}

/* ── Metric strip ── */
.vm-metrics { display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:2rem; }
.vm-mbox {
  flex:1; min-width:140px;
  background: rgba(255,255,255,.03);
  border: 1px solid var(--rim);
  border-radius: 20px; padding: 1.2rem 1.4rem; text-align:center;
  position:relative; overflow:hidden; transition:all .3s;
}
.vm-mbox:hover { border-color:rgba(124,58,237,.45); transform:translateY(-3px); box-shadow:0 12px 36px rgba(124,58,237,.14); }
.vm-mbox::before {
  content:''; position:absolute; inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.06) 0%,transparent 60%);
  pointer-events:none;
}
/* Animated gradient border on hover */
.vm-mbox::after {
  content:''; position:absolute; inset:-1px; border-radius:20px; z-index:-1;
  background: linear-gradient(135deg, rgba(124,58,237,.5), rgba(6,182,212,.3), rgba(244,114,182,.3));
  background-size:200% 200%; animation:chromaShift 5s ease infinite;
  opacity:0; transition:opacity .3s;
}
.vm-mbox:hover::after { opacity:1; }
.vm-mval {
  font-family: var(--head); font-size:2.2rem; font-weight:800; line-height:1;
  background:linear-gradient(135deg,#c4b5fd,#67e8f9,#f9a8d4);
  background-size:300% 300%; animation:chromaShift 6s ease infinite;
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  position:relative; z-index:1;
}
.vm-mlbl { font-size:.7rem; color:var(--muted); margin-top:.4rem; font-weight:500; letter-spacing:.07em; text-transform:uppercase; position:relative; z-index:1; }

/* ── Title banner ── */
.vm-title-banner {
  background:linear-gradient(135deg,rgba(124,58,237,.1),rgba(6,182,212,.07),rgba(244,114,182,.05));
  border:1px solid rgba(124,58,237,.28); border-radius:22px;
  padding:2.2rem 2.6rem; text-align:center; margin-bottom:1.8rem;
  position:relative; overflow:hidden;
}
.vm-title-banner::before {
  content:''; position:absolute; top:-1px; left:15%; right:15%; height:1px;
  background:linear-gradient(90deg,transparent,rgba(167,139,250,.8),rgba(103,232,249,.6),transparent);
}
.vm-title-banner::after {
  content:''; position:absolute; bottom:-1px; left:30%; right:30%; height:1px;
  background:linear-gradient(90deg,transparent,rgba(244,114,182,.5),transparent);
}
/* Scan line on title banner */
.vm-title-banner-scan {
  position:absolute; inset:0; overflow:hidden; border-radius:22px; pointer-events:none;
}
.vm-title-banner-scan::after {
  content:''; position:absolute; left:0; right:0; height:2px;
  background:linear-gradient(90deg,transparent,rgba(167,139,250,.4),transparent);
  animation: bannerScan 4s ease-in-out infinite;
}
@keyframes bannerScan {
  0%   { top:-5%; opacity:0; }
  10%  { opacity:1; }
  90%  { opacity:.7; }
  100% { top:110%; opacity:0; }
}
.vm-tbadge {
  font-family:var(--mono); font-size:.65rem; letter-spacing:.18em; text-transform:uppercase;
  color:#a78bfa; margin-bottom:.7rem; display:block; position:relative; z-index:1;
}
.vm-ttxt {
  font-family:var(--head); font-size:1.75rem; font-weight:800; line-height:1.25;
  background:linear-gradient(120deg,#fff 10%,#c4b5fd 40%,#67e8f9 70%,#f9a8d4 90%);
  background-size:300% 300%; animation:chromaShift 8s ease infinite;
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  position:relative; z-index:1;
}

/* ── Info cards ── */
.vm-icard {
  background:rgba(255,255,255,.025); border:1px solid var(--rim);
  border-radius:18px; padding:1.2rem 1.5rem; margin-bottom:.9rem;
  position:relative; overflow:hidden; transition:all .22s;
  backdrop-filter:blur(10px);
}
.vm-icard::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; border-radius:0 3px 3px 0; }
.vm-icard::after {
  content:''; position:absolute; inset:0; border-radius:18px;
  background:linear-gradient(135deg,rgba(255,255,255,.04) 0%,transparent 50%);
  pointer-events:none;
}
.vm-icard:hover { transform:translateX(5px); box-shadow:0 6px 32px rgba(0,0,0,.25); }
.vm-icard.c-purple::before { background:linear-gradient(180deg,#7c3aed,#4c1d95); box-shadow:2px 0 14px rgba(124,58,237,.6); }
.vm-icard.c-cyan::before   { background:linear-gradient(180deg,#06b6d4,#0e7490); box-shadow:2px 0 14px rgba(6,182,212,.6); }
.vm-icard.c-amber::before  { background:linear-gradient(180deg,#f59e0b,#92400e); box-shadow:2px 0 14px rgba(245,158,11,.6); }
.vm-icard.c-rose::before   { background:linear-gradient(180deg,#f43f5e,#9f1239); box-shadow:2px 0 14px rgba(244,63,94,.6); }
.vm-icard.c-green::before  { background:linear-gradient(180deg,#10b981,#065f46); box-shadow:2px 0 14px rgba(16,185,129,.6); }
.vm-ibadge {
  display:inline-block; font-family:var(--mono); font-size:.6rem; font-weight:500;
  letter-spacing:.14em; text-transform:uppercase;
  border-radius:7px; padding:.2rem .6rem; margin-bottom:.55rem;
  position:relative; z-index:1;
}
.c-purple .vm-ibadge { background:rgba(124,58,237,.18); color:#a78bfa; }
.c-cyan   .vm-ibadge { background:rgba(6,182,212,.14);  color:#67e8f9; }
.c-amber  .vm-ibadge { background:rgba(245,158,11,.14); color:#fcd34d; }
.c-rose   .vm-ibadge { background:rgba(244,63,94,.14);  color:#fb7185; }
.c-green  .vm-ibadge { background:rgba(16,185,129,.14); color:#6ee7b7; }
.vm-ibody { font-size:.9rem; line-height:1.78; color:rgba(226,232,248,.82); position:relative; z-index:1; }

/* Empty state */
.vm-empty-state {
  text-align:center; padding:2.5rem 1rem;
  color:var(--muted); font-size:.9rem; font-style:italic;
}

/* ── Transcript box ── */
.vm-tx {
  background:rgba(0,0,0,.35); border:1px solid var(--rim); border-radius:18px;
  padding:1.5rem; font-family:var(--mono); font-size:.78rem;
  line-height:1.9; color:var(--muted);
  max-height:380px; overflow-y:auto; white-space:pre-wrap; word-break:break-word;
}
.vm-tx::-webkit-scrollbar { width:4px; }
.vm-tx::-webkit-scrollbar-track { background:rgba(255,255,255,.02); border-radius:9px; }
.vm-tx::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg,#7c3aed,#06b6d4,#f472b6); border-radius:9px;
}

/* ── Chat ── */
.vm-chat { display:flex; flex-direction:column; gap:.9rem; padding-bottom:.5rem; }
.vm-bubble {
  max-width:84%; padding:.9rem 1.25rem; border-radius:20px;
  font-size:.9rem; line-height:1.68; animation: bubblePop .32s ease both;
  position:relative; overflow:hidden;
}
.vm-bubble::after {
  content:''; position:absolute; inset:0; border-radius:20px;
  background:linear-gradient(135deg,rgba(255,255,255,.05) 0%,transparent 55%);
  pointer-events:none;
}
.vm-blabel { font-family:var(--mono); font-size:.62rem; letter-spacing:.1em;
  text-transform:uppercase; opacity:.4; margin-bottom:.35rem; }
.vm-bubble.user {
  align-self:flex-end;
  background:linear-gradient(135deg,rgba(124,58,237,.48),rgba(6,182,212,.28));
  border:1px solid rgba(124,58,237,.32); border-bottom-right-radius:5px; color:var(--txt);
}
.vm-bubble.bot {
  align-self:flex-start; background:rgba(255,255,255,.05);
  border:1px solid var(--rim); border-bottom-left-radius:5px; color:rgba(226,232,248,.9);
}
.vm-empty { text-align:center; padding:3.5rem 1rem; color:var(--muted); font-size:.88rem; }
.vm-empty-icon { font-size:3.2rem; margin-bottom:.8rem; opacity:.3;
  animation:breathe 3.5s ease-in-out infinite; display:block; }
@keyframes breathe {
  0%,100% { transform:scale(1) rotate(-4deg); opacity:.28; }
  50%      { transform:scale(1.1) rotate(4deg); opacity:.52; }
}
@keyframes bubblePop {
  from { opacity:0; transform:scale(.93) translateY(8px); }
  to   { opacity:1; transform:none; }
}

/* ── Download button overrides ── */
.stDownloadButton > button {
  background:rgba(255,255,255,.05) !important;
  border:1px solid var(--rim) !important; border-radius:13px !important;
  color:var(--txt) !important; font-family:var(--body) !important;
  font-size:.85rem !important; padding:.62rem 1.45rem !important;
  transition:all .22s !important;
}
.stDownloadButton > button:hover {
  background:rgba(124,58,237,.18) !important;
  border-color:rgba(124,58,237,.55) !important;
  box-shadow:0 4px 20px rgba(124,58,237,.2) !important;
}

/* ── Section title ── */
.vm-section-title { font-family:var(--head); font-size:1.25rem; font-weight:700; color:var(--txt); margin-bottom:1.15rem; }

/* ── Floating glow orb decorations ── */
.vm-orb { position:fixed; border-radius:50%; pointer-events:none; z-index:0; filter:blur(70px); opacity:.16; }
.vm-orb-1 { width:450px; height:450px; top:18%; left:-120px; background:#7c3aed; animation:orbFloat1 22s ease-in-out infinite alternate; }
.vm-orb-2 { width:380px; height:380px; top:62%; right:-100px; background:#06b6d4; animation:orbFloat2 19s ease-in-out infinite alternate; }
.vm-orb-3 { width:320px; height:320px; top:8%; right:18%;  background:#f472b6; animation:orbFloat3 26s ease-in-out infinite alternate; }
.vm-orb-4 { width:260px; height:260px; top:45%; left:30%;  background:#10b981; animation:orbFloat4 30s ease-in-out infinite alternate; opacity:.08; }
@keyframes orbFloat1 { 0%{transform:translateY(0) scale(1)}   100%{transform:translateY(90px) scale(1.25)} }
@keyframes orbFloat2 { 0%{transform:translateY(0) scale(1)}   100%{transform:translateY(-80px) scale(1.18)} }
@keyframes orbFloat3 { 0%{transform:translateX(0) scale(1)}   100%{transform:translateX(-70px) scale(.88)} }
@keyframes orbFloat4 { 0%{transform:translate(0,0) scale(1)}  100%{transform:translate(60px,-60px) scale(1.15)} }

/* ── Footer ── */
.vm-footer {
  text-align:center; padding:3rem 0 2rem;
  font-family:var(--mono); font-size:.72rem;
  color:rgba(226,232,248,.14); letter-spacing:.09em;
}
.vm-footer span {
  background:linear-gradient(90deg,#7c3aed,#06b6d4,#f472b6,#10b981);
  background-size:300% 300%; animation:chromaShift 6s ease infinite;
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  font-weight:700;
}

/* ── Stagger for icard entries ── */
.vm-icard:nth-child(1) { animation-delay:.05s; }
.vm-icard:nth-child(2) { animation-delay:.1s; }
.vm-icard:nth-child(3) { animation-delay:.15s; }
.vm-icard:nth-child(4) { animation-delay:.2s; }
.vm-icard:nth-child(5) { animation-delay:.25s; }
@keyframes cardIn {
  from { opacity:0; transform:translateY(14px); }
  to   { opacity:1; transform:none; }
}
.vm-icard { animation: cardIn .4s ease both; }
</style>

<!-- Floating orbs -->
<div class="vm-orb vm-orb-1"></div>
<div class="vm-orb vm-orb-2"></div>
<div class="vm-orb vm-orb-3"></div>
<div class="vm-orb vm-orb-4"></div>
""", unsafe_allow_html=True)

# ── session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {"result": None, "chat_history": [], "error": None}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── pipeline steps ────────────────────────────────────────────────────────────
STEPS = [
    ("⬇",  "Downloading / loading media"),
    ("🎙", "Transcribing with Whisper"),
    ("✏️", "Generating smart title"),
    ("📋", "Summarising content"),
    ("✅", "Extracting action items"),
    ("🔑", "Extracting key decisions"),
    ("❓", "Finding open questions"),
    ("🧠", "Building RAG vector store"),
]

def _steps_html(current: int) -> str:
    rows = ""
    for i, (icon, label) in enumerate(STEPS):
        state = "done" if i < current else ("active" if i == current else "idle")
        mark  = "✓" if state == "done" else ("" if state == "active" else "")
        rows += (
            f'<div class="vm-step">'
            f'  <div class="vm-node {state}">{mark}</div>'
            f'  <span class="vm-step-label {state}">{icon}&nbsp;&nbsp;{label}</span>'
            f'</div>'
        )
    return f'<div class="vm-steps">{rows}</div>'

# ── BUG FIX: _lines now also filters out common "no items" placeholder phrases ──
_NO_CONTENT_PHRASES = {
    "no action items found", "no action items", "none",
    "no key decisions found", "no key decisions",
    "no open questions found", "no open questions",
    "no items found", "n/a", "-", "—",
}

def _lines(text: str) -> list:
    """
    Parse a numbered / bulleted list from LLM output into clean strings.
    Returns an empty list if the text is a placeholder "no items" response.
    """
    out = []
    for raw in str(text or "").split("\n"):
        s = re.sub(r"^[\d]+[.)]\s*", "", raw.strip())
        s = re.sub(r"^[-*•]\s*", "", s)
        s = s.strip()
        if s and s.lower().rstrip(".") not in _NO_CONTENT_PHRASES:
            out.append(s)
    return out

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="vm-hero">
  <div class="vm-hero-ring"></div>
  <div class="vm-hero-ring2"></div>
  <div class="vm-hero-ring3"></div>
  <span class="vm-icon">🎬</span>
  <div class="vm-badge">
    <div class="vm-badge-dot"></div>
    Whisper &nbsp;·&nbsp; LangChain &nbsp;·&nbsp; Mistral &nbsp;·&nbsp; ChromaDB
  </div>
  <div class="vm-title">VidMind AI</div>
  <p class="vm-sub">
    Drop any YouTube link or local video file — get instant transcription,
    AI summaries, action items, decisions, and a smart Q&amp;A assistant.
  </p>
  <div class="vm-chips">
    <span class="vm-chip"><span class="vm-chip-dot" style="background:#7c3aed"></span>Auto-transcribe</span>
    <span class="vm-chip"><span class="vm-chip-dot" style="background:#06b6d4"></span>AI Summaries</span>
    <span class="vm-chip"><span class="vm-chip-dot" style="background:#f472b6"></span>Action Items</span>
    <span class="vm-chip"><span class="vm-chip-dot" style="background:#10b981"></span>RAG Chat</span>
    <span class="vm-chip"><span class="vm-chip-dot" style="background:#f59e0b"></span>Key Decisions</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="vm-hr"></div>', unsafe_allow_html=True)

# ── INPUT SECTION ────────────────────────────────────────────────────────────
col_src, col_lang = st.columns([4, 1], gap="large")
with col_src:
    st.markdown('<span class="vm-label">Video Source</span>', unsafe_allow_html=True)
    source = st.text_input("source", placeholder="🔗  YouTube URL  — or —  /absolute/path/to/video.mp4",
                           label_visibility="collapsed", key="source_input")
with col_lang:
    st.markdown('<span class="vm-label">Language</span>', unsafe_allow_html=True)
    language = st.selectbox("lang",
                            ["english", "hinglish", "hindi", "spanish", "french", "german", "auto"],
                            label_visibility="collapsed", key="lang_select")

st.markdown("<br>", unsafe_allow_html=True)
btn_col, _ = st.columns([1, 5])
with btn_col:
    go = st.button("⚡  Analyse Video", use_container_width=True)

# ── PIPELINE ─────────────────────────────────────────────────────────────────
if go:
    if not source.strip():
        st.warning("Please enter a YouTube URL or local file path first.")
    else:
        st.session_state.result       = None
        st.session_state.chat_history = []
        st.session_state.error        = None

        st.markdown('<div class="vm-hr"></div>', unsafe_allow_html=True)
        left, right = st.columns([1, 1], gap="large")

        with left:
            st.markdown('<div class="vm-card" style="text-align:center;padding:2.8rem 1.5rem;">',
                        unsafe_allow_html=True)
            st.markdown('<div class="vm-spinner"></div>', unsafe_allow_html=True)
            pbar    = st.progress(0)
            pstatus = st.empty()
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            step_ph = st.empty()

        def _tick(n: int):
            pct = int(n / len(STEPS) * 100)
            pbar.progress(pct)
            icon, label = STEPS[n]
            pstatus.markdown(
                f'<p style="color:#a5b4fc;font-family:\'DM Mono\',monospace;font-size:.82rem;'
                f'margin-top:.9rem;text-align:center;letter-spacing:.07em;">'
                f'{icon}&nbsp;&nbsp;{label}…</p>',
                unsafe_allow_html=True)
            step_ph.markdown(
                f'<div class="vm-card">{_steps_html(n)}</div>',
                unsafe_allow_html=True)

        try:
            (process_input, transcribe_all,
             summarize, generate_title,
             extract_action_items, extract_key_decisions, extract_questions,
             build_rag_chain, ask_question) = _lazy_pipeline()

            _tick(0);  chunks       = process_input(source.strip())
            _tick(1);  transcript   = transcribe_all(chunks, language)
            _tick(2);  title        = generate_title(transcript)
            _tick(3);  summary      = summarize(transcript)
            _tick(4);  action_items = extract_action_items(transcript)
            _tick(5);  decisions    = extract_key_decisions(transcript)
            _tick(6);  questions    = extract_questions(transcript)
            _tick(7);  rag_chain    = build_rag_chain(transcript)

            pbar.progress(100)
            pstatus.markdown(
                '<p style="color:#34d399;font-family:\'DM Mono\',monospace;font-size:.85rem;'
                'margin-top:.9rem;text-align:center;">✓&nbsp;&nbsp;Analysis complete!</p>',
                unsafe_allow_html=True)
            step_ph.markdown(
                f'<div class="vm-card">{_steps_html(len(STEPS))}</div>',
                unsafe_allow_html=True)

            st.session_state.result = {
                "title": title, "transcript": transcript, "summary": summary,
                "action_items": action_items, "key_decisions": decisions,
                "open_questions": questions, "rag_chain": rag_chain,
            }
            time.sleep(.45)
            st.rerun()

        except Exception as exc:
            st.session_state.error = (str(exc), traceback.format_exc())
            st.rerun()

# ── ERROR ────────────────────────────────────────────────────────────────────
if st.session_state.error:
    msg, tb = st.session_state.error
    st.markdown('<div class="vm-hr"></div>', unsafe_allow_html=True)
    st.error(f"**Something went wrong:** {msg}")
    with st.expander("Show full traceback", expanded=False):
        st.code(tb, language="python")
    r_col, _ = st.columns([1, 5])
    with r_col:
        if st.button("🔄  Try again", use_container_width=True):
            st.session_state.error = None
            st.rerun()

# ── RESULTS ──────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result
    st.markdown('<div class="vm-hr"></div>', unsafe_allow_html=True)

    # Title banner
    safe_title = str(r.get("title") or "Untitled").strip()
    st.markdown(f"""
    <div class="vm-title-banner">
      <div class="vm-title-banner-scan"></div>
      <span class="vm-tbadge">📌 &nbsp;Detected Title</span>
      <div class="vm-ttxt">{safe_title}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── BUG FIX: Use _lines() for ALL counts so placeholders don't inflate numbers ──
    tx     = str(r.get("transcript")    or "")
    ai_lst = _lines(r.get("action_items",  ""))
    dec_lst= _lines(r.get("key_decisions", ""))
    q_lst  = _lines(r.get("open_questions",""))

    ai_n   = len(ai_lst)
    dec_n  = len(dec_lst)
    q_n    = len(q_lst)

    st.markdown(f"""
    <div class="vm-metrics">
      <div class="vm-mbox"><div class="vm-mval">{len(tx.split()):,}</div><div class="vm-mlbl">Words transcribed</div></div>
      <div class="vm-mbox"><div class="vm-mval">{len(tx):,}</div><div class="vm-mlbl">Characters</div></div>
      <div class="vm-mbox"><div class="vm-mval">{ai_n}</div><div class="vm-mlbl">Action items</div></div>
      <div class="vm-mbox"><div class="vm-mval">{dec_n}</div><div class="vm-mlbl">Key decisions</div></div>
      <div class="vm-mbox"><div class="vm-mval">{q_n}</div><div class="vm-mlbl">Questions</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    t_sum, t_act, t_dec, t_q, t_tx, t_chat = st.tabs([
        "📋  Summary", "✅  Action Items", "🔑  Decisions",
        "❓  Questions", "📄  Transcript", "💬  Chat",
    ])

    with t_sum:
        summary_txt = str(r.get("summary") or "No summary generated.")
        st.markdown(f"""
        <div class="vm-icard c-purple">
          <div class="vm-ibadge">AI Summary</div>
          <div class="vm-ibody">{summary_txt}</div>
        </div>""", unsafe_allow_html=True)

    with t_act:
        if ai_lst:
            for item in ai_lst:
                st.markdown(f"""
                <div class="vm-icard c-cyan">
                  <div class="vm-ibadge">Action Item</div>
                  <div class="vm-ibody">{item}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="vm-empty-state">✦ No action items found in this video.</div>',
                        unsafe_allow_html=True)

    with t_dec:
        if dec_lst:
            for d in dec_lst:
                st.markdown(f"""
                <div class="vm-icard c-amber">
                  <div class="vm-ibadge">Decision</div>
                  <div class="vm-ibody">{d}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="vm-empty-state">✦ No key decisions found in this video.</div>',
                        unsafe_allow_html=True)

    with t_q:
        if q_lst:
            for q in q_lst:
                st.markdown(f"""
                <div class="vm-icard c-rose">
                  <div class="vm-ibadge">Open Question</div>
                  <div class="vm-ibody">{q}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="vm-empty-state">✦ No open questions found in this video.</div>',
                        unsafe_allow_html=True)

    with t_tx:
        st.markdown('<span class="vm-label" style="margin-bottom:1rem;display:block;">Full Transcript</span>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="vm-tx">{tx}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        dl_col, _ = st.columns([1, 4])
        with dl_col:
            st.download_button("⬇  Download .txt", data=tx,
                               file_name="transcript.txt", mime="text/plain",
                               use_container_width=True)

    with t_chat:
        st.markdown('<p class="vm-section-title">Chat with your video</p>', unsafe_allow_html=True)
        st.markdown(
            '<p style="color:var(--muted);font-size:.84rem;margin-bottom:1.4rem;">'
            'The assistant has read the full transcript — ask anything about its content.</p>',
            unsafe_allow_html=True)

        if st.session_state.chat_history:
            html = '<div class="vm-chat">'
            for msg in st.session_state.chat_history:
                cls  = "user" if msg["role"] == "user" else "bot"
                lbl  = "You"  if msg["role"] == "user" else "VidMind"
                body = (str(msg["content"])
                        .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
                html += (f'<div class="vm-bubble {cls}">'
                         f'<div class="vm-blabel">{lbl}</div>{body}</div>')
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="vm-empty">
              <span class="vm-empty-icon">💬</span>
              Ask your first question below…
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        qi_col, send_col = st.columns([5, 1], gap="small")
        with qi_col:
            user_q = st.text_input("q", placeholder="e.g.  What were the main conclusions?",
                                   key="chat_input", label_visibility="collapsed")
        with send_col:
            send = st.button("Send →", use_container_width=True, key="chat_send")

        if send and user_q.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_q.strip()})
            with st.spinner("Thinking…"):
                try:
                    (_, _, _, _, _, _, _, _, _ask) = _lazy_pipeline()
                    ans = _ask(r["rag_chain"], user_q.strip())
                except Exception as exc:
                    ans = f"⚠️  Could not get an answer: {exc}"
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.rerun()

        if st.session_state.chat_history:
            st.markdown("<br>", unsafe_allow_html=True)
            cl_col, _ = st.columns([1, 6])
            with cl_col:
                if st.button("🗑  Clear chat", use_container_width=True, key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()

    st.markdown('<div class="vm-hr"></div>', unsafe_allow_html=True)
    na_col, _ = st.columns([1, 5])
    with na_col:
        if st.button("🔄  Analyse another video", use_container_width=True, key="reset_btn"):
            for _k, _v in _DEFAULTS.items():
                st.session_state[_k] = _v
            st.rerun()

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="vm-footer">
  VidMind AI &nbsp;·&nbsp; Whisper &nbsp;·&nbsp; LangChain &nbsp;·&nbsp;
  Mistral &nbsp;·&nbsp; ChromaDB &nbsp;&nbsp;
  <span>Made with ✦</span>
</div>
""", unsafe_allow_html=True)