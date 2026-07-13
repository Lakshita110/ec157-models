from datetime import date, timedelta

from jim.agent.validate import (
    balance_notes,
    fallback_session,
    plan_balance,
    validate,
    validate_plan,
)
from jim.schemas import ExerciseStep, HistoryFeatures, StructuredSession

FOR_DATE = date(2026, 7, 7)


def features(**overrides) -> HistoryFeatures:
    base = {"as_of": FOR_DATE, "window_days": 28, "weekly_volume_min": 200, "days_since_legs": 3}
    base.update(overrides)
    return HistoryFeatures(**base)


def session(**overrides) -> StructuredSession:
    base = StructuredSession(
        for_date=FOR_DATE,
        kind="strength",
        title="test",
        steps=[ExerciseStep(exercise="Bench press", sets=3, reps=8)],
        est_duration_min=45,
    )
    return base.model_copy(update=overrides)


def test_sane_session_passes():
    assert validate(session(), features()).ok


def test_forbidden_exercise_rejected():
    bad = session(steps=[ExerciseStep(exercise="Box Jump", sets=3, reps=5)])
    result = validate(bad, features())
    assert not result.ok
    assert "forbidden" in result.violations[0]


def test_too_many_steps_rejected():
    bad = session(steps=[ExerciseStep(exercise="Bench press", sets=1, reps=5)] * 51)
    assert not validate(bad, features()).ok


def test_session_too_long_rejected():
    assert not validate(session(est_duration_min=180), features()).ok


def test_no_weekly_volume_rule():
    """There is deliberately no weekly cap or progression limit. Capping total
    weekly minutes was a crude proxy that mostly punished normal training: as a
    *weekly* number checked per-day, it rejected any session over ~10% of last
    week's total. Session length is the cap that matters."""
    heavy = session(est_duration_min=90)
    assert validate(heavy, features(weekly_volume_min=550)).ok
    assert validate(heavy, features(weekly_volume_min=100)).ok


def test_leg_day_spacing_enforced():
    legs = session(steps=[ExerciseStep(exercise="Goblet squat", sets=3, reps=8)])
    assert not validate(legs, features(days_since_legs=1)).ok
    assert validate(legs, features(days_since_legs=2)).ok


def test_fallback_is_always_valid():
    fb = fallback_session(session())
    assert fb.kind == "mobility"
    assert validate(fb, features(days_since_legs=0, weekly_volume_min=300)).ok


# --- multi-day plans --------------------------------------------------------


def week(*specs) -> list[StructuredSession]:
    """specs: (day_offset, est_duration_min, exercise)"""
    return [
        session(
            for_date=date(2026, 7, 7) + timedelta(days=off),
            est_duration_min=mins,
            steps=[ExerciseStep(exercise=ex, sets=3, reps=8)],
        )
        for off, mins, ex in specs
    ]


def test_a_full_week_is_buildable_at_any_volume():
    """The bug the athlete hit: a weekly minute budget, checked per-day, made a
    full Mon-Fri plan impossible to build. Volume alone must never reject a day."""
    f = features(weekly_volume_min=340, days_since_legs=None)
    plan = week(
        (0, 75, "PT protocol"), (1, 50, "Bench press"), (2, 60, "PT protocol"),
        (3, 50, "Lat pulldown"), (4, 40, "Hip mobility flow"),
    )
    assert validate_plan(plan, f) == {}

    # even seven long days: length is capped per-day, not per-week
    assert validate_plan(week(*[(i, 110, "Bench press") for i in range(7)]), f) == {}


def test_planned_leg_days_space_against_each_other():
    """Spacing only looked at history, so two planned leg days back-to-back
    both passed."""
    f = features(weekly_volume_min=340, days_since_legs=None)
    plan = week((0, 45, "Barbell squat"), (1, 45, "Romanian deadlift"))
    violations = validate_plan(plan, f)
    assert "2026-07-08" in violations
    assert "leg session only 1 day(s)" in violations["2026-07-08"][0]


def test_planned_leg_day_still_spaces_against_history():
    f = features(days_since_legs=0)   # trained legs today
    plan = week((1, 45, "Barbell squat"))
    assert "2026-07-08" in validate_plan(plan, f)


def test_per_session_rules_still_apply_inside_a_plan():
    f = features(days_since_legs=None)
    plan = week((0, 45, "Box jump"), (1, 200, "Bench press"))
    violations = validate_plan(plan, f)
    assert "forbidden" in violations["2026-07-07"][0]
    assert any("exceeds max" in v for v in violations["2026-07-08"])


# --- balance (advisory) -----------------------------------------------------


def test_plan_balance_splits_loading_work_by_group():
    plan = week((0, 60, "Barbell squat"), (1, 60, "Bench press"), (2, 60, "Lat pulldown"))
    assert plan_balance(plan) == {"legs": 0.333, "push": 0.333, "pull": 0.333}


def test_mobility_and_rest_sit_outside_the_balance():
    """PT is ~70% of this athlete's logged volume and is meant to run daily —
    counting it would swamp every split."""
    plan = week((0, 60, "Bench press")) + [
        session(for_date=date(2026, 7, 8), kind="mobility",
                steps=[ExerciseStep(exercise="Hip mobility flow", sets=1)],
                est_duration_min=90),
        session(for_date=date(2026, 7, 9), kind="rest", steps=[], est_duration_min=0),
    ]
    assert plan_balance(plan) == {"push": 1.0}


def test_conditioning_counts_as_its_own_group():
    plan = [
        session(for_date=date(2026, 7, 7), kind="conditioning",
                steps=[ExerciseStep(exercise="Easy spin", sets=1)], est_duration_min=30),
        session(for_date=date(2026, 7, 8), est_duration_min=30,
                steps=[ExerciseStep(exercise="Bench press", sets=3, reps=8)]),
    ]
    assert plan_balance(plan) == {"conditioning": 0.5, "push": 0.5}


def test_balance_notes_flag_a_dominant_group():
    plan = week((0, 60, "Bench press"), (1, 60, "Shoulder press"), (2, 30, "Lat pulldown"))
    notes = balance_notes(plan)
    assert any("push is 80%" in n for n in notes)
    assert any("nothing for legs" in n for n in notes)


def test_balance_notes_are_quiet_on_a_balanced_plan():
    plan = week(
        (0, 45, "Barbell squat"), (1, 45, "Bench press"),
        (2, 45, "Lat pulldown"), (3, 45, "Plank"),
    ) + [session(for_date=date(2026, 7, 11), kind="conditioning",
                 steps=[ExerciseStep(exercise="Easy spin", sets=1)], est_duration_min=45)]
    assert balance_notes(plan) == []


def test_balance_stays_quiet_on_short_plans():
    """One day is *supposed* to be one-sided; nagging would make the coach pad
    every single session."""
    assert balance_notes(week((0, 60, "Bench press"))) == []
    assert balance_notes(week((0, 60, "Bench press"), (1, 60, "Shoulder press"))) == []


def test_balance_never_rejects_a_day():
    """The whole point: skew is advice, not a violation."""
    f = features(days_since_legs=None)
    all_push = week((0, 60, "Bench press"), (1, 60, "Shoulder press"), (2, 60, "Bench dip"))
    assert balance_notes(all_push)          # it IS skewed...
    assert validate_plan(all_push, f) == {}  # ...and no day is dropped for it
