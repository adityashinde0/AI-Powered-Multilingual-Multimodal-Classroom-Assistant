"""
UI-02 (upgraded): Smart Classroom Student Web UI — Wow-Factor Edition
Zero external Python dependencies — stdlib only (http.server, json, urllib.parse, threading, webbrowser).

Endpoints:
  GET  /                      → Rich single-page student dashboard
  GET  /api/notes             → JSON structured notes (?lang=en|hi|bn|ar)
  GET  /api/modalities        → JSON raw lecture modalities
  POST /api/ask               → JSON Q&A response (body: {"question":"...","lang":"..."})
  GET  /api/download          → Markdown notes file download (?lang=en|hi|bn|ar)
  GET  /api/lectures          → JSON list of available lectures
  POST /api/lectures/switch   → Switch active lecture (body: {"lecture_id":"..."})

Run:
  python src/web_ui.py              # http://localhost:8000
  python src/web_ui.py --open       # + auto-open browser
  python src/web_ui.py --port 9000  # custom port
  python src/web_ui.py --test       # self-test and exit 0
"""
import json
import sys
import webbrowser
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.models import (
    LectureContext, TranscriptSegment, ExtractedText,
    VisualElement, TechnicalElement,
)
from src.app import SmartClassroomApp
from src.translator import SUPPORTED_LANGUAGES
from src.sample_data import get_sample_lectures, get_lecture_metadata

# ---------------------------------------------------------------------------
# Lecture registry & active app state
# ---------------------------------------------------------------------------
_LECTURES = get_sample_lectures()          # {id: LectureContext}
_LECTURE_META = get_lecture_metadata()     # [{id, title, topic}]

# Start with the algorithms lecture (first in registry)
_DEFAULT_LECTURE_ID = list(_LECTURES.keys())[0]
_APP = SmartClassroomApp(context=_LECTURES[_DEFAULT_LECTURE_ID])
_ACTIVE_LECTURE_ID = _DEFAULT_LECTURE_ID

# ---------------------------------------------------------------------------
# HTML — single-page app
# ---------------------------------------------------------------------------
_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Classroom</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false}]})"></script>
<style>
:root {
  --bg:       #0a0d14;
  --bg2:      #0e1220;
  --surface:  rgba(19,24,38,0.70);
  --border:   rgba(99,102,241,0.18);
  --border2:  rgba(59,130,246,0.12);
  --text:     #e2e8f8;
  --muted:    #7b83a6;
  --accent:   #6366f1;
  --accent2:  #3b82f6;
  --green:    #34d399;
  --amber:    #fbbf24;
  --red:      #f87171;
  --font-h:   'Outfit', system-ui, sans-serif;
  --font-b:   'Inter', system-ui, sans-serif;
  --font-m:   'JetBrains Mono', monospace;
  --blur:     blur(16px);
  --r:        12px;
  --r-sm:     8px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--font-b);font-size:14px;line-height:1.65}

/* scrollbar */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(99,102,241,.3);border-radius:99px}

