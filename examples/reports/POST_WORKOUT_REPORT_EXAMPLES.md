# Post-Workout Report Examples

## Default quick example (fictional)

Ride review: Wednesday 4 November
✅ Completed 60 min; the matched Z2 window was close to target.
📊 Main block: 45 min averaging 180 W and 137 bpm.
➡️ Keep the next session as planned pending your response.
❓ How hard did it feel, and any shoulder symptoms during or after?

## Extended examples — only when detail is requested

The older examples below illustrate the detailed field catalog, not default message length.

> Anonymized examples showing standard post-workout report format.  
> See `POST_WORKOUT_REPORT_TEMPLATE.md` for field reference. Legacy examples do not supply recorded elevation, so Ascent is omitted. Missing matched-step data is stated explicitly; aggregate numbers are preserved. The fictional field excerpts below illustrate the new producer contract without inventing step actuals for those legacy reports.

The eight legacy scenarios retain their supplied measurements and omit new fields that were not captured. Their timestamps use explicitly labelled UTC fallback because no athlete timezone is supplied. The new-field excerpts are synthetic, including their temperature, elapsed time, W/kg and curve points; they are not Daniel's captured responses.

---

## New-field excerpts (fictional, not full reports)

These independent synthetic records illustrate display values and branch/status wording. They do not revise the historical examples below. A production report includes the remaining applicable session fields and weekly totals. Ascent values are the recorded display values, not calculated from route density or compared across sources.

```text
**Ride: Stepped endurance**
Indoor ride
Moving time: 45m
Total time: 47m
Planned: 45m

Distance: 22.00 km
Ascent: 0 m
Avg speed: 29.3 km/h
Temperature: 21 °C avg (min 20, max 23)

Power: 152 W avg (2.03 W/kg), 156 W NP
Max power: 420 W
Peaks: 5s 390 W, 1m 230 W, 5m 190 W, 20m 160 W
Executed structure: paired_plan_windows, followed; measured 0:01–10:00 target 120 W, actual 119 W; 10:01–30:00 target 180 W, actual 179 W; 30:01–45:00 target 140 W, actual 139 W; all windows agree, 100% power coverage. Roles unspecified; formal adherence unavailable

Work: 410 kJ

**Ride: Free road ride**
Outdoor ride
Moving time: 1h

Distance: 30.00 km
Ascent: 180 m
Avg speed: 30.0 km/h
Terrain: rolling (6 m/km)
Temperature: 12 °C avg (min 10, max 14)
Wind: breezy (4.0 m/s, gusts up to 7.0 m/s)

Climbs
12.0 km: 0.6 km at 3.8% (max 6.0%)

Power: 180 W avg, 205 W NP
Executed structure: fixed_elapsed_thirds, no_plan; three 20m descriptive windows: 170 / 180 / 190 W, 100% power coverage; upstream detected WORK effort shown separately

**Morning walk**
Moving time: 30m

Distance: 2.50 km
Ascent: 45 m
Pace: 12:00 /km

**Indoor run**
Moving time: 30m

Distance: 3.10 mi
Ascent: 0 ft
Pace: 9:41 /mi (6.2 mph)
Temperature: 68 °F avg (min 66, max 70)

Executed structure: fixed_elapsed_thirds, no_plan; power unavailable

**Outdoor run**
Moving time: 40m

Distance: 6.00 km
Ascent: 70 m
Pace: 6:40 /km (9.0 km/h)

Executed structure: fixed_elapsed_thirds, no_plan; power unavailable
```

The same ascent rule applies to indoor walks and all ride/run types. When `display.elevation` is null, omit Ascent; a recorded zero remains visible. Walk/Hike omit Executed structure. Shortened or partly-followed windows must distinguish original planned amount from measured time, each agreement flag and any unobserved steps. A not-followed plan uses descriptive fallback and does not present projected step actuals as execution. A synthetic set descriptor `[8,30,10]` can be reported as “8 × 30 s, measured work 232 s, target 280 W, actual 279 W, match true”; it is not 232 seconds of continuous work.

