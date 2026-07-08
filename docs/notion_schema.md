# Notion schema mapping (PLAN.md §12 Q1 — resolved)

Notion is a **READ-ONLY source** for Jim: the habits/knee log and tasks.
Discovered from the live workspace on 2026-07-07. IDs are defaulted in
`config.py:Settings` and overridable via env.

## Databases

| Purpose | Database | ID |
|---|---|---|
| Knee+Habit log | `habits db` (under the `habits` page) | `b872f62a28604573980e983be6fd3143` |
| Tasks | `tasks ` (note trailing space in title) | `6843311f33194f40b65ea7e7c0f47436` |

`My Tasks` also exists in the workspace but is an empty shell (no data source)
— ignore it. Two databases from earlier iterations are **dormant** — Jim no
longer touches them and they're safe to delete in Notion: `training proposals`
(`67d2cfc3c75442c4b373736ad38b1cda`) and `training check-in`
(`b789621918c74bd58568eec9218aeb4c`).

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
| `day score` | formula (number) | `day_score` |

## tasks properties

Title is `task`; dates are `do date` and `due date`; `status` is a status
property (`Not started` / `In progress` / `Done`). "Tomorrow's tasks" =
(do date = tomorrow OR due date = tomorrow) AND status ≠ Done.

## Remaining runtime setup

The agent hits the official Notion API with `NOTION_TOKEN`. Create an internal
integration at notion.so/my-integrations, then share **both databases** (knee
log, tasks) with it (⋯ menu → Connections). Without the share, queries 404.
