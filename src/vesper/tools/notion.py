"""Notion tools: read the Knee+Habit log and Tasks, write proposals.

Exact property names/types are an open question (PLAN.md §12); the mapping is
isolated in `parse_knee_log_page` / `parse_task_page` so wiring in the real
schema touches one place, and those parsers unit-test against recorded
fixtures without hitting the API."""

import logging
from datetime import date, timedelta
from typing import Any

from vesper.config import settings
from vesper.schemas import NotionDay, StructuredSession

log = logging.getLogger(__name__)

_client: Any = None


def client() -> Any:
    global _client
    if _client is None:
        from notion_client import Client

        _client = Client(auth=settings().notion_token)
    return _client


# --- property extraction helpers (schema-tolerant) -------------------------


def _prop(page: dict[str, Any], name: str) -> dict[str, Any]:
    return page.get("properties", {}).get(name, {})


def _number(page: dict[str, Any], name: str) -> float | None:
    return _prop(page, name).get("number")


def _checkbox(page: dict[str, Any], name: str) -> bool:
    return bool(_prop(page, name).get("checkbox"))


def _text(page: dict[str, Any], name: str) -> str:
    prop = _prop(page, name)
    rich = prop.get("rich_text") or prop.get("title") or []
    if rich:
        return "".join(part.get("plain_text", "") for part in rich)
    select = prop.get("select")
    return select.get("name", "") if select else ""


def parse_knee_log_page(page: dict[str, Any], day: date) -> NotionDay:
    pain = _number(page, "Pain Level")
    score = _number(page, "Day Score")
    habit_props = {
        name: bool(prop.get("checkbox"))
        for name, prop in page.get("properties", {}).items()
        if prop.get("type") == "checkbox" and name != "PT Done"
    }
    return NotionDay(
        day=day,
        pain_level=int(pain) if pain is not None else None,
        pain_location=_text(page, "Pain Location"),
        pt_done=_checkbox(page, "PT Done"),
        habits=habit_props,
        day_score=int(score) if score is not None else None,
    )


def parse_task_page(page: dict[str, Any]) -> str:
    return _text(page, "Name")


# --- tool contracts (PLAN.md §7) -------------------------------------------


def get_notion_logs(day: date) -> NotionDay:
    """Pain level/location, PT adherence, habits, and tomorrow's planned tasks."""
    cfg = settings()
    api = client()

    log_rows = api.databases.query(
        database_id=cfg.notion_knee_log_db_id,
        filter={"property": "Date", "date": {"equals": day.isoformat()}},
        page_size=1,
    ).get("results", [])
    result = (
        parse_knee_log_page(log_rows[0], day) if log_rows else NotionDay(day=day)
    )

    tomorrow = day + timedelta(days=1)
    task_rows = api.databases.query(
        database_id=cfg.notion_tasks_db_id,
        filter={"property": "Due", "date": {"equals": tomorrow.isoformat()}},
        page_size=20,
    ).get("results", [])
    result.tomorrow_tasks = [t for t in (parse_task_page(p) for p in task_rows) if t]
    return result


def write_notion(for_date: date, plan: StructuredSession, rationale: str) -> None:
    """Write the proposal + reasoning to Notion for morning review."""
    cfg = settings()
    steps_text = "\n".join(
        f"- {s.exercise}: {s.sets}x{s.reps or ''}"
        + (f" @ {s.weight_kg}kg" if s.weight_kg else "")
        + (f" ({s.duration_sec}s)" if s.duration_sec else "")
        for s in plan.steps
    )
    client().pages.create(
        parent={"database_id": cfg.notion_proposal_db_id},
        properties={
            "Name": {"title": [{"text": {"content": f"{for_date}: {plan.title}"}}]},
            "Date": {"date": {"start": for_date.isoformat()}},
            "Kind": {"select": {"name": plan.kind}},
        },
        children=[
            _paragraph(f"Est. duration: {plan.est_duration_min:.0f} min"),
            _paragraph(steps_text or "(rest day — no steps)"),
            _paragraph(f"Why: {rationale}"),
        ],
    )
    log.info("wrote proposal for %s to Notion", for_date)


def _paragraph(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
    }