/* noise overlay */
body::before{content:'';position:fixed;inset:0;background:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.03'/%3E%3C/svg%3E");pointer-events:none;z-index:0}

/* glow blobs */
.blob{position:fixed;border-radius:50%;filter:blur(120px);pointer-events:none;z-index:0;opacity:.25}
.blob-a{width:600px;height:600px;background:radial-gradient(circle,#6366f1,transparent 70%);top:-200px;right:-100px}
.blob-b{width:500px;height:500px;background:radial-gradient(circle,#3b82f6,transparent 70%);bottom:-150px;left:-100px}

/* layout */
.layout{position:relative;z-index:1;display:grid;grid-template-columns:1fr 1fr;height:100vh;overflow:hidden}

/* header */
header{position:fixed;top:0;left:0;right:0;z-index:100;
  background:rgba(10,13,20,.85);backdrop-filter:var(--blur);
  border-bottom:1px solid var(--border);
  padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between}
header h1{font-family:var(--font-h);font-size:1.05rem;font-weight:700;
  background:linear-gradient(135deg,#a5b4fc,#60a5fa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
header .tagline{font-size:.75rem;color:var(--muted);letter-spacing:.02em}
.badge-row{display:flex;gap:8px;align-items:center}
.hbadge{font-size:.65rem;font-weight:600;letter-spacing:.06em;padding:3px 9px;border-radius:20px;
  background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);color:#a5b4fc}

.main{padding-top:56px;display:grid;grid-template-columns:1fr 1fr;height:100vh;overflow:hidden}
.panel{overflow-y:auto;padding:20px 22px}
.panel-left{border-right:1px solid var(--border)}

/* glass card */
.card{background:var(--surface);backdrop-filter:var(--blur);border:1px solid var(--border);
  border-radius:var(--r);padding:16px 18px;margin-bottom:14px;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;inset:0;border-radius:var(--r);
  background:linear-gradient(135deg,rgba(99,102,241,.04),rgba(59,130,246,.02));pointer-events:none}

/* section titles */
.stitle{font-size:.67rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);margin-bottom:12px;display:flex;align-items:center;gap:6px}
.stitle::after{content:'';flex:1;height:1px;background:var(--border)}

/* language tabs */
.lang-tabs{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap}
.lang-tab{padding:6px 16px;border-radius:20px;font-size:.8rem;font-family:var(--font-h);
  font-weight:500;cursor:pointer;border:1px solid var(--border);background:transparent;
  color:var(--muted);transition:all .2s;white-space:nowrap}
.lang-tab.active,.lang-tab:hover{background:linear-gradient(135deg,var(--accent),var(--accent2));
  border-color:transparent;color:#fff;box-shadow:0 0 14px rgba(99,102,241,.4)}

/* modality deck */
.modality-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px}
.m-card{background:rgba(19,24,38,.5);backdrop-filter:var(--blur);border:1px solid var(--border2);
  border-radius:var(--r-sm);padding:12px 14px}
.m-icon{font-size:1.3rem;margin-bottom:6px}
.m-label{font-size:.67rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:var(--accent);margin-bottom:4px;font-family:var(--font-h)}
.m-count{font-size:1.4rem;font-weight:700;font-family:var(--font-h);color:var(--text)}
.m-sub{font-size:.72rem;color:var(--muted)}

/* transcript pills */
.seg-pill{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;
  background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.1);
  border-radius:var(--r-sm);margin-bottom:8px}
.seg-time{font-family:var(--font-m);font-size:.7rem;color:var(--accent);white-space:nowrap;
  padding-top:2px;min-width:80px}
.seg-text{font-size:.83rem;color:var(--text)}

/* OCR blocks */
.ocr-block{padding:10px 14px;border-radius:var(--r-sm);background:rgba(59,130,246,.06);
  border:1px solid rgba(59,130,246,.15);margin-bottom:8px}
.ocr-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.ocr-src{font-size:.68rem;color:var(--muted);font-family:var(--font-m)}
.conf-bar{height:4px;border-radius:2px;background:rgba(255,255,255,.08);width:80px;overflow:hidden;display:inline-block;vertical-align:middle;margin-left:6px}
.conf-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent2),var(--green))}
.ocr-text{font-size:.83rem}

/* visual cards */
.vis-card{padding:10px 14px;border-radius:var(--r-sm);background:rgba(16,185,129,.05);
  border:1px solid rgba(16,185,129,.15);margin-bottom:8px}
.vis-type-badge{display:inline-block;font-size:.65rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;padding:2px 8px;border-radius:10px;
  background:rgba(16,185,129,.12);color:var(--green);margin-bottom:4px}
.vis-desc{font-size:.83rem;margin-bottom:4px}
.vis-src{font-size:.68rem;color:var(--muted);font-family:var(--font-m)}

/* formula chips */
.formula-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:4px}
.f-chip{display:inline-flex;align-items:center;gap:8px;
  background:rgba(251,191,36,.05);border:1px solid rgba(251,191,36,.2);
  border-radius:var(--r-sm);padding:7px 12px}
.f-type{font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--amber)}
.f-content{font-family:var(--font-m);font-size:.85rem;color:#fef3c7}

/* notes */
.notes-summary{font-size:.85rem;color:var(--muted);line-height:1.7;margin-bottom:14px}
.kp-list{list-style:none;display:flex;flex-direction:column;gap:7px;margin-bottom:14px}
.kp-item{font-size:.83rem;padding:9px 14px;border-radius:var(--r-sm);
  border-left:3px solid var(--accent);background:rgba(99,102,241,.06)}

/* Q&A */
.preset-chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:16px}
.preset-chip{padding:5px 13px;border-radius:20px;font-size:.75rem;cursor:pointer;
  border:1px solid var(--border);background:transparent;color:var(--muted);
  font-family:var(--font-b);transition:all .18s;text-align:left}