## Example 1: Clean Endurance Day (Multi-Session)

```
**Post-workout: Thursday 15 January**
Data updated: 15 Jan 14:22 UTC (fallback)

Completed 2h30m endurance ride and rowing as scheduled. Clean aerobic execution throughout.

**Ride: Endurance - Wednesday**
Indoor ride
Start: 09:30
Moving time: 2h30m
Planned: 2h30m

Distance: 76.42 km

Power: 155 W avg, 156 W NP
Executed structure: unavailable in this legacy example; step-power adherence not established
IF: 0.57
Power zones: Z1 12%, Z2 88%
Grey Zone (Z3): 0%
Quality (Z4+): 0%
Session profile: Endurance
Variability Index: 1.01 (good)

HR: 118 avg, 131 max
HR zones: Z1 100%
Cadence: 88 avg
Decoupling: 2.14%
EF: 1.32

Calories: 1396 kcal
Carbs used: 268 g
TSS: 82 (planned 78)
Feel: 2/5 (Good)
RPE: 3/10

**Rowing: Recovery Session**
Start: 12:45
Moving time: 15m

Executed structure: no matched plan windows supplied

HR: 125 avg, 141 max
HR zones: Z1 68%, Z2 32%

Calories: 165 kcal
TSS: 10 (planned 10)

**Weekly totals (rolling 7 days)**
Phase: Build Wk2

Polarization: Z1+Z2 97%, Z3 1%, Z4+ 3%
Durability: 2.14% 7d mean(3) / 2.50% 28d mean(11) (stable)
EF: 1.45 7d mean(4) / 1.42 28d mean(14) (stable)
HRRc: 36 bpm 28d mean(5); 7d: no data
TID 28d: Polarized (PI: 3.18); drift: consistent

TSB: -4.85
CTL: 71.20
ATL: 76.05
Ramp rate: 0.52
ACWR: 1.07 (optimal)
Recovery Index: 0.92

Hours: 12h24m
TSS: 410

**Interpretation**
Planned bike duration was completed; step-power adherence is not established here. Bike decoupling 2.14% over 2h30m shows solid aerobic control.
Rowing stayed in Z1-Z2 as prescribed. Load is tracking well, with manageable TSB.

**Tomorrow**
Ride: Endurance 2h15m, 1h30m @173W
SkiErg: Z2 HR 10m
```

---

## Example 2: Multi-Sport Day (Short Ride + Bike + SkiErg + Walk)

