"""Payload shaping only — live Garmin calls are exercised by scripts/, not CI."""

from datetime import date

from vesper.schemas import ExerciseStep, StructuredSession
from vesper.tools.garmin import build_strength_payload


def test_strength_payload_shape():
    session = StructuredSession(
        for_date=date(2026, 7, 7),
        kind="strength",
        title="Test session",
        steps=[
            ExerciseStep(exercise="Goblet squat", sets=3, reps=8, weight_kg=16),
            ExerciseStep(exercise="Side plank", sets=2, duration_sec=40),
        ],
        est_duration_min=30,
    )
    payload = build_strength_payload(session)

    assert payload["workoutName"] == "Test session"
    assert payload["sportType"]["sportTypeKey"] == "strength_training"
    steps = payload["workoutSegments"][0]["workoutSteps"]
    assert [s["stepOrder"] for s in steps] == [1, 2]

    reps_step = steps[0]
    assert reps_step["endCondition"] == {"conditionTypeKey": "reps", "conditionValue": 8}
    assert reps_step["weightValue"] == 16
    assert reps_step["numberOfIterations"] == 3

    timed_step = steps[1]
    assert timed_step["endCondition"] == {"conditionTypeKey": "time", "conditionValue": 40}
