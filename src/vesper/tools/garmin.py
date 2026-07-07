"""Garmin tools: read today's state, create + schedule structured workouts.

Auth is mobile-SSO via `python-garminconnect`; tokens cache at ~/.garminconnect
and MFA may be prompted on first/expired login. Never hardcode credentials.

The write path is the workout API (JSON) — FIT structured-workout upload is
rejected (406). The exact strength JSON accepted by the account is the M1
unknown; `build_strength_payload` is the current best guess and the accepted
shape must be documented in docs/garmin_strength.md once the M1 round-trip
passes on a real device."""

import logging
from datetime import date
from typing import Any

from vesper.config import settings
from vesper.schemas import ActivitySummary, GarminToday, StructuredSession, WorkoutRef

log = logging.getLogger(__name__)

_client: Any = None


TOKEN_STORE = "~/.garminconnect"


def client() -> Any:
    """Lazily authenticated Garmin client (cached tokens, re-login on expiry)."""
    global _client
    if _client is None:
        from garminconnect import Garmin

        cfg = settings()
        garmin = Garmin(cfg.garmin_email, cfg.garmin_password)
        # Loads cached tokens from TOKEN_STORE when present; otherwise does a
        # full SSO login and dumps fresh tokens there.
        garmin.login(TOKEN_STORE)
        _client = garmin
    return _client


def get_garmin_today(day: date) -> GarminToday:
    """Activities + recovery for `day`. Computation done here; returns summary."""
    api = client()
    iso = day.isoformat()

    activities = []
    for raw in api.get_activities_by_date(iso, iso) or []:
        activities.append(
            ActivitySummary(
                activity_id=str(raw.get("activityId", "")),
                type=str(raw.get("activityType", {}).get("typeKey", "unknown")),
                duration_min=round(float(raw.get("duration") or 0) / 60, 1),
                training_load=raw.get("activityTrainingLoad"),
            )
        )

    stats = api.get_stats(iso) or {}
    sleep = (api.get_sleep_data(iso) or {}).get("dailySleepDTO") or {}
    hrv = ((api.get_hrv_data(iso) or {}).get("hrvSummary") or {}).get("lastNightAvg")

    sleep_sec = sleep.get("sleepTimeSeconds")
    return GarminToday(
        day=day,
        activities=activities,
        hrv=hrv,
        sleep_hours=round(sleep_sec / 3600, 1) if sleep_sec else None,
        body_battery=stats.get("bodyBatteryMostRecentValue"),
        readiness=stats.get("trainingReadinessScore"),
        resting_hr=stats.get("restingHeartRate"),
    )


def build_strength_payload(session: StructuredSession) -> dict[str, Any]:
    """Best-guess Garmin workout-API JSON for a strength session (M1 unknown).

    Cardio has typed helpers in garminconnect; strength needs a hand-built
    payload. Verify against a real account and update docs/garmin_strength.md."""
    steps = []
    for i, step in enumerate(session.steps, start=1):
        end_condition = (
            {"conditionTypeKey": "reps", "conditionValue": step.reps}
            if step.reps
            else {"conditionTypeKey": "time", "conditionValue": step.duration_sec or 60}
        )
        steps.append(
            {
                "type": "ExecutableStepDTO",
                "stepOrder": i,
                "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
                "endCondition": end_condition,
                "description": step.exercise,
                "category": "strength",
                "weightValue": step.weight_kg,
                "numberOfIterations": step.sets,
            }
        )
    return {
        "workoutName": session.title,
        "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
                "workoutSteps": steps,
            }
        ],
    }


def create_garmin_workout(session: StructuredSession) -> WorkoutRef:
    """Create a structured workout via the workout API (JSON path, NOT FIT upload)."""
    api = client()
    payload = build_strength_payload(session)
    resp = api.upload_workout(payload)
    workout_id = str(resp.get("workoutId", ""))
    log.info("created garmin workout %s (%s)", workout_id, session.title)
    return WorkoutRef(workout_id=workout_id)


def schedule_workout(workout_id: str, on: date) -> None:
    api = client()
    api.schedule_workout(workout_id, on.isoformat())
    log.info("scheduled workout %s for %s", workout_id, on)
