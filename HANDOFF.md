# Handoff — Jim (local Claude Code session)

Read this first when picking up **Jim** in a local Claude Code session. It
captures where the project stands and exactly how to bring it up on your own
machine so the app runs against live Garmin/OpenRouter in a real browser.

For deeper context see `README.md`, `PLAN.md`, and `docs/` (architecture,
chat, memory, garmin_strength, notion_schema). This doc is the short version
plus the local-setup steps that couldn't be finished from the cloud sandbox.

## What Jim is

A single-user personal training agent. Nightly it reviews the day (Garmin +
a read-only Notion habit/knee log), reasons about tomorrow within knee/ankle
constraints, and drops a proposal into **Jim's chat** — a self-hosted page
where you iterate on the plan and push structured workouts to Garmin on
approve. Python 3.11+, FastAPI, Postgres, OpenRouter (via the `openai` SDK),
`garminconnect`. No build step — the whole chat UI is one inline HTML string
in `src/jim/app.py`.

## Current state (branch `claude/agent-billing-plan-6q730r`)

Working and committed:
- **Coach chat** (`src/jim/coach.py`) — conversational planning, plain-text
  goals memory, guardrail-validated drafts, approve → Garmin. Tool-calling
  loop can look up exercise/workout history and research mid-turn.
- **Chat UI** (`src/jim/app.py`, `CHAT_PAGE`) — "AI Coach" layout: serif
  header, glassy stat cards (Readiness / Next session / Pain), greeting hero
  with "Try asking" chips, +/send composer, plus the persistent Plan panel
  (right column on desktop, bottom sheet on mobile) with Push to Garmin.
- **Training-load & readiness** (`src/jim/tools/history.py::compute_readiness`)
  — acute:chronic workload ratio + recovery distilled into a planning verdict
  (push/steady/ease/rest), fed into the coach and shown on the Readiness card.
- **Garmin** (`src/jim/tools/garmin.py`) — verified structured-workout JSON
  (numeric conditionTypeId, RepeatGroupDTO, taxonomy enums), scheduling, and
  per-set history parsing. Base workouts (Full Body A/B/C + PT home/gym) are
  wired by Garmin workout ID.
- **Backfill** (`scripts/backfill.py`) — pulls Garmin daily metrics,
  activities, and per-set strength data into Postgres.
- 91 tests pass; `ruff` clean. `AUTO_PUSH=False` (propose-only; pushes happen
  only through the chat's Push button).

Not done from the cloud (needs a real machine — that's this session's job):
- Running the app in a real browser to see the actual fonts (the sandbox's
  headless browser couldn't reach Google Fonts, so screenshots showed the
  Georgia/serif fallback, not Fraunces).
- Living day-to-day use against your real Garmin calendar.

## Local setup

Prereqs (install if missing): **Git**, **Python 3.11+**, **PostgreSQL 16**.
On Windows use `winget` or the direct installers (git-scm.com; python.org —
tick "Add python.exe to PATH"; postgresql.org — remember the `postgres`
superuser password, keep port 5432).

```bash
git clone https://github.com/lakshita110/ec157-models.git
cd ec157-models
git checkout claude/agent-billing-plan-6q730r

python -m venv .venv
# macOS/Linux:  . .venv/bin/activate
# Windows PS:   .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Create the database (uses the default `DATABASE_URL` in `.env.example`):

```bash
# psql as the postgres superuser (you set its password at install time)
psql -U postgres -h localhost -c "CREATE USER jim WITH PASSWORD 'jim';"
psql -U postgres -h localhost -c "CREATE DATABASE jim OWNER jim;"
```

Secrets — copy the template and fill in the values (you already have these
from the cloud session; **never commit `.env`**):

```bash
cp .env.example .env
```

Fill in `.env`:
- `GARMIN_EMAIL`, `GARMIN_PASSWORD` — your Garmin login.
- `OPENROUTER_API_KEY`, `TAVILY_API_KEY` — the keys you provided earlier.
- `NOTION_TOKEN` — optional; leave blank to run without it (the Pain card and
  Notion context just hide; everything else works).
- `DATABASE_URL=postgresql://jim:jim@localhost:5432/jim`
- `CHAT_SECRET` — any long random string (goes in the chat URL).
- `APP_TIMEZONE=America/New_York` (or yours).

> Security: the OpenRouter/Tavily keys and the Garmin password were shared
> into a cloud chat during development — rotate them once you're set up
> locally, and cap the OpenRouter credit.

Verify, then run:

```bash
ruff check .
pytest                      # expect 91 passing
python scripts/backfill.py 120   # first run: pull ~120d of Garmin history
uvicorn jim.app:app --reload
```

Open **http://127.0.0.1:8000/chat?key=YOUR_CHAT_SECRET** in Chrome/Edge —
this is where you'll finally see the real Fraunces/Inter fonts and the glass
UI. Try "plan my week" or "my knee is sore today".

## Gotchas learned the hard way

- **Garmin login**: token-based; tokens cache at `~/.garminconnect`. From a
  normal residential IP the login works directly (the cloud sandbox was
  blocked by Cloudflare on datacenter IPs — not an issue locally). If login
  ever fails with a transport/`curl_cffi` error, `pip uninstall curl_cffi`
  so it falls back to plain `requests`.
- **Notion API**: needs `notion-client` 3.x — queries go through
  `data_sources.query`, not the old `databases.query` (handled in
  `src/jim/tools/notion.py`). Notion is **read-only** by design.
- **pgvector**: migration `002_research_corpus.sql` is skipped with a warning
  if the `vector` extension isn't installed. That only disables the research
  corpus; everything else runs. Install pgvector if you want research.
- **fetch_state degrades per-source** — a down integration (e.g. no Notion
  token) won't blank Garmin/readiness; cards just hide.
- **Pushing to Garmin** only happens when you click **Push to Garmin** in the
  chat (or call `coach.approve()`). The nightly job is propose-only.

## Continuing the work

Develop on `claude/agent-billing-plan-6q730r`; commit and push there. One open
polish question left from the cloud session: whether the Readiness card should
re-fetch after every message (currently it loads once per page load, which is
fine since load/recovery don't move within a session). Other backlog:
`docs/` M5 eval suite that would gate turning `AUTO_PUSH` on.

To hand a local session the full picture, point it at this file plus
`docs/architecture.md`.