```
**Post-workout: Wednesday 11 March**
Data updated: 11 Mar 18:02 UTC (fallback)

Tempo ride overshot planned load due to terrain; short ride, SkiErg, and walk also logged.

**Ride: Training Session**
Outdoor ride
Start: 09:42
Moving time: 5m

Distance: 1.80 km
Terrain: rolling (12.4 m/km)

Power: 72 W avg, 128 W NP
Executed structure: unavailable in this legacy example
IF: 0.49

HR: 112 avg, 124 max

TSS: 2
Feel: 2/5 (Good)
RPE: 1/10

**Ride: Training Session**
Outdoor ride
Start: 10:05
Moving time: 2h12m
Planned: 2h

Distance: 58.37 km

Power: 142 W avg, 162 W NP
Executed structure: unavailable in this legacy example; whole-session zones remain descriptive
IF: 0.66
Power zones: Z1 30%, Z2 36%, Z3 23%, Z4 9%, Z5 2%
Grey Zone (Z3): 23%
Quality (Z4+): 11%
Session profile: Tempo
Variability Index: 1.14 (variable)

HR: 135 avg, 158 max
HR zones: Z1 84%, Z2 16%
Cadence: 92 avg
Decoupling: -4.12%
EF: 1.20

Calories: 1240 kcal
Carbs used: 258 g
TSS: 95 (planned 65)
Feel: 2/5 (Good)
RPE: 4/10
Effort response: neutral

**SkiErg**
Start: 13:28
Moving time: 12m
Planned: 10m

Executed structure: no matched plan windows supplied

HR: 128 avg, 142 max
HR zones: Z1 65%, Z2 35%

Calories: 118 kcal
TSS: 6 (planned 8)

**Walk: Training Session**
Start: 15:10
Moving time: 38m

Distance: 3.40 km

HR: 82 avg, 98 max
HR zones: Z1 100%

Calories: 156 kcal
TSS: 5

**Weekly totals (rolling 7 days)**
Phase: Base Wk3

Polarization: Z1+Z2 88%, Z3 7%, Z4+ 5%: Polarized (PI: 1.85)
Durability: 3.20% 7d mean(3) / 2.75% 28d mean(12) (stable)
EF: 1.38 7d mean(4) / 1.42 28d mean(15) (stable)
HRRc: 32 bpm 7d mean(2) / 31 bpm 28d mean(8) (stable)
TID 28d: Polarized (PI: 2.42); drift: consistent

TSB: -3.75
CTL: 68.40
ATL: 72.15
Ramp rate: 0.85
ACWR: 1.04 (optimal)
Recovery Index: 0.94

Hours: 11h48m
TSS: 445

**Interpretation**
Main ride overshot planned TSS (95 vs 65), expected given the rolling terrain, with VI and grey
zone confirming the outdoor premium, but HR stayed fully in Z1-Z2. Decoupling (-4.12%) is
not drift evidence at VI 1.14. The short 5m ride is logged separately in breezy, cool conditions; no `description` or `chat_notes` explains it.
SkiErg and walk were easy secondary sessions, and load is tracking normally at ACWR 1.04.

**Tomorrow**
Ride: Threshold 1h15m, 3×10m @245W
```

---

## Example 3: Interval Session with Quality Check

```
**Post-workout: Saturday 17 January**
Data updated: 17 Jan 18:05 UTC (fallback)

Threshold session recorded at the planned total duration. Matched step-power data is unavailable.

**Ride: 3x12min Threshold - Friday**
Indoor ride
Start: 08:15
Moving time: 1h30m
Planned: 1h30m

Distance: 48.23 km

Power: 178 W avg, 205 W NP
Executed structure: unavailable in this legacy example; three planned efforts do not establish three executed steps
IF: 0.80
Power zones: Z1 28%, Z2 31%, Z3 3%, Z4 33%, Z5 4%, Z6 1%
Grey Zone (Z3): 3%
Quality (Z4+): 37%
Session profile: Threshold
Variability Index: 1.15

HR: 138 avg, 162 max
HR zones: Z1 32%, Z2 29%, Z3 14%, Z4 25%
Cadence: 85 avg
Decoupling: 3.82%
EF: 1.49
HRRc: 34 bpm

Calories: 962 kcal
Carbs used: 196 g
TSS: 95 (planned 90)
Feel: 3/5 (Normal)
RPE: 7/10
Effort response: negative

**Weekly totals (rolling 7 days)**
Phase: Build Wk3

Polarization: Z1+Z2 84%, Z3 2%, Z4+ 13%
Durability: 2.95% 7d mean(3) / 2.50% 28d mean(11) (stable)
EF: 1.46 7d mean(4) / 1.43 28d mean(14) (stable)
HRRc: 34 bpm 7d mean(1) / 36 bpm 28d mean(5) (stable)
TID 28d: Polarized (PI: 3.10); drift: consistent

TSB: -11.40
CTL: 72.80
ATL: 84.20
Ramp rate: 0.78
ACWR: 1.16 (optimal)
Recovery Index: 0.88

Hours: 14h45m
TSS: 485

**Interpretation**
The whole-session power does not establish whether the three step targets were met. Z3 at 3% is
an aggregate distribution; step roles cannot be reconstructed from it. Decoupling (3.82%) is not interpretable on an
interval session at VI 1.15. TSB at -11.40 reflects build week loading, with a recovery spin tomorrow. 🔄
```

---

## Example 4: Shortened Session (Modified)

