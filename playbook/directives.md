# Directives — standing instructions for the nightly agent

<!--
This file IS how you give the agent instructions. Edit it in plain English;
it's loaded into the agent's context every night, so a change here takes
effect on the next run. Keep it short and imperative. The agent treats these
as rules, above its own judgement, below the hard safety guardrail in code.
-->

## Weekly shape

- Three lifting days a week, rotating **Full Body A → B → C** (see
  `base_workouts.yaml`). Never two lifting days back-to-back.
- On non-lifting days, do a **PT routine** (see `pt_routines.yaml`) unless the
  day is a planned rest.
- At least one full rest day a week; add rest when recovery is poor.

## Lifting days

- Schedule the existing Garmin workout for the next letter in the rotation.
  Don't invent a new lifting session unless adapting for pain (below).
- Skip a lifting day and swap to PT or rest if any of: pain ≥ 4/10, readiness
  very low, or a leg session happened in the last 2 days.

## PT days — home vs gym

- If tomorrow's **check-in** sets a location, use it (home → `pt_home`,
  gym → `pt_gym`). The check-in always wins.
- Otherwise default to **gym PT** on weekdays, **home PT** on weekends or when
  tomorrow's tasks/travel mean no gym.
- If you still can't tell, pick home PT — it needs the least equipment.
- Always keep the ★ priority exercise (ankle eversion) in; it's the driver for
  the lateral ankle pain.

## The check-in (my input for tomorrow)

- Read the `training check-in` row dated for the target day. It carries my
  stated focus, active pain points, location, minutes available, and a
  free-text note. Treat it as a strong preference and honor it unless it breaks
  a hard rule or the pain guardrail — then follow the rule and tell me why.
- If minutes are given, fit the session to that budget (trim accessory work,
  keep the priority + iso-anchor moves).
- No check-in = decide from recovery, pain, and the rotation as usual.

## Pain & flare rules (from PT — do not override)

- **Next-morning test.** The verdict is tomorrow's pain, not today's. If
  yesterday's session left me worse, back off ~20% today.
- **2/10 ceiling.** Keep working pain at or below 2–3/10.
- **Flare mode** (pain elevated / knee flaring): keep knee bend to ~60°, drop
  every `skip_on_flare` exercise, prefer PT or easy Zone-2 cardio over lifting.

## Adapting a session

- Prefer scheduling a base template unchanged. Only hand-build a modified
  session when pain/recovery forces a substitution — and when you do, cite the
  PT protocol or a research snippet for the swap.
- Left knee is the reactive one; note left–right asymmetry when it shows up.
