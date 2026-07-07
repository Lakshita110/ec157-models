from datetime import date

from vesper.jobs.reconcile import adhered
from vesper.schemas import ActivitySummary, ExerciseStep, StructuredSession

FOR_DATE = date(2026, 7, 6)


def plan(kind="strength", minutes=45.0) -> StructuredSession:
    return StructuredSession(
        for_date=FOR_DATE,
        kind=kind,
        title="t",
        steps=[ExerciseStep(exercise="Bench press", sets=3, reps=8)],
        est_duration_min=minutes,
    )


def activity(type_="strength_training", minutes=45.0) -> ActivitySummary:
    return ActivitySummary(activity_id="a1", type=type_, duration_min=minutes)


def test_matching_activity_adheres():
    ok, _ = adhered(plan(), [activity()])
    assert ok


def test_wrong_kind_does_not_adhere():
    ok, notes = adhered(plan(), [activity(type_="running")])
    assert not ok
    assert "no strength activity" in notes


def test_duration_way_off_does_not_adhere():
    ok, notes = adhered(plan(minutes=60), [activity(minutes=10)])
    assert not ok
    assert "duration off" in notes


def test_rest_day_respected_and_violated():
    ok, _ = adhered(plan(kind="rest"), [])
    assert ok
    ok, _ = adhered(plan(kind="rest"), [activity()])
    assert not ok


def test_multiple_activities_summed():
    ok, _ = adhered(plan(minutes=60), [activity(minutes=30), activity(minutes=25)])
    assert ok