.preset-chip:hover{border-color:var(--accent);color:var(--text);background:rgba(99,102,241,.1)}
.preset-chip.danger:hover{border-color:var(--amber);color:var(--amber);background:rgba(251,191,36,.08)}

.chat-history{display:flex;flex-direction:column;gap:12px;margin-bottom:14px;min-height:160px}
.bubble{border-radius:var(--r);padding:12px 15px;font-size:.84rem;max-width:88%}
.bubble-user{background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:#fff;align-self:flex-end;border-bottom-right-radius:3px;box-shadow:0 4px 20px rgba(99,102,241,.35)}
.bubble-bot{background:var(--surface);backdrop-filter:var(--blur);border:1px solid var(--border);
  align-self:flex-start;border-bottom-left-radius:3px}

/* grounding badges */
.g-badge{display:inline-flex;align-items:center;gap:5px;font-size:.68rem;font-weight:700;
  letter-spacing:.06em;padding:3px 10px;border-radius:10px;margin-bottom:8px}
.g-dot{width:6px;height:6px;border-radius:50%}
.grounded-badge{background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.3);color:var(--green)}
.grounded-badge .g-dot{background:var(--green);box-shadow:0 0 6px var(--green)}
.notset-badge{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);color:var(--amber)}
.notset-badge .g-dot{background:var(--amber);box-shadow:0 0 6px var(--amber)}

.evidence-block{margin-top:8px;padding-top:8px;border-top:1px solid var(--border)}
.ev-label{font-size:.67rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:5px}
.ev-item{font-size:.77rem;color:var(--muted);padding:5px 8px;border-left:2px solid rgba(99,102,241,.3);margin-bottom:4px;border-radius:0 4px 4px 0;background:rgba(99,102,241,.04)}

/* typing indicator */
.typing{display:flex;gap:4px;align-items:center;padding:4px 0}
.typing span{width:6px;height:6px;border-radius:50%;background:var(--muted);
  animation:bounce .9s infinite ease-in-out}
.typing span:nth-child(2){animation-delay:.15s}
.typing span:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}

/* input area */
.qa-form{display:flex;gap:8px}
.qa-input{flex:1;background:rgba(19,24,38,.7);backdrop-filter:var(--blur);
  border:1px solid var(--border);border-radius:var(--r-sm);
  padding:10px 14px;color:var(--text);font-family:var(--font-b);font-size:.85rem;outline:none;transition:border-color .2s}
.qa-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.12)}
.qa-input::placeholder{color:var(--muted)}
.qa-btn{background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;
  border-radius:var(--r-sm);padding:10px 20px;color:#fff;font-size:.85rem;
  font-family:var(--font-h);font-weight:600;cursor:pointer;
  box-shadow:0 4px 16px rgba(99,102,241,.35);transition:opacity .15s,box-shadow .15s}
.qa-btn:hover{opacity:.9;box-shadow:0 4px 24px rgba(99,102,241,.5)}
.qa-btn:disabled{opacity:.4;cursor:not-allowed;box-shadow:none}

/* download btn */
.dl-btn{display:inline-flex;align-items:center;gap:7px;padding:7px 16px;
  border-radius:var(--r-sm);background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.25);
  color:var(--accent2);font-size:.78rem;font-family:var(--font-h);font-weight:600;
  cursor:pointer;text-decoration:none;transition:all .18s;margin-bottom:16px}