```
**Post-workout: Tuesday 20 January**
Data updated: 20 Jan 12:48 UTC (fallback)

Endurance ride cut short at 1h30m of planned 2h30m due to knee discomfort. SkiErg skipped.

**Ride: Endurance - Monday (modified)**
Indoor ride
Start: 10:02
Moving time: 1h30m
Planned: 2h30m

Distance: 45.14 km

Power: 148 W avg, 149 W NP
Executed structure: ride shortened; matched step windows unavailable in this legacy example
IF: 0.56
Power zones: Z1 19%, Z2 81%
Grey Zone (Z3): 0%
Quality (Z4+): 0%
Session profile: Endurance
Variability Index: 1.01 (good)

HR: 115 avg, 128 max
HR zones: Z1 100%
Cadence: 86 avg
Decoupling: 1.92%
EF: 1.29

Calories: 800 kcal
Carbs used: 153 g
TSS: 47 (planned 78)

**Skipped workout: SkiErg Training Session**
Reason: Precautionary (knee discomfort from ride)

**Weekly totals (rolling 7 days)**
Phase: Base Wk4

Polarization: Z1+Z2 98%, Z3 0%, Z4+ 2%
Durability: 1.92% 7d mean(2) / 2.40% 28d mean(10) (improving)
EF: 1.41 7d mean(3) / 1.42 28d mean(12) (stable)
TID 28d: Polarized (PI: 3.15); drift: consistent

TSB: +2.35
CTL: 70.50
ATL: 68.15
Ramp rate: -0.30
ACWR: 0.97 (optimal)
Recovery Index: 0.95

Hours: 4h15m
TSS: 132

**Interpretation**
Session cut short because of knee discomfort. Aerobic quality during the 1h30m
was excellent (decoupling 1.92%, VI 1.01). TSS 47 vs planned 78 means a lighter day than
intended. Monitor the knee before tomorrow's session; if discomfort persists, consider upper-body only. 🩹
```

---

## Example 5: Rest Day (Active Recovery Walk)

```
**Post-workout: Thursday 22 January**
Data updated: 22 Jan 16:45 UTC (fallback)

Rest day walk in the rain. Low intensity, full recovery zone.

**Walk: Training Session**
Start: 14:30
Moving time: 1h

Distance: 5.10 km

HR: 78 avg, 96 max
HR zones: Z1 100%

Calories: 210 kcal
TSS: 6

**Weekly totals (rolling 7 days)**
Phase: Base Wk2

Polarization: Z1+Z2 97%, Z3 0%, Z4+ 3%
Durability: 2.30% 7d mean(3) / 2.55% 28d mean(11) (stable)
EF: 1.44 7d mean(4) / 1.43 28d mean(13) (stable)
TID 28d: Polarized (PI: 3.22); drift: consistent

TSB: +0.85
CTL: 73.10
ATL: 72.25
Ramp rate: -1.20
ACWR: 0.82 (optimal)
Recovery Index: 0.91

Hours: 15h30m
TSS: 498

**Interpretation**
Easy recovery walk, entirely in Z1 as expected on a rest day. TSB positive at +0.85,
recovering well heading into tomorrow's interval session. Braved the rain at 4°C too. 🌧️
```

---

## Example 6: Long Endurance Ride with DFA a1 Drift Flag

Fictional schema-2 scenario: the full 4h12m recording has verified 1 Hz timing and passes endpoint coverage, sixth coverage and gap checks. `drift_quality.status` is `eligible`, reasons are empty and `interpretable` is true. The session structure confirms continuous easy/endurance work without hard blocks. Fuel and fluid intake were not recorded; "Carbs used" is estimated expenditure, not intake.

