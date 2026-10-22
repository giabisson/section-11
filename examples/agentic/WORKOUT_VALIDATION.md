# Checked cycling workout prescriptions

Add `coaching_prescription` to the existing push JSON for checked power workouts. Preview and confirmed creation compile the same structure before any calendar read/write. Every repetition and recovery is expanded, the supplied session window and installed constraints are checked, and the native description/duration are derived. Existing confirmation and uncertain-write handling remain.

This checks numeric dose, not health clearance, truthful athlete inputs, complete plan capacity or training effectiveness. Current feedback, readiness, health, suitability and exact technique still require coaching review. `available_minutes` is a supplied individual-session budget; day/week capacity and calendar conflicts belong to the plan layer.

## Local use

The examples are synthetic. Replace their date, targets, zone bounds, provenance and availability with actual inputs before prescribing.

```bash
python3 examples/agentic/workout_validation.py examples/json-examples/checked_workout.example.json
python3 examples/agentic/workout_validation.py examples/json-examples/checked_complex_workouts.example.json
python3 examples/agentic/push.py push --json my-workout.json
```

The compiler command needs no credentials or network. Its [worked output](../json-examples/checked_workout_output.example.json) contains 3,000 seconds: 1,200 warm-up + 600 work + 600 recovery + 600 cool-down. Push follows its usual setup and defaults to preview. Review the canonical description, duration, reference/warnings and `coaching_validation` before confirmed writing. Never remove a failed prescription to bypass validation.

