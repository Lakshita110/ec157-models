# Notion schema mapping (PLAN.md §12 Q1 — resolved)

Notion is a **READ-ONLY source** for Jim, and supplies exactly one thing: the
habits/knee log. Discovered from the live workspace on 2026-07-07. The ID is
defaulted in `config.py:Settings` and overridable via env.

## Databases

| Purpose | Database | ID |
|---|---|---|
| Knee+Habit log | `habits db` (under the `habits` page) | `b872f62a28604573980e983be6fd3143` |

**No tasks DB.** Scheduling context comes from Garmin, so Jim deliberately does
not read Notion tasks (decided 2026-07-12). `tasks `, `My Tasks`, and two
databases from earlier iterations — `training proposals`
(`67d2cfc3c75442c4b373736ad38b1cda`) and `training check-in`
(`b789621918c74bd58568eec9218aeb4c`) — are all **dormant**: Jim never touches
them and they're safe to delete in Notion.

## habits db properties

| Property | Type | Mapping |
|---|---|---|
| `name` | title | ignored (e.g. "@May 27, 2026 - habit journal") |
| `date` | date | `NotionDay.day` query key |
| `pain level` | number (0–10) | `pain_level`; **often blank** — see below |
| `knee pain` | multi-select | mixes severity (`none/mild/moderate/severe`) with locations (`left/right/ankles/hips/quads/shins`); locations → `pain_location`, severity → fallback `pain_level` (none=0, mild=2, moderate=5, severe=8) |
| `pain location` | select (`none/both/right/left`) | fallback for `pain_location` when `knee pain` has no locations |
| `pain notes` | rich text | `pain_notes` |
| `physical therapy` | checkbox | `pt_done` (excluded from `habits`) |
| `cardio`, `reading`, `strength training`, `vitamins`, `dental care` | checkbox | `habits` dict (any new checkbox is picked up automatically) |
| `day score` | formula (number) | `day_score` — a **fraction** (e.g. `0.5`), so it is a float end-to-end; coercing to int silently truncated every partial day to 0 (fixed 2026-07-12, migration `005`) |

## Remaining runtime setup

The agent hits the official Notion API with `NOTION_TOKEN`. Create an internal
integration at notion.so/my-integrations, then share the **habits db** with it
(⋯ menu → Connections). Without the share, queries 404.