.dl-btn:hover{background:rgba(59,130,246,.2);border-color:var(--accent2);box-shadow:0 0 14px rgba(59,130,246,.2)}

/* lecture selector */
.lec-select{background:rgba(19,24,38,.85);border:1px solid var(--border);border-radius:var(--r-sm);
  padding:6px 10px;color:var(--text);font-family:var(--font-h);font-size:.78rem;outline:none;
  cursor:pointer;max-width:260px;transition:border-color .2s}
.lec-select:focus{border-color:var(--accent)}
.lec-select option{background:#0e1220;color:var(--text)}

@media(max-width:700px){.main{grid-template-columns:1fr}.panel-left{border-right:none;border-bottom:1px solid var(--border)}.modality-grid{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="blob blob-a"></div>
<div class="blob blob-b"></div>

<header>
  <div>
    <h1>The Smart Classroom</h1>
    <div class="tagline">AI-Powered Multilingual Multimodal Classroom Assistant</div>
  </div>
  <div class="badge-row">
    <select class="lec-select" id="lecSelect" onchange="switchLecture(this.value)">
      <option value="">Loading lectures…</option>
    </select>
    <span class="hbadge">IBM Hackathon</span>
    <span class="hbadge">59/59 Invariants</span>
    <span class="hbadge">en · hi · bn · ar</span>
  </div>
</header>

<div class="main">
<!-- ===== LEFT PANEL ===== -->
<div class="panel panel-left">

  <!-- Language -->
  <div class="stitle">Student Language</div>
  <div class="lang-tabs">
    <button class="lang-tab active" data-lang="en" onclick="switchLang('en')">English</button>
    <button class="lang-tab" data-lang="hi" onclick="switchLang('hi')">हिंदी</button>
    <button class="lang-tab" data-lang="bn" onclick="switchLang('bn')">বাংলা</button>
    <button class="lang-tab" data-lang="ar" onclick="switchLang('ar')">العربية</button>
  </div>

  <!-- Modality Overview -->
  <div class="stitle">Multimodal Ingestion</div>
  <div class="modality-grid" id="modalityGrid">
    <div class="m-card"><div class="m-icon">🎙️</div><div class="m-label">Speech</div><div class="m-count" id="mSpeech">—</div><div class="m-sub">transcript segments</div></div>
    <div class="m-card"><div class="m-icon">📷</div><div class="m-label">Whiteboard OCR</div><div class="m-count" id="mOCR">—</div><div class="m-sub">text blocks</div></div>
    <div class="m-card"><div class="m-icon">📊</div><div class="m-label">Visual Elements</div><div class="m-count" id="mVis">—</div><div class="m-sub">diagrams / charts</div></div>
    <div class="m-card"><div class="m-icon">🧮</div><div class="m-label">Formulas</div><div class="m-count" id="mForm">—</div><div class="m-sub">preserved elements</div></div>
  </div>

  <!-- Speech segments -->
  <div class="stitle">Speech Transcript</div>
  <div id="speechSegs"></div>

  <!-- OCR blocks -->
  <div class="stitle">Whiteboard / OCR</div>
  <div id="ocrBlocks"></div>

  <!-- Visuals -->
  <div class="stitle">Visual Elements</div>
  <div id="visCards"></div>

  <!-- Formulas -->
  <div class="stitle">Preserved Formulas & Terms</div>
  <div id="formulaChips" class="formula-row" style="margin-bottom:20px"></div>

  <!-- Structured Notes -->
  <div class="stitle">Structured Notes</div>
  <a class="dl-btn" id="dlBtn" href="/api/download?lang=en" download="notes.md">⬇ Download Notes (.md)</a>
  <div class="card">
    <div class="notes-summary" id="notesSummary">Loading…</div>
    <ul class="kp-list" id="keyPoints"></ul>
  </div>

</div><!-- end panel-left -->

<!-- ===== RIGHT PANEL ===== -->
<div class="panel">
  <div class="stitle">Lecture Q&amp;A</div>

  <div class="stitle" style="margin-bottom:8px">Try a Demo Question</div>
  <div class="preset-chips">
    <button class="preset-chip" onclick="fillQ(this.dataset.q)" data-q="What is the average time complexity of Quicksort?">🟢 Grounded: Average time complexity?</button>
    <button class="preset-chip" onclick="fillQ(this.dataset.q)" data-q="What is the worst-case complexity?">🟢 Grounded: Worst-case complexity?</button>
    <button class="preset-chip danger" onclick="fillQ(this.dataset.q)" data-q="Who was the first president of the United States?">🛡 Hallucination Gate: First US president?</button>
  </div>

  <div class="chat-history" id="chatHistory">
    <div class="bubble bubble-bot">Ask any question about the lecture. Answers are strictly grounded — only verified lecture content is cited.</div>
  </div>

  <div class="qa-form">
    <input class="qa-input" id="qaInput" type="text" placeholder="Ask a question about the lecture…"
      onkeydown="if(event.key==='Enter')sendQuestion()">
    <button class="qa-btn" id="qaBtn" onclick="sendQuestion()">Ask</button>
  </div>
</div>
</div><!-- end main -->

<script>
let currentLang = 'en';

function switchLang(lang) {
  currentLang = lang;
  document.querySelectorAll('.lang-tab').forEach(t =>
    t.classList.toggle('active', t.dataset.lang === lang));
  document.getElementById('dlBtn').href = '/api/download?lang=' + lang;
  document.getElementById('dlBtn').download = 'notes_' + lang + '.md';
  loadNotes(lang);
}

function fillQ(q) {
  document.getElementById('qaInput').value = q;
  document.getElementById('qaInput').focus();
}

async function loadLectureList() {
  try {
    const r = await fetch('/api/lectures');
    const lectures = await r.json();
    const sel = document.getElementById('lecSelect');
    sel.innerHTML = '';
    lectures.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.id; opt.textContent = l.title;
      sel.appendChild(opt);
    });
  } catch(e) { console.warn('Failed to load lecture list', e); }
}

async function switchLecture(lectureId) {
  if (!lectureId) return;
  try {
    await fetch('/api/lectures/switch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({lecture_id: lectureId})
    });
    // Clear chat history
    document.getElementById('chatHistory').innerHTML =
      '<div class="bubble bubble-bot">Lecture switched. Ask a question about the new lecture.</div>';
    // Reload all data panels
    await loadModalities();
    await loadNotes(currentLang);
  } catch(e) { console.warn('Lecture switch failed', e); }
}