```
**Post-workout: Sunday 8 February**
Data updated: 8 Feb 16:30 UTC (fallback)

Long Z2 ride finished 12 minutes beyond plan, with an eligible negative DFA contrast between the original first and last thirds; review fueling, heat and fatigue context.

**Ride: Long Endurance - Saturday**
Outdoor ride
Start: 09:15
Moving time: 4h12m
Planned: 4h

Distance: 118.50 km
Terrain: rolling (8 m/km)

Power: 168 W avg, 171 W NP
Executed structure: continuous easy/endurance confirmed by the supplied scenario context; plan-window mapping unavailable
IF: 0.71
Power zones: Z1 18%, Z2 78%, Z3 4%
Grey Zone (Z3): 4%
Quality (Z4+): 0%
Session profile: Endurance
Variability Index: 1.02 (good)

HR: 132 avg, 154 max
HR zones: Z1 62%, Z2 36%, Z3 2%
Cadence: 87 avg
Decoupling: 6.85%
EF: 1.30
HRRc: 28 bpm
DFA a1: 0.94 avg, 38% easy/52% endurance/10% tempo/0% supra (drift -0.31, eligible)

Calories: 2480 kcal
Carbs used: 412 g
TSS: 218 (planned 210)
Feel: 3/5 (Normal)
RPE: 6/10
Effort response: negative

**Weekly totals (rolling 7 days)**
Phase: Base Wk4

Polarization: Z1+Z2 92%, Z3 5%, Z4+ 3%
Durability: 4.50% 7d mean(3) / 3.20% 28d mean(13) (declining)
EF: 1.36 7d mean(4) / 1.41 28d mean(15) (declining)
HRRc: 30 bpm 7d mean(2) / 33 bpm 28d mean(9) (declining)
TID 28d: Polarized (PI: 2.95); drift: consistent

TSB: -8.20
CTL: 78.40
ATL: 86.60
Ramp rate: 0.92
ACWR: 1.10 (optimal)
Recovery Index: 0.86

Hours: 13h05m
TSS: 528

**Interpretation**
The ride exceeded planned duration by 12 minutes; the easy/endurance DFA split is consistent
with the prescription. The eligible -0.31 contrast is below -0.2 on confirmed steady
endurance cycling, so it warrants a possible physiological-drift flag and context review,
not a diagnosis: missing hard efforts or selective loss can still bias an eligible contrast.
Calm, cool conditions do not support a heat explanation here, and fuel/fluid intake is unknown;
412g is estimated carbohydrate use, so it cannot establish underfueling or justify a new
intake target; review intake and accumulated fatigue alongside decoupling and subjective
response, while DFA alone does not change readiness or tomorrow's plan.

**Tomorrow**
Ride: Recovery 1h, Z1 only
```

---

## Example 7: Sweet Spot Session with Consonant DFA Reading

Fictional schema-2 scenario: 5100 original slots (85 recorded minutes), sufficient session data and passing timing/coverage/gap checks. The only drift reason is `short_session`; 3% supra does not trigger the >15% veto.

