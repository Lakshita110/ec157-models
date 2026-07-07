# Garmin strength workout JSON (M1)

**Status: UNVERIFIED.** This documents the payload we currently *send*
(`vesper.tools.garmin.build_strength_payload`); the exact shape Garmin
*accepts* for this account/device is the M1 deliverable. Update this file with
the confirmed shape once `scripts/m1_roundtrip.py` puts a workout on the watch.

## What we know going in (PLAN.md §10)

- Write path is the **workout API (JSON)**. FIT structured-workout upload is
  rejected with 406 — do not build on it.
- `python-garminconnect`'s typed workout helpers are cardio-oriented;
  strength/lifting likely needs a hand-built payload.
- Garmin caps workouts at ~50 steps (`GARMIN_MAX_STEPS` in config.py).

## Current best-guess payload

```json
{
  "workoutName": "...",
  "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
  "workoutSegments": [
    {
      "segmentOrder": 1,
      "sportType": {"sportTypeId": 5, "sportTypeKey": "strength_training"},
      "workoutSteps": [
        {
          "type": "ExecutableStepDTO",
          "stepOrder": 1,
          "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
          "endCondition": {"conditionTypeKey": "reps", "conditionValue": 8},
          "description": "Goblet squat",
          "category": "strength",
          "weightValue": 16,
          "numberOfIterations": 3
        }
      ]
    }
  ]
}
```

## Open questions to resolve during M1

1. Does the account accept `RepeatGroupDTO` for sets, or is
   `numberOfIterations` on the step enough?
2. Which `exerciseName`/`category` enums map to my movements (Garmin has a
   fixed exercise taxonomy — free-text `description` may not render on-watch)?
3. Weight units: `weightValue` metric vs. account display units?
4. Does `schedule_workout` need a separate calendar payload for strength?

## Verified shape (fill in after M1 passes)

_TODO: paste the accepted JSON + device screenshots/notes here._