function fmt(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function fmtTime(s) {
  const m = Math.floor(s/60), sec = Math.floor(s%60);
  return String(m).padStart(2,'0')+':'+String(sec).padStart(2,'0');
}

// ---- Load modalities
async function loadModalities() {
  try {
    const r = await fetch('/api/modalities');
    const d = await r.json();
    document.getElementById('mSpeech').textContent = d.transcript ? d.transcript.length : 0;
    document.getElementById('mOCR').textContent    = d.extracted_text ? d.extracted_text.length : 0;
    document.getElementById('mVis').textContent    = d.visual_elements ? d.visual_elements.length : 0;
    document.getElementById('mForm').textContent   = d.technical_elements ? d.technical_elements.length : 0;

    // Speech pills
    const sp = document.getElementById('speechSegs'); sp.innerHTML='';
    (d.transcript||[]).forEach(s=>{
      const el=document.createElement('div'); el.className='seg-pill';
      el.innerHTML=`<span class="seg-time">${fmtTime(s.start_time)} – ${fmtTime(s.end_time)}</span><span class="seg-text">${fmt(s.text)}</span>`;
      sp.appendChild(el);
    });

    // OCR
    const oc = document.getElementById('ocrBlocks'); oc.innerHTML='';
    (d.extracted_text||[]).forEach(e=>{
      const pct = Math.round((e.confidence||1)*100);
      const el=document.createElement('div'); el.className='ocr-block';
      el.innerHTML=`<div class="ocr-meta"><span class="ocr-src">${fmt(e.source_image)}</span><span style="font-size:.7rem;color:var(--muted)">${pct}% <span class="conf-bar"><span class="conf-fill" style="width:${pct}%"></span></span></span></div><div class="ocr-text">${fmt(e.text)}</div>`;
      oc.appendChild(el);
    });

    // Visuals
    const vc = document.getElementById('visCards'); vc.innerHTML='';
    (d.visual_elements||[]).forEach(v=>{
      const el=document.createElement('div'); el.className='vis-card';
      el.innerHTML=`<span class="vis-type-badge">${fmt(v.visual_type)}</span><div class="vis-desc">${fmt(v.description)}</div><div class="vis-src">${fmt(v.source_image)}</div>`;
      vc.appendChild(el);
    });

    // Formulas — render with KaTeX via auto-render
    const fc = document.getElementById('formulaChips'); fc.innerHTML='';
    (d.technical_elements||[]).forEach(t=>{
      const el=document.createElement('div'); el.className='f-chip';
      el.innerHTML=`<span class="f-type">${fmt(t.element_type)}</span><span class="f-content">${fmt(t.raw_content)}</span>`;
      fc.appendChild(el);
    });
    // trigger KaTeX auto-render on the new nodes if available
    if(window.renderMathInElement) renderMathInElement(fc);
  } catch(e){ console.warn('Modalities load failed',e); }
}

// ---- Load notes
async function loadNotes(lang) {
  document.getElementById('notesSummary').textContent = 'Loading…';
  document.getElementById('keyPoints').innerHTML='';
  try {
    const r = await fetch('/api/notes?lang='+lang);
    const d = await r.json();
    document.getElementById('notesSummary').textContent = d.summary || '(No summary)';
    const kp = document.getElementById('keyPoints'); kp.innerHTML='';
    (d.key_points||[]).forEach(p=>{
      const li=document.createElement('li'); li.className='kp-item'; li.textContent=p; kp.appendChild(li);
    });
    if(!d.key_points||!d.key_points.length) kp.innerHTML='<li class="kp-item" style="color:var(--muted);font-style:italic">No key points extracted.</li>';
  } catch(e){ document.getElementById('notesSummary').textContent='Failed to load notes.'; }
}

// ---- Q&A
async function sendQuestion() {
  const input = document.getElementById('qaInput');
  const btn   = document.getElementById('qaBtn');
  const q = input.value.trim(); if(!q) return;
  input.value=''; btn.disabled=true;

  const chat = document.getElementById('chatHistory');
  const ub=document.createElement('div'); ub.className='bubble bubble-user'; ub.textContent=q;
  chat.appendChild(ub);

  const lb=document.createElement('div'); lb.className='bubble bubble-bot';
  lb.innerHTML='<div class="typing"><span></span><span></span><span></span></div>';
  chat.appendChild(lb); chat.scrollTop=chat.scrollHeight;

  try {
    const r = await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,lang:currentLang})});
    const d = await r.json();
    lb.innerHTML='';
    const grounded = d.grounding_status==='grounded';
    const badge=document.createElement('div');
    badge.className='g-badge '+(grounded?'grounded-badge':'notset-badge');
    badge.innerHTML=`<span class="g-dot"></span>${grounded?'GROUNDED IN LECTURE':'HALLUCINATION BLOCKED — NOT ESTABLISHED'}`;
    lb.appendChild(badge);
    const ans=document.createElement('div'); ans.textContent=d.answer; lb.appendChild(ans);
    if(grounded && d.supporting_context && d.supporting_context.length){
      const ev=document.createElement('div'); ev.className='evidence-block';
      ev.innerHTML='<div class="ev-label">Lecture evidence</div>';
      d.supporting_context.forEach(s=>{
        const item=document.createElement('div'); item.className='ev-item'; item.textContent=s;
        ev.appendChild(item);
      });
      lb.appendChild(ev);
    }
  } catch(e){ lb.innerHTML='<div style="color:var(--red)">Network error.</div>'; }
  btn.disabled=false; chat.scrollTop=chat.scrollHeight;
}

