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
<style>
* { box-sizing: border-box; margin: 0; }
body { font-family: -apple-system, system-ui, sans-serif; background: #f8f7f4; height: 100dvh;
       display: flex; flex-direction: column; }
header { background: #1c2b3a; color: #fff; padding: 14px 16px; display: flex;
         justify-content: space-between; align-items: center; }
header b { font-weight: 700; }
header a { color: #7a90a4; font-size: 12px; text-decoration: none; }
#log { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.msg { max-width: 88%; padding: 10px 12px; border-radius: 14px; font-size: 14px;
       white-space: pre-wrap; line-height: 1.45; }
.me { align-self: flex-end; background: #1c2b3a; color: #fff; border-bottom-right-radius: 4px; }
.bot { align-self: flex-start; background: #fff; border: 1px solid #e3e8ee;
       border-bottom-left-radius: 4px; }
.bot.busy { color: #7a90a4; font-style: italic; }
#draft { display: none; margin: 0 12px; background: #fff; border: 1px solid #1a7f74;
         border-radius: 12px; padding: 10px 12px; font-size: 13px; }
#draft h4 { color: #1a7f74; font-size: 12px; margin-bottom: 6px; letter-spacing: 0.3px; }
#draft pre { white-space: pre-wrap; font-family: inherit; line-height: 1.45; }
#push { margin-top: 8px; width: 100%; padding: 10px; border: none; border-radius: 10px;
        background: #1a7f74; color: #fff; font-weight: 700; font-size: 13px; }
form { display: flex; gap: 8px; padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
       background: #fff; border-top: 1px solid #e3e8ee; }
input { flex: 1; padding: 11px 14px; border: 1px solid #cbd5df; border-radius: 22px;
        font-size: 15px; outline: none; }
button { padding: 0 18px; border: none; border-radius: 22px; background: #1c2b3a;
         color: #fff; font-weight: 600; font-size: 14px; }
</style></head><body>
<header><b>Jim</b><a href="#" id="clear">clear chat</a></header>
<div id="log"></div>
<div id="draft"><h4>WORKING PLAN — not on your watch yet</h4><pre id="draft-body"></pre>
<button id="push">Push to Garmin</button></div>
<form id="f"><input id="t" placeholder="Message Jim" autocomplete="off"><button>Send</button></form>
<script>
const key = new URLSearchParams(location.search).get("key") || "";
const log = document.getElementById("log"), t = document.getElementById("t");
const draftBox = document.getElementById("draft");
const draftBody = document.getElementById("draft-body");

function add(cls, text) {
  const d = document.createElement("div"); d.className = "msg " + cls; d.textContent = text;
  log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
}
function renderDraft(draft) {
  if (!draft || !draft.length) { draftBox.style.display = "none"; return; }
  draftBody.textContent = draft.map(s => {
    let head = `${s.for_date} — ${s.title} (${s.kind}, ~${Math.round(s.est_duration_min)} min)`;
    const steps = (s.steps || []).map(x => {
      const dose = x.reps ? `${x.sets}x${x.reps}` : `${x.sets}x${x.duration_sec}s`;
      return `  • ${x.exercise} — ${dose}` + (x.weight_kg ? ` @ ${x.weight_kg}kg` : "");
    });
    return [head, ...steps].join("\\n");
  }).join("\\n\\n");
  draftBox.style.display = "block";
}
async function api(path, body) {
  const r = await fetch(path, { method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ key, ...body }) });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || "error");
  return data;
}
async function load() {
  try {
    const r = await fetch(`/chat/state?key=${encodeURIComponent(key)}`);
    const s = await r.json();
    if (!r.ok) { add("bot", s.detail || "error"); return; }
    if (!s.history.length) add("bot",
      "Tell me how you're feeling, what you want this week, or a long-term goal — " +
      "I'll plan around it and nothing goes on your watch until you push it.");
    for (const m of s.history) add(m.role === "user" ? "me" : "bot", m.content);
    renderDraft(s.draft);
  } catch { add("bot", "network error — reload"); }
}
document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = t.value.trim(); if (!text) return;
  add("me", text); t.value = "";
  const busy = add("bot busy", "thinking…");
  try {
    const data = await api("/chat/message", { text });
    busy.textContent = data.reply; busy.classList.remove("busy");
    renderDraft(data.draft);
  } catch (err) { busy.textContent = err.message; busy.classList.remove("busy"); }
});
document.getElementById("push").addEventListener("click", async () => {
  const busy = add("bot busy", "pushing to Garmin…");
  try {
    const data = await api("/chat/approve", {});
    busy.textContent = data.summary; busy.classList.remove("busy");
    renderDraft([]);
  } catch (err) { busy.textContent = err.message; busy.classList.remove("busy"); }
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
