"""Thin FastAPI service (PLAN.md §5): health check, manual nightly trigger, and
Jim's chat — a private, mobile-friendly page (add to home screen) where the
athlete iterates on plans and pushes them to Garmin on approve. The agent is a
callable, not tied to HTTP — Render Cron invokes the nightly job directly."""

import hmac
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from jim import coach
from jim.agent.loop import run_agent
from jim.config import settings

app = FastAPI(title="jim")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def trigger_run() -> dict:
    """Manual nightly run (same as the cron job, minus the data sync)."""
    today = datetime.now(ZoneInfo(settings().app_timezone)).date()
    report = run_agent(today)
    return {
        "for_date": report.for_date.isoformat(),
        "suggestion_id": report.suggestion_id,
        "tier": report.tier,
        "research_used": report.research_used,
        "tool_calls": report.tool_calls,
        "fell_back": report.fell_back,
    }


# --- Jim's chat ---------------------------------------------------------------


def _check_key(key: str) -> None:
    secret = settings().chat_secret
    if not secret or not hmac.compare_digest(key, secret):
        raise HTTPException(status_code=403, detail="bad or missing chat key")


class KeyOnly(BaseModel):
    key: str


class ChatMessage(BaseModel):
    key: str
    text: str


@app.post("/chat/message")
def chat_message(msg: ChatMessage) -> dict:
    _check_key(msg.key)
    if not msg.text.strip():
        raise HTTPException(status_code=400, detail="empty message")
    return coach.converse(msg.text.strip())


@app.post("/chat/approve")
def chat_approve(body: KeyOnly) -> dict:
    _check_key(body.key)
    return {"summary": coach.approve()}


@app.post("/chat/clear")
def chat_clear(body: KeyOnly) -> dict:
    _check_key(body.key)
    coach.clear()
    return {"ok": True}


@app.get("/chat/state")
def chat_state(key: str = "") -> dict:
    _check_key(key)
    return coach.current_state()