loadLectureList();
loadModalities();
loadNotes('en');
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # suppress default stderr

    def _send_json(self, code: int, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, code: int, content_type: str, data: bytes, filename: str = "") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self._send_html(_HTML)

        elif path == "/api/notes":
            qs = parse_qs(parsed.query)
            lang = (qs.get("lang", ["en"])[0] or "en").strip().lower()
            try:
                notes = _APP.get_notes(language=lang, title="Smart Classroom Lecture")
                self._send_json(200, {
                    "title": notes.title,
                    "language": notes.language,
                    "summary": notes.summary,
                    "key_points": notes.key_points,
                    "formulas_and_terms": notes.formulas_and_terms,
                    "visual_summaries": notes.visual_summaries,
                    "source_references": notes.source_references,
                })
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        elif path == "/api/lectures":
            self._send_json(200, _LECTURE_META)

        elif path == "/api/modalities":
            try:
                ctx = _APP.context
                if ctx is None:
                    ctx = _LECTURES[_DEFAULT_LECTURE_ID]
                self._send_json(200, {
                    "transcript": [
                        {"id": s.id, "start_time": s.start_time, "end_time": s.end_time, "text": s.text}
                        for s in ctx.transcript
                    ],
                    "extracted_text": [
                        {"id": e.id, "text": e.text, "source_image": e.source_image, "confidence": e.confidence}
                        for e in ctx.extracted_text
                    ],
                    "visual_elements": [
                        {"id": v.id, "visual_type": v.visual_type, "description": v.description,
                         "source_image": v.source_image, "key_entities": v.key_entities}
                        for v in ctx.visual_elements
                    ],
                    "technical_elements": [
                        {"id": t.id, "element_type": t.element_type, "raw_content": t.raw_content,
                         "description": t.description}
                        for t in ctx.technical_elements
                    ],
                    "source_references": ctx.source_references,
                })
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        elif path == "/api/download":
            qs = parse_qs(parsed.query)
            lang = (qs.get("lang", ["en"])[0] or "en").strip().lower()
            try:
                notes = _APP.get_notes(language=lang, title="Smart Classroom Lecture")
                md_bytes = notes.to_markdown().encode("utf-8")
                self._send_bytes(200, "text/markdown; charset=utf-8", md_bytes,
                                 filename=f"notes_{lang}.md")
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        global _APP, _ACTIVE_LECTURE_ID
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/ask":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                data = json.loads(body.decode("utf-8"))
                question = str(data.get("question", "")).strip()
                lang = str(data.get("lang", "en")).strip().lower() or "en"
                response = _APP.ask(question, language=lang)
                self._send_json(200, {
                    "answer": response.answer,
                    "grounding_status": response.grounding_status,
                    "supporting_context": response.supporting_context,
                })
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        elif path == "/api/lectures/switch":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                data = json.loads(body.decode("utf-8"))
                lecture_id = str(data.get("lecture_id", "")).strip()
                if lecture_id not in _LECTURES:
                    self._send_json(400, {"error": f"Unknown lecture_id: {lecture_id}"})
                    return
                _APP.context = _LECTURES[lecture_id]
                _ACTIVE_LECTURE_ID = lecture_id
                meta = next((m for m in _LECTURE_META if m["id"] == lecture_id), {})
                self._send_json(200, {"switched_to": lecture_id, "title": meta.get("title", lecture_id)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        else:
            self._send_json(404, {"error": "Not found"})


# ---------------------------------------------------------------------------
# Server entry points
# ---------------------------------------------------------------------------
def start_server(port: int = 8000, open_browser: bool = False) -> None:
    """Starts a local zero-dependency HTTP server serving the Smart Classroom Student UI."""
    server = HTTPServer(("", port), _Handler)
    url = f"http://localhost:{port}"
    print(f"Smart Classroom UI running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def _run_self_test(port: int = 18765) -> bool:
    import urllib.request
    server = HTTPServer(("", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)
    base = f"http://localhost:{port}"
    ok = True
    try:
        # GET /
        with urllib.request.urlopen(f"{base}/") as r:
            assert r.status == 200
            assert b"Smart Classroom" in r.read()
        print("  [PASS] GET /  -> 200 HTML")

        # GET /api/notes
        with urllib.request.urlopen(f"{base}/api/notes?lang=en") as r:
            assert r.status == 200
            d = json.loads(r.read())
            assert "key_points" in d
        print("  [PASS] GET /api/notes?lang=en  -> 200 JSON")

        # GET /api/modalities
        with urllib.request.urlopen(f"{base}/api/modalities") as r:
            assert r.status == 200
            d = json.loads(r.read())
            assert "transcript" in d and "technical_elements" in d
        print("  [PASS] GET /api/modalities  -> 200 JSON with transcript + technical_elements")

        # GET /api/download
        with urllib.request.urlopen(f"{base}/api/download?lang=en") as r:
            assert r.status == 200
            md = r.read().decode("utf-8")
            assert "# Smart Classroom" in md
        print("  [PASS] GET /api/download?lang=en  -> 200 Markdown")

        # POST /api/ask — grounded
        payload = json.dumps({"question": "What is the average time complexity of Quicksort?", "lang": "en"}).encode()
        req = urllib.request.Request(f"{base}/api/ask", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
            d = json.loads(r.read())
            assert d["grounding_status"] == "grounded"
            assert "O(n log n)" in d["answer"]
        print("  [PASS] POST /api/ask (grounded)  -> grounded, cites O(n log n)")

        # POST /api/ask — ungrounded
        payload2 = json.dumps({"question": "Who was the first president of the United States?", "lang": "en"}).encode()
        req2 = urllib.request.Request(f"{base}/api/ask", data=payload2,
                                      headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req2) as r:
            assert r.status == 200
            d = json.loads(r.read())
            assert d["grounding_status"] == "not_established"
            assert d["supporting_context"] == []
        print("  [PASS] POST /api/ask (ungrounded)  -> not_established, empty evidence")

        # GET /api/lectures
        with urllib.request.urlopen(f"{base}/api/lectures") as r:
            assert r.status == 200
            lectures = json.loads(r.read())
            assert isinstance(lectures, list) and len(lectures) == 3
            ids = [l["id"] for l in lectures]
            assert "algorithms" in ids
        print("  [PASS] GET /api/lectures  -> 200 JSON with 3 lectures")

        # POST /api/lectures/switch
        sw_payload = json.dumps({"lecture_id": "ml_gradient"}).encode()
        sw_req = urllib.request.Request(f"{base}/api/lectures/switch", data=sw_payload,
                                        headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(sw_req) as r:
            assert r.status == 200
            d = json.loads(r.read())
            assert d["switched_to"] == "ml_gradient"
        print("  [PASS] POST /api/lectures/switch  -> switched to ml_gradient")

        # POST /api/ask after lecture switch — grounded in new lecture
        ml_payload = json.dumps({"question": "What is the learning rate in gradient descent?", "lang": "en"}).encode()
        ml_req = urllib.request.Request(f"{base}/api/ask", data=ml_payload,
                                        headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(ml_req) as r:
            assert r.status == 200
            d = json.loads(r.read())
            assert d["grounding_status"] == "grounded", f"Expected grounded after switch, got: {d['grounding_status']}"
        print("  [PASS] POST /api/ask after switch  -> grounded in ML lecture")

    except Exception as exc:
        print(f"  [FAIL] {exc}")
        ok = False
    finally:
        server.shutdown()
        server.server_close()
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        print("\nRunning web UI self-test...")
        success = _run_self_test()
        print("\nALL WEB UI SELF-TESTS PASSED" if success else "\nWEB UI SELF-TEST FAILED")
        sys.exit(0 if success else 1)

    port = 8000
    if "--port" in args:
        idx = args.index("--port")
        try:
            port = int(args[idx + 1])
        except (IndexError, ValueError):
            pass

    start_server(port=port, open_browser="--open" in args)
