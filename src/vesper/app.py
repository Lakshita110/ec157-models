"""Thin FastAPI service (PLAN.md §5): health check + manual trigger. The agent
is a callable, not tied to HTTP — Render Cron invokes the jobs directly."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI

from vesper.agent.loop import run_agent
from vesper.config import settings

app = FastAPI(title="vesper")


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