CHAT_PAGE = """<!doctype html><html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Jim</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;450;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#f7f7f5; --panel:#fff; --ink:#16161a; --muted:#8e8e98; --line:#ececea;
  --accent:#ff4d2e; --shadow:0 1px 2px rgba(0,0,0,.05);
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#0f0f11; --panel:#1a1a1e; --ink:#f3f3f5; --muted:#8b8b95;
    --line:#26262b; --shadow:0 1px 2px rgba(0,0,0,.3); }
}
:root[data-theme="light"]{ --bg:#f7f7f5; --panel:#fff; --ink:#16161a; --muted:#8e8e98; --line:#ececea; }
:root[data-theme="dark"]{ --bg:#0f0f11; --panel:#1a1a1e; --ink:#f3f3f5; --muted:#8b8b95; --line:#26262b; }
* { box-sizing: border-box; margin: 0; -webkit-tap-highlight-color: transparent; }
body { font-family: 'Inter', -apple-system, system-ui, sans-serif; background: var(--bg);
       color: var(--ink); height: 100dvh; display: flex; flex-direction: column;
       -webkit-font-smoothing: antialiased; letter-spacing: -.01em; }
header { padding: 16px 18px 13px; display: flex; align-items: baseline; gap: 10px;
         border-bottom: 1px solid var(--line); background: var(--bg); z-index: 5; }
.hname { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 19px;
         letter-spacing: -.02em; }
.hname i { color: var(--accent); font-style: normal; }
.htag { font-size: 12.5px; color: var(--muted); font-weight: 450; flex: 1; }
#clear { color: var(--muted); font-size: 12px; font-weight: 500; text-decoration: none; }
#clear:hover { color: var(--ink); }
#log { flex: 1; overflow-y: auto; padding: 18px 14px 8px; display: flex;
       flex-direction: column; gap: 9px; }
.row { display: flex; max-width: 82%; }
.row.me { align-self: flex-end; }
.row.bot { align-self: flex-start; }
.msg { padding: 10px 14px; border-radius: 16px; font-size: 14.5px; line-height: 1.5;
       white-space: pre-wrap; word-wrap: break-word; }
.me .msg { background: var(--ink); color: var(--bg); border-bottom-right-radius: 5px; }
.bot .msg { background: var(--panel); color: var(--ink); border: 1px solid var(--line);
            border-bottom-left-radius: 5px; }
.msg.busy { display: flex; gap: 4px; align-items: center; padding: 13px 14px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--muted);
       animation: bounce 1.3s infinite; }
.dot:nth-child(2){ animation-delay:.16s } .dot:nth-child(3){ animation-delay:.32s }
@keyframes bounce { 0%,64%,100%{ transform: translateY(0); opacity:.4 }
                    32%{ transform: translateY(-5px); opacity:1 } }
.chips { display: flex; flex-wrap: wrap; gap: 7px; padding: 2px; align-self: flex-start; }
.chip { border: 1px solid var(--line); background: var(--panel); color: var(--ink);
        border-radius: 11px; padding: 8px 12px; font-size: 13px; font-weight: 500;
        font-family: 'Inter'; cursor: pointer; }
.chip:hover { border-color: var(--muted); }
.chip:active { transform: scale(.97); }
#draft { display: none; margin: 8px 14px 2px; background: var(--panel); border-radius: 16px;
         padding: 15px 16px; border: 1px solid var(--line); box-shadow: var(--shadow); }
.draft-h { font-family: 'Space Grotesk'; font-weight: 600; font-size: 13px;
           letter-spacing: .02em; display: flex; align-items: center; gap: 7px; }
.draft-h::before { content:""; width: 6px; height: 6px; border-radius: 50%;
                   background: var(--accent); }
.draft-sub { font-size: 12px; color: var(--muted); margin: 3px 0 11px 13px; }
.day { display: flex; gap: 11px; padding: 11px 0; border-top: 1px solid var(--line);
       align-items: baseline; }
.day:first-of-type { border-top: none; padding-top: 2px; }
.day-em { font-size: 15px; line-height: 1.3; flex-shrink: 0; width: 18px; text-align: center; }
.day-main { flex: 1; min-width: 0; }
.day-top { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.day-title { font-family: 'Space Grotesk'; font-weight: 600; font-size: 14.5px; }
.day-when { font-size: 11.5px; color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
.day-steps { font-size: 12.5px; color: var(--muted); margin-top: 3px; line-height: 1.5; }
#push { margin-top: 14px; width: 100%; padding: 12px; border: none; border-radius: 12px;
        background: var(--accent); color: #fff; font-weight: 600; font-size: 14px;
        font-family: 'Inter'; letter-spacing: -.01em; cursor: pointer; }
#push:active { transform: translateY(1px); }
form { display: flex; gap: 9px; padding: 12px 14px calc(12px + env(safe-area-inset-bottom));
       background: var(--bg); border-top: 1px solid var(--line); }
#t { flex: 1; padding: 12px 16px; border: 1px solid var(--line); border-radius: 13px;
     font-size: 15px; font-family: 'Inter'; font-weight: 450; outline: none;
     background: var(--panel); color: var(--ink); }
#t:focus { border-color: var(--accent); }
#send { border: none; border-radius: 12px; width: 46px; height: 46px; background: var(--ink);
        color: var(--bg); font-size: 17px; cursor: pointer; flex-shrink: 0; }
#send:active { transform: scale(.95); }
</style></head><body>
<header>
  <div class="hname">Jim<i>.</i></div>
  <div class="htag">training coach</div>
  <a href="#" id="clear">Clear</a>
</header>
<div id="log"></div>
<div id="draft">
  <div class="draft-h">Working plan</div>
  <div class="draft-sub">Not on your watch yet — review, then push.</div>
  <div id="draft-body"></div>
  <button id="push">Push to Garmin</button>
</div>
<form id="f">
  <input id="t" placeholder="Message Jim…" autocomplete="off">
  <button id="send" type="submit" aria-label="Send">↑</button>
</form>
<script>
const key = new URLSearchParams(location.search).get("key") || "";
const log = document.getElementById("log"), t = document.getElementById("t");
const draftBox = document.getElementById("draft");
const draftBody = document.getElementById("draft-body");
const EMOJI = { strength:"🏋", conditioning:"🚴", mobility:"🧘", rest:"🌙" };
const DOW = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

function bubble(role, node) {
  const row = document.createElement("div"); row.className = "row " + role;
  const m = document.createElement("div"); m.className = "msg";
  if (typeof node === "string") m.textContent = node; else m.appendChild(node);
  row.appendChild(m); log.appendChild(row); log.scrollTop = log.scrollHeight; return m;
}
function add(role, text) { return bubble(role, text); }
function typing() {
  const m = bubble("bot", ""); m.classList.add("busy");
  m.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  return m;
}
function settle(m, text) { m.classList.remove("busy"); m.textContent = text; }

function renderDraft(draft) {
  draftBody.innerHTML = "";
  if (!draft || !draft.length) { draftBox.style.display = "none"; return; }
  for (const s of draft) {
    const row = document.createElement("div"); row.className = "day";
    const em = document.createElement("div"); em.className = "day-em";
    em.textContent = EMOJI[s.kind] || "•";
    const main = document.createElement("div"); main.className = "day-main";
    const d = new Date(s.for_date + "T00:00");
    const when = isNaN(d) ? s.for_date : `${DOW[d.getDay()]} ${d.getMonth()+1}/${d.getDate()}`;
    const steps = (s.steps || []).map(x => {
      const dose = x.reps ? `${x.sets}×${x.reps}` : `${x.sets}×${x.duration_sec}s`;
      return x.exercise + " " + dose + (x.weight_kg ? ` @ ${x.weight_kg}kg` : "");
    }).join(" · ");
    main.innerHTML =
      `<div class="day-top"><span class="day-title"></span><span class="day-when"></span></div>` +
      (steps ? `<div class="day-steps"></div>` : "");
    main.querySelector(".day-title").textContent = s.title;
    main.querySelector(".day-when").textContent = `${when} · ${Math.round(s.est_duration_min)}m`;
    if (steps) main.querySelector(".day-steps").textContent = steps;
    row.appendChild(em); row.appendChild(main); draftBody.appendChild(row);
  }
  draftBox.style.display = "block";
}
function showChips() {
  const wrap = document.createElement("div"); wrap.className = "chips";
  [["Plan my week","plan my week"], ["Knee's sore","my knee is sore today"],
   ["Set a goal","my long-term goal is "], ["Tomorrow?","what should I train tomorrow?"]]
    .forEach(([label, msg]) => {
      const c = document.createElement("button"); c.className = "chip"; c.textContent = label;
      c.onclick = () => { if (msg.endsWith(" ")) { t.value = msg; t.focus(); } else send(msg); };
      wrap.appendChild(c);
    });
  log.appendChild(wrap);
}
async function api(path, body) {
  const r = await fetch(path, { method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ key, ...body }) });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || "error");
  return data;
}
async function send(text) {
  add("me", text); t.value = "";
  document.querySelectorAll(".chips").forEach(c => c.remove());
  const busy = typing();
  try {
    const data = await api("/chat/message", { text });
    settle(busy, data.reply); renderDraft(data.draft);
  } catch (err) { settle(busy, err.message); }
}
async function load() {
  try {
    const r = await fetch(`/chat/state?key=${encodeURIComponent(key)}`);
    const s = await r.json();
    if (!r.ok) { add("bot", s.detail || "error"); return; }
    if (!s.history.length) {
      add("bot", "Hey — I'm Jim. Tell me how you're feeling, what you want this week, " +
        "or a long-term goal. I'll draft it here and nothing hits your watch until you push.");
      showChips();
    }
    for (const m of s.history) add(m.role === "user" ? "me" : "bot", m.content);
    renderDraft(s.draft);
  } catch { add("bot", "network error — reload"); }
}
document.getElementById("f").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = t.value.trim(); if (text) send(text);
});
document.getElementById("push").addEventListener("click", async () => {
  const busy = typing();
  try {
    const data = await api("/chat/approve", {});
    settle(busy, data.summary); renderDraft([]);
  } catch (err) { settle(busy, err.message); }
});
document.getElementById("clear").addEventListener("click", async (e) => {
  e.preventDefault();
  try { await api("/chat/clear", {}); log.innerHTML = ""; load(); } catch {}
});
load();
</script></body></html>"""


@app.get("/chat", response_class=HTMLResponse)
def chat_page(key: str = "") -> str:
    _check_key(key)
    return CHAT_PAGE
