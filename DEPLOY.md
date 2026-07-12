# Deploy Jim (and put it on your phone)

One Render blueprint creates everything: a Postgres database, the web service
(health + chat), and the nightly cron. Roughly 15 minutes end to end.

Nothing here needs a Dockerfile or a CI pipeline — `render.yaml` is the whole
deployment.

---

## 1. Collect the secrets (5 min, on your laptop)

**Chat key** — this is what gates the chat. Generate a long random one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Garmin session blob** — the important one. A deployed container has no cached
token store and *no stdin to answer an MFA prompt*, so it can't do a normal
Garmin login. Instead it authenticates from a session blob:

```bash
python scripts/garmin_login.py --export
```

This reuses your existing local session if there is one (no password re-entry)
and prints a `GARMIN_TOKENS` blob. **Treat it like a password** — paste it
straight into Render, never commit it.

You'll also need what's already in your `.env`: `GARMIN_EMAIL`, `NOTION_TOKEN`,
`OPENROUTER_API_KEY`, `TAVILY_API_KEY`.

## 2. Push the repo

Render deploys from GitHub, so the code has to be there:

```bash
git push origin main
```

`.env` is gitignored — keep it that way.

## 3. Create the blueprint

In Render: **New → Blueprint**, pick this repo. It reads `render.yaml` and
proposes three resources:

| Resource | What it is |
|---|---|
| `jim-db` | Postgres 16 (`basic-256mb`) |
| `jim-web` | the chat, `uvicorn jim.app:app` |
| `jim-nightly` | cron, 20:00 UTC — reconcile today + plan tomorrow |

`DATABASE_URL` is wired to `jim-db` automatically. Approve it.

## 4. Fill in the `jim-secrets` env group

Render will prompt for every `sync: false` key. Paste:

| Key | Value |
|---|---|
| `CHAT_SECRET` | the random string from step 1 |
| `GARMIN_TOKENS` | the blob from step 1 |
| `GARMIN_EMAIL` | your Garmin email |
| `GARMIN_PASSWORD` | your Garmin password (fallback only; the blob is what's used) |
| `NOTION_TOKEN` | from `.env` |
| `NOTION_KNEE_LOG_DB_ID` | `b872f62a28604573980e983be6fd3143` |
| `OPENROUTER_API_KEY` | from `.env` |
| `TAVILY_API_KEY` | from `.env` |

`APP_TIMEZONE` is already set to `Europe/Berlin` in the blueprint.

## 5. Deploy

Hit deploy. **Migrations run automatically on web-service boot** (`app.py`
lifespan), so the schema is created on the first request — there is no separate
migrate step. Watch for `migrations applied` in the logs.

Sanity check:

```bash
curl https://jim-web.onrender.com/health          # {"status":"ok"}
```

## 6. (Optional) Backfill history

A fresh database has no Garmin history, so the readiness card and load ratio
start empty. From the Render shell (`jim-web` → Shell):

```bash
python scripts/backfill.py 90     # 90 days of Garmin history
python scripts/seed_corpus.py     # research corpus for pain-driven substitutions
```

After any backfill, clear the cached state snapshot or the cards keep showing
stale "no data" for up to an hour:

```bash
python -c "from jim.db import kv_set; kv_set('state', None)"
```

## 7. Put it on your phone 📱

Open the chat **on your phone**, with the key:

```
https://jim-web.onrender.com/chat?key=YOUR_CHAT_SECRET
```

Then install it — it's a proper PWA, so it gets its own icon and opens fullscreen
with no browser chrome:

- **iOS / Safari** — Share → **Add to Home Screen**
- **Android / Chrome** — ⋮ → **Install app** (or "Add to Home Screen")

The installed app launches straight into the chat: the key is baked into the
manifest's `start_url`, so you never type it again. Bookmark or install once and
you're done.

> **The key is the only thing protecting your chat.** Anyone with that URL can
> talk to Jim and push workouts to your watch. Don't paste it anywhere public.
> To rotate it, change `CHAT_SECRET` in Render and re-install on the phone.

---

## Changing the icon

The home-screen icon is 💪. To change it:

```bash
pip install -e ".[dev]"
python scripts/make_icon.py "🏋️"    # any emoji
git add src/jim/static && git commit -m "New icon"
```

The PNGs are committed and served as static bytes, so production needs neither
Pillow nor an emoji font.

## Troubleshooting

**Chat 500s / "no data" everywhere** — the DB was unreachable at boot, so
migrations were skipped. Check `DATABASE_URL` and redeploy; migrations retry on
every boot.

**Garmin calls fail with an auth error** — the session blob expired. Re-run
`python scripts/garmin_login.py --export` locally and update `GARMIN_TOKENS`.
This is the one thing you'll have to redo periodically; nothing else drifts.

**`GARMIN_TOKENS is only N chars`** — the blob was truncated when pasted. Paste
it whole (it's long); the app now fails loudly rather than silently treating it
as a file path.

**First request after idle is slow** — on Render's `free` plan the web service
spins down after ~15 minutes. `starter` (in the blueprint) stays warm.

**Cron ran at the wrong hour** — `schedule` is UTC. `0 20 * * *` = 21:00 Berlin
in winter, 22:00 in summer. It's deliberately after the training day; shift it if
you want it earlier.
