"""Morning reconcile (Render Cron): read yesterday's Garmin actuals and match
them against the stored suggestion, writing `outcomes` (adherence). This is the
loop-closer that feeds the last-7 summary. `python -m vesper.jobs.reconcile`."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from vesper.config import settings
from vesper.db import connect
from vesper.schemas import ActivitySummary, StructuredSession
from vesper.tools.memory import record_outcome

log = logging.getLogger(__name__)

ADHERENCE_DURATION_TOLERANCE = 0.5  # actual within ±50% of proposed duration

KIND_TO_ACTIVITY_TYPES = {
    "strength": ("strength_training", "fitness_equipment"),
    "conditioning": ("running", "cycling", "walking", "cardio", "elliptical", "swimming"),
    "mobility": ("yoga", "stretching", "breathwork", "other"),
}


def adhered(plan: StructuredSession, actuals: list[ActivitySummary]) -> tuple[bool, str]:
    """Deterministic adherence check: right kind of activity, plausible duration."""
    if plan.kind == "rest":
        return (not actuals, "rest day" + (" violated" if actuals else " respected"))
    expected_types = KIND_TO_ACTIVITY_TYPES.get(plan.kind, ())
    matches = [a for a in actuals if a.type in expected_types]
    if not matches:
        return False, f"no {plan.kind} activity recorded"
    total = sum(a.duration_min for a in matches)
    lo = plan.est_duration_min * (1 - ADHERENCE_DURATION_TOLERANCE)
    hi = plan.est_duration_min * (1 + ADHERENCE_DURATION_TOLERANCE)
    if plan.est_duration_min and not (lo <= total <= hi):
        return False, f"duration off: {total:.0f} min vs proposed {plan.est_duration_min:.0f}"
    return True, f"matched {len(matches)} activity(ies), {total:.0f} min"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from vesper.tools.garmin import get_garmin_today

    yesterday = datetime.now(ZoneInfo(settings().app_timezone)).date() - timedelta(days=1)
    with connect() as conn:
        row = conn.execute(
            "SELECT id, plan FROM suggestions WHERE for_date = %s ORDER BY run_ts DESC LIMIT 1",
            (yesterday,),
        ).fetchone()
    if row is None:
        log.info("no suggestion stored for %s; nothing to reconcile", yesterday)
        return

    plan = StructuredSession.model_validate(row["plan"])
    actuals = get_garmin_today(yesterday).activities
    ok, notes = adhered(plan, actuals)
    record_outcome(
        suggestion_id=row["id"],
        actual_activity_id=actuals[0].activity_id if actuals else None,
        adhered=ok,
        notes=notes,
    )
    log.info("reconciled %s: adhered=%s (%s)", yesterday, ok, notes)


if __name__ == "__main__":
    main()
