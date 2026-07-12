from datetime import date, timedelta

from jim.tools.history import (
    classify_muscle_group,
    compute_features,
    compute_readiness,
    days_since_legs,
    muscle_group_balance,
    pain_trend,
    recent_pain_notes,
    weekly_volume_min,
)

AS_OF = date(2026, 7, 6)


def act(day: date, type_: str, minutes: float) -> dict:
    return {"day": day, "type": type_, "duration_min": minutes}


ACTIVITIES = [
    act(date(2026, 7, 6), "strength_training leg day squat", 45),
    act(date(2026, 7, 4), "running", 30),
    act(date(2026, 7, 1), "bench press session", 40),
    act(date(2026, 6, 20), "cycling", 60),  # outside the 7-day window
]


def test_classify_muscle_group():
    assert classify_muscle_group("Goblet Squat") == "legs"
    assert classify_muscle_group("Bench Press") == "push"
    assert classify_muscle_group("running") == "conditioning"
    assert classify_muscle_group("mystery move") == "other"


def test_weekly_volume_only_counts_last_7_days():
    assert weekly_volume_min(ACTIVITIES, AS_OF) == 45 + 30 + 40


def test_muscle_group_balance_fractions_sum_to_one():
    balance = muscle_group_balance(ACTIVITIES, AS_OF)
    assert set(balance) == {"legs", "conditioning", "push"}
    assert abs(sum(balance.values()) - 1.0) < 0.01
    assert balance["legs"] == round(45 / 115, 3)


def test_days_since_legs():
    assert days_since_legs(ACTIVITIES, AS_OF) == 0
    assert days_since_legs([act(date(2026, 7, 1), "running", 30)], AS_OF) is None


def test_pain_trend_positive_when_worsening():
    logs = [
        {"day": date(2026, 7, d), "pain_level": p}
        for d, p in [(1, 1), (2, 2), (3, 2), (4, 3), (5, 4)]
    ]
    assert pain_trend(logs) > 0.5


def test_pain_trend_handles_sparse_data():
    assert pain_trend([]) == 0.0
    assert pain_trend([{"day": AS_OF, "pain_level": 3}]) == 0.0
    assert pain_trend([{"day": AS_OF, "pain_level": None}] * 5) == 0.0


def test_recent_pain_notes_are_newest_first_with_context():
    logs = [
        {"day": date(2026, 7, 4), "pain_level": 3, "pain_location": "right",
         "pain_notes": "might've been triggered by driving"},
        {"day": date(2026, 7, 6), "pain_level": 5, "pain_location": "wrists",
         "pain_notes": "wrists still poor"},
        {"day": date(2026, 7, 5), "pain_level": None, "pain_location": "",
         "pain_notes": "   "},                                   # blank note skipped
        {"day": date(2026, 7, 3), "pain_level": 2, "pain_location": "left",
         "pain_notes": ""},                                      # no note skipped
    ]
    notes = recent_pain_notes(logs)
    assert notes == [
        "2026-07-06 (wrists, 5/10): wrists still poor",
        "2026-07-04 (right, 3/10): might've been triggered by driving",
    ]


def test_recent_pain_notes_caps_the_list():
    logs = [{"day": date(2026, 7, i), "pain_level": 1, "pain_location": "knee",
             "pain_notes": f"note {i}"} for i in range(1, 12)]
    notes = recent_pain_notes(logs)
    assert len(notes) == 6                 # MAX_PAIN_NOTES
    assert notes[0].startswith("2026-07-11")   # newest first


def test_recent_pain_notes_tolerates_missing_fields():
    assert recent_pain_notes([{"day": date(2026, 7, 6)}]) == []
    assert recent_pain_notes([]) == []


def test_compute_features_assembles_everything():
    logs = [{"day": date(2026, 7, d), "pain_level": d % 3} for d in range(1, 7)]
    daily = [{"day": AS_OF, "readiness": 60}, {"day": date(2026, 7, 5), "readiness": 40}]
    f = compute_features(AS_OF, 28, ACTIVITIES, logs, daily)
    assert f.weekly_volume_min == 115
    assert f.days_since_legs == 0
    assert f.avg_readiness == 50


# --- load & readiness verdict ---------------------------------------------


def _load_act(day: date, load: float) -> dict:
    return {"day": day, "duration_min": 40, "training_load": load}


def test_readiness_uses_training_load_when_present():
    # Steady base of 100/week for 4 weeks, so chronic avg-week = 100.
    acts = [_load_act(AS_OF - timedelta(days=d), 100 / 7) for d in range(28)]
    r = compute_readiness(AS_OF, acts, [{"day": AS_OF, "readiness": 70}])
    assert r.basis == "load"
    assert r.acwr is not None and 0.9 <= r.acwr <= 1.1
    assert r.status == "steady"


def test_readiness_flags_load_spike_as_ease():
    # Light chronic base, heavy last week -> ACWR well above 1.5.
    acts = [_load_act(AS_OF - timedelta(days=d), 5) for d in range(8, 28)]
    acts += [_load_act(AS_OF - timedelta(days=d), 60) for d in range(0, 7)]
    r = compute_readiness(AS_OF, acts, [{"day": AS_OF, "readiness": 65}])
    assert r.acwr > 1.5
    assert r.status == "ease"


def test_readiness_poor_recovery_overrides_to_rest():
    acts = [_load_act(AS_OF - timedelta(days=d), 100 / 7) for d in range(28)]
    r = compute_readiness(AS_OF, acts, [{"day": AS_OF, "readiness": 20}])
    assert r.status == "ease"  # low readiness pulls steady down
    acts_spike = [_load_act(AS_OF - timedelta(days=d), 5) for d in range(8, 28)]
    acts_spike += [_load_act(AS_OF - timedelta(days=d), 60) for d in range(0, 7)]
    r2 = compute_readiness(AS_OF, acts_spike, [{"day": AS_OF, "body_battery": 25}])
    assert r2.status == "rest"  # ease + very low recovery -> rest


def test_readiness_falls_back_to_minutes_without_load():
    acts = [{"day": AS_OF - timedelta(days=d), "duration_min": 30, "training_load": None}
            for d in range(28)]
    r = compute_readiness(AS_OF, acts, [{"day": AS_OF, "readiness": 60}])
    assert r.basis == "minutes"
    assert r.acwr is not None


def test_readiness_no_data_is_steady():
    r = compute_readiness(AS_OF, [], [])
    assert r.status == "steady"
    assert r.acwr is None
    assert r.basis == "none"
    assert "not enough" in r.detail