## Schema 1

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1` |
| `session_template`, `template_version` | Checked ID and matching installed library version, currently `0.9.0` |
| `available_minutes` | Actual supplied session window, including preparation and recovery |
| `fitness_reference` | Named reference power, provenance/status and configured zone bounds |
| `steps` | Ordered explicit steps and bounded repeats |

A step has `role`, integer `seconds` and `target`; optional single-line `label`, integer `cadence_rpm` and `technique` (`high_cadence`/`single_leg`, AE-5 work only) are supported. Roles are `warmup`, `work`, `endurance` (background riding), `recovery`, `set_recovery`, `cooldown`. Labels cannot contain digits or reserved executable syntax such as `ramp`/`freeride`; the renderer supplies those from checked fields and places the cue before the duration. A repeat is `{"repeat": N, "steps": [...]}`. Every included recovery executes, including the final recovery. Omit it by writing a separate final work step. Limits are four nesting levels and 2,000 expanded steps.

A target has `basis` (`ftp`, `ramp_peak_power`, `critical_power`, `watts`), `low`, optional `high`, and contiguous configured `zones`. Relative values are percentages of the explicitly matching reference. `ramp: "up"`/`"down"` preserves direction. Supplied absolute zone bounds are required; no universal FTP multiplier manufactures them or establishes LT1/LT2.

Targets resolve to whole absolute watts, rounding half-up, so a later FTP setting does not silently redefine the selected prescription. Original units/reference remain in the report. A fitness change requires a deliberate revision. Native duration, watts, ranges and ramps follow the [Intervals.icu workout-builder guide](https://forum.intervals.icu/t/workout-builder/1163/1), checked 22 October 2026; live server parsing/device export remains an integration check.

AN-2/AN-3 work steps instead require `{"basis": "max_effort", "zones": [7]}` without numerical power fields. Zone 7 records maximal intent, not a predicted achieved wattage. They render as `- Maximal sprint 10s freeride`, using the maintainer's documented [free-ride syntax](https://forum.intervals.icu/t/workout-builder/1163?page=10). No arbitrary FTP multiple, estimated sprint TSS or ERG setpoint is invented. A warning requires checking the actual trainer/device mode: support and resistance behavior are device-dependent and have not been tested here. Free effort cannot replace ordinary power targets, preparation or recovery.

AN-3 additionally requires `sprint_reference`: `value_watts`, `duration_seconds: 10`, assessment `date`, `source`, and three `set_targets_watts`. Use comparable ten-second power, not instantaneous peak or FTP. For example, 700 W with `[700, 721, 735]` records nondecreasing +3–5% quality goals for sets two/three; `[700, 700, 700]` is the template's maintain-reference regression. Provenance is supplied, not independently verified. These goals appear in the report; they never control ERG or promise increasing maximal output under fatigue.

Supplied `description` and `duration_minutes` must agree with the compiled steps. `target`, when supplied, must be POWER. No TSS is invented; supplied TSS remains a caller estimate. Basic push checks also run, including rejection of boolean/nonfinite duration and TSS.

## Fitness provenance

The reference carries `metric`, positive `value_watts`, `source`, nullable assessment `date`, `method`, `equipment`, `environment`, `status` and `zone_bounds_watts`. Zone keys `"1"`–`"7"` map to `[low, high]` watts. Resolved targets must fit their declared configured bands and the template's allowed bands.

Unknown date/method/equipment produce visible warnings, not invented provenance or an automatic demand for maximal testing. Environment is indoor/outdoor/unknown. Future assessment dates are rejected. Explicit stale/contradictory status, an environment mismatch or an expired athlete-selected `review_after` requires a current `review` with `decision: "use_provisionally"`, date and reason. This records coaching judgment rather than validating it independently. There is no universal FTP age cutoff; preserve illness/testing safeguards when deciding what further assessment is appropriate.

FTP timeline dates now distinguish `setting_recorded` and `setting_observed`. Assessment date, method and equipment remain null because the settings history does not supply them. A setting date must not masquerade as a fitness-test date.

## Scope and installation

The [catalog](../workout-library/workout_constraints.json) now covers all 26 library templates: AE-1–AE-7, SS-1–SS-5, TH-1–TH-2, VO2-1–VO2-5, AN-1–AN-3, MIX-1–MIX-2 and SE-1–SE-2. Guards cover applicable patterns, repetition/set counts, work/recovery timing, zones, cadence, preparation duration/primers and cool-down duration. SS-4 has an explicit smaller-dose variant. Non-numeric suitability and actual technique execution remain outside certification.

| Previously unsupported template | Additional executable checks |
|---|---|
| AE-5 | 4–6 × 5 min Z2 drills, 3 min Z1 rests, explicit single-leg or 100–110 rpm instruction, 60–75 min complete ride |
| AE-6 | 60–120 min easy lead-in including ramp-in, then 30–45 min Z3, optional cool-down, 120–165 min total |
| AE-7 | 3–4 blocks of 30–45 min, strictly increasing nonoverlapping rendered power targets, Z2 until optional final Z3, 90–150 min total |
| SS-3 | 3–4 blocks of 8–10 min, repeating 2 min Z4 / 1 min Z5, only the final segment clipped to block length, 5 min Z1 between blocks |
| VO2-3 | Exactly 5 × 3 min Z5, exactly 180/150/120/90 s Z1 between efforts, no extra final rest |
| AN-2 | 4–6 × 10–15 s maximal free effort immediately after sprint preparation, 5 min Z1 rests, background riding afterward, 60–75 min total |
| AN-3 | Exactly 3 × 5 × 10 s maximal free effort, 3 min between reps, 5 min between sets replacing the final rep rest, comparable sprint reference, 20–30 min cool-down |
| MIX-1 | 6–8 × 2–3 min Z4–Z5, surge starts 10–20 min apart, Z2 background/recovery, 90–120 min complete ride |
| MIX-2 | Three 1 min Z5 efforts followed by two 30 s Z6 efforts, 3–5 min Z2 between efforts, 45–60 min complete ride |
| SE-1 | 4–6 × 8 min Z3, one consistent 50–60 or 70–80 rpm work variant, 4 min Z1 with supplied higher cadence |
| SE-2 | 3 × 10–12 min Z4 at 55–65 rpm, 5–6 min Z1 with supplied higher cadence |

These are explicit operational interpretations of the library, not scientifically validated thresholds. In particular, low/mid-zone wording, subtle progression, individual normal cadence, seated/single-leg execution, health and weekly suitability still require coaching review. Equal spacing is an allowed MIX-1 variant. AN-3's complete listed dose is **90.5–103.5 minutes**, replacing its inconsistent earlier ~60 minute estimate. Do not shorten mandatory recoveries/preparation to make it fit an hour; select a suitable alternative. The [eleven synthetic examples](../json-examples/checked_complex_workouts.example.json) and [worked output](../json-examples/checked_complex_workouts_output.example.json) demonstrate every added format.

`not_yet_checked` is empty. Unknown template IDs still fail explicitly. Routine coaching agents must not rewrite the catalog/library to make a prescription pass. Legacy native descriptions remain usable but return `not_checked`; that is not template/dose validation. Without execution capability, label checks manual rather than claiming the compiler ran.

Reports include separate work, background endurance, recovery and preparation duration components, step count, budget, reference/warnings, evidence caveats and library/catalog/prescription hashes. VO2-5 uses the library's five-minute set rests, not the three-minute Methods/Table 2 rest in the Rønnestad paper; [the takeaways](../../literature/cycling-training/papers/24382021/takeaways.md) retain its conflicting descriptions. Exact reproduction is not claimed.

Install `push.py` and `workout_validation.py` together with the matching catalog/library. Discovery checks the source's sibling `workout-library/`, then the script directory's `workout-library/`, `section11/examples/workout-library/` and `examples/workout-library/`. The first complete pair must match its version/hash; mismatches fail rather than silently selecting another copy. Missing files fail before API access. These checkout changes are not a deployed bundle or regenerated release manifest.