```
**Post-workout: Tuesday 10 February**
Data updated: 10 Feb 11:45 UTC (fallback)

Sweet spot session recorded; DFA a1 describes the internal response to the intended intensity.

**Ride: 4x10min Sweetspot - Tuesday**
Indoor ride
Start: 09:00
Moving time: 1h25m
Planned: 1h25m

Distance: 42.85 km

Power: 195 W avg, 215 W NP
Executed structure: matched work-step actuals unavailable in this legacy example
IF: 0.79
Power zones: Z1 22%, Z2 28%, Z3 8%, Z4 38%, Z5 3%, Z6 1%
Grey Zone (Z3): 8%
Quality (Z4+): 42%
Session profile: Sweetspot
Variability Index: 1.10

HR: 142 avg, 158 max
HR zones: Z1 25%, Z2 33%, Z3 22%, Z4 20%
Cadence: 89 avg
Decoupling: 2.45%
EF: 1.51
HRRc: 32 bpm
DFA a1: 0.78 avg, 18% easy/35% endurance/44% tempo/3% supra (drift +0.04, descriptive_only: short_session, under 90 recorded minutes)

Calories: 825 kcal
Carbs used: 168 g
TSS: 88 (planned 85)
Feel: 2/5 (Good)
RPE: 6/10
Effort response: neutral

**Weekly totals (rolling 7 days)**
Phase: Build Wk2

Polarization: Z1+Z2 81%, Z3 6%, Z4+ 13%
Durability: 2.80% 7d mean(2) / 2.95% 28d mean(12) (stable)
EF: 1.48 7d mean(3) / 1.45 28d mean(14) (improving)
HRRc: 33 bpm 7d mean(2) / 32 bpm 28d mean(8) (stable)
TID 28d: Polarized (PI: 3.05); drift: consistent

TSB: -6.50
CTL: 76.20
ATL: 82.70
Ramp rate: 0.65
ACWR: 1.08 (optimal)
Recovery Index: 0.93

Hours: 8h12m
TSS: 295

**Interpretation**
Step-power adherence is not established by these aggregates. DFA a1 sat predominantly
in the 0.5–0.75 tempo band (44%) where sweet spot work should land per the protocol
threshold mapping; internal intensity matched prescription. Drift +0.04 is descriptive only
because the recording is under 90 minutes; the 3% supra share does not trigger the supra
veto or establish that the contrast is structural. No physiological drift flag applies,
and this interval session would also fail the separate steady easy/endurance context rule.

**Tomorrow**
Ride: Endurance 2h, Z2 steady
```

---

## Example 8: Threshold Intervals with Positive Effort Response

```
**Post-workout: Tuesday 17 February**
Data updated: 17 Feb 10:30 UTC (fallback)

Post-deload threshold session recorded; RPE came in notably low for the IF achieved. Fitness/freshness tell.

**Ride: 4x10min Threshold - Tuesday**
Outdoor ride
Start: 08:30
Moving time: 1h30m
Planned: 1h30m

Distance: 47.20 km
Terrain: flat (3 m/km)

Power: 210 W avg, 238 W NP
Executed structure: matched work-step actuals unavailable in this legacy example
IF: 0.88
Power zones: Z1 16%, Z2 22%, Z3 5%, Z4 52%, Z5 4%, Z6 1%
Grey Zone (Z3): 5%
Quality (Z4+): 57%
Session profile: Threshold
Variability Index: 1.13

HR: 148 avg, 168 max
HR zones: Z1 18%, Z2 22%, Z3 26%, Z4 32%, Z5 2%
Cadence: 88 avg
Decoupling: 2.10%
EF: 1.61
HRRc: 38 bpm

Calories: 892 kcal
Carbs used: 182 g
TSS: 117 (planned 115)
Feel: 1/5 (Strong)
RPE: 5/10
Effort response: positive

**Weekly totals (rolling 7 days)**
Phase: Build Wk1

Polarization: Z1+Z2 84%, Z3 4%, Z4+ 12%
Durability: 2.30% 7d mean(2) / 2.65% 28d mean(11) (improving)
EF: 1.58 7d mean(3) / 1.50 28d mean(13) (improving)
HRRc: 38 bpm 7d mean(2) / 34 bpm 28d mean(9) (improving)
TID 28d: Polarized (PI: 3.12); drift: consistent

TSB: 3.20
CTL: 72.50
ATL: 69.30
Ramp rate: 0.45
ACWR: 0.95 (optimal)
Recovery Index: 1.08

Hours: 7h48m
TSS: 312

**Interpretation**
Threshold work at IF 0.88 with RPE 5, below the 6–8 band for this intensity, and notable on a
cold, breezy day where thermal cost may increase RPE. Coming off a deload week with positive
TSB (+3.2) and improving HRRc trend, this reads as fitness showing through rather than a
measurement error. Decoupling (2.10%) and session EF (1.61) are not interpretable at VI 1.13;
the improving 7d EF mean comes from other steady sessions and is context only. Neither athlete nor AI should over-read a single positive session, but
the pattern is worth naming: if the next two threshold touches hold at similar IF with RPE in
the low-to-mid range, that's a fitness signal the block is working.

**Tomorrow**
Ride: Endurance 2h, Z2 steady
```

---

