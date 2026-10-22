# Pre-Workout Report Template

> This template defines the standard output format for pre-workout reports.  
> Read `latest.json.data_overview` first for companion availability and route/map status. Resolve paths against that latest file's local folder or URL base; for Manual uploads without folders match by filename. Presence alone does not prove AI access. Weather times use local HH:MM from `display_time`; add a zone only when it differs from the athlete's timezone or is a UTC fallback. The Data updated header retains its date, time and zone. Maps and data fields keep their existing zone/offset labels. Use 16-point compass directions, never degrees. Read matching `route_weather_map.pages` before showing them in order, directly after the report text; identify any missing page. Do not offer maps as downloads or ask the user to download/upload them; use the text brief when unavailable.
> Fields in `[brackets]` are placeholders. Omit fields that don't apply.  
> **Data Freshness:** Take every number from a current read of the source that owns it: training metrics and planned sessions from the source JSON file, stable athlete facts (such as a tested bottle quantity) from the current official dossier, athlete-reported values from the athlete's explicit current statement, and external conditions such as weather from their current source (see SECTION_11.md §Output Format Guidelines). Never take a number from memory or an earlier chat. Do not carry forward values from earlier reports or earlier in the conversation. Re-read before quoting.  
> **Display Units:** For distance / elevation / weight / height / position / speed, quote `display.*` fields from the source JSON; they're pre-converted to the athlete's Intervals.icu preferences. Use canonical metric (`*_km`, `*_m`, `*_kg`) only for calculations. See SECTION_11.md §Display Unit Semantics.

---

```
**Pre-workout: [Weekday D Month]**
Data updated: [local date time + zone; label UTC fallback]

**Current Status Summary**
Phase: [phase_detection.phase] Wk[phase_detection.phase_duration_weeks]
RHR: [XX] bpm (baseline: [XX] bpm)
HRV: [XX] ms (7d avg: [XX] ms)
Sleep: [XhYm]
Sleep Quality: [X/4]

TSB: [X.XX]
CTL: [XX.XX]
ATL: [XX.XX]
ACWR: [X.XX] ([assessment]); start-of-day
Recovery Index: [X.XX] ([assessment])
Ramp Rate: [X.XX]
Load/Recovery: [X.X] (tolerance [X.X]); [context note if near edge]
Durability: [X.XX]% 7d mean([X]) ([trend])
EF: [X.XX] 7d mean([X]) ([trend])
Monotony: [X.XX] ([primary sport] [X.XX], total [X.XX]); [note]

Polarization: Z1+Z2 [XX]%, Z3 [X]%, Z4+ [X]%; [Classification] (PI: [X.XX])
TID 28d: [Classification] (PI: [X.XX]); drift: [shifting/acute_depolarization] [only if not consistent]

Total hours, last 7 days: [XhYm]
Total activities, last 7 days: [XX]
Total TSS, last 7 days: [XXX]

**Today: [session name]**
[type, with outdoor/indoor status when known]
Distance: [route distance in supplied display units; if available]
Ascent: [route ascent in supplied display units; if available]
Terrain: [course_character; if available]
Duration: [formatted duration; if present]
Planned TSS: [session planned TSS; if present]
Main set: [condensed supported structure; if present]

Climbs
[position]: [length] at [avg]% (max [max]%)
[One line per supplied climb; omit unavailable values and the block if none]

Pacing: [one supported sentence connecting terrain to this session's effort]

**Weather on the route**
Start: [HH:MM; append (assumed) when applicable]
[Assumed only: No start time set. When are you leaving?]

Moving time: [formatted moving window]
Total time: [formatted elapsed window]
Wind: [compass] [speed range and supplied units]
Gusts: up to [maximum and supplied units]
Strongest gusts at: [bounds of the band holding the maximum gust; only if supported]
[Dominant wind effect]: [where it applies; only if supported]
Rain: [native-period amount], [probability]% [supported timing]
Temperature: [range]
Feels like: [available range, or unavailable]
[If map unavailable/partial: one line per supplied forecast band, from bands[].display]

Prepare: [supported actionable advice; omit if none]

Note: [only material limits, including missing pages; omit routine diagnostics]

[For an outdoor ride/run without a usable route, replace the route-weather block with:]
**Weather at home**
Place: [place] ([you said / from Intervals.icu / from dossier])
Time: [planned local window, or explicitly labelled daily window]
Temperature: [range]
Feels like: [available range, or unavailable]
Wind: [compass] [speed range and supplied units]
Gusts: up to [maximum and supplied units]
Rain: [native-period amount], [probability]% [supported timing]

Prepare: [supported actionable advice; omit if none]

[Repeat Today and its eligible weather block for each planned session, in plan order]
[If rest day: Rest day: no sessions scheduled.]
[If rest day: Next session: [Day]: [workout preview]]

**Recommendation: [readiness_decision.recommendation: Go / Modify / Skip]**
[2-3 sentences directly below the recommendation: readiness vs baselines, load context,
suitability (proceed/modify/skip with rationale), coach tip.
Use readiness_decision.signals for individual signal values.
If recommendation is Modify, reference readiness_decision.modification
for adjustment directions (intensity/volume/cap_zone).
AI may adjust the recommendation only under the override rules in SECTION_11.md
(Feel/RPE Override): athlete-reported state escalates unconditionally, de-escalation
is P2-only, P0 and P1 are not overridable. State the rationale.]

Weather data by Open-Meteo, CC BY 4.0.
```

Keep four unlabelled status groups separated by blank lines: readiness, load/capability, Polarization/TID, then 7-day totals. Preserve every existing field and conditional below. Omit absent Duration and Main set lines entirely; never print "no structure" or a substitute missing-structure line.

Use workout_summary as source. Condense to main set; omit a warm-up, cool-down or recovery step only where the plan labels it so, since a lower target alone does not make a step recovery. Square-bracketed text in workout_summary (`[step not summarized]`, `[repeat not summarized]`, `[target not shown]`) marks a step, repeat or target the summary could not render. A summary without a marker lists every step with its duration and its power target (or HR target when no power target is set); it does not carry secondary targets such as cadence or an HR target set alongside power, and where it compresses repeated steps it shows them at the first step's value when each is within 2 W and 2 s of that first step. If workout_summary is null or carries a marker, take the plan from whichever of `description` (entries up to 7 days ahead) or `description_preview` (later entries; its first 3 lines only, so say the plan may continue) the entry carries; if that field is absent or empty, report a marked summary as given and say it is incomplete, or for a null summary give the workout name and duration when present, omitting Main set without a missing-structure line. Never invent targets or step roles.

Weather belongs only to an outdoor ride or run, directly beneath that session's details. Indoor sessions, walks and all other sports get no weather, even when home weather is available. A routed run needs an actual matching brief; this layout does not create a forecast or extend sync's cycling eligibility. A usable route with unavailable weather gets its reason, never home substitution. Home forecasts require actual fetch capability and the location gates below; do not print the old point-forecast disclaimer. No weather block on rest days.

No middle-dot separators or hyphen-prefixed continuation lines in report text. Reformat existing display labels into the labelled lines without altering values. Use the [weather template's supported wind/gust and rain rules](WEATHER_REPORT_TEMPLATE.md#supported-wind-gust-and-rain-lines). Dominant wind effect means estimated air resistance relative to calm air: Headwind adds it, Tailwind reduces it and Crosswind is roughly neutral (can slightly help or hinder); Calm is exclusive to 0 m/s. Consume the supplied bands under the producer's 80°/110° rule, preserving coverage, location and tie gates; do not reclassify them. For `start_passed`, print `Start: 10:30 (assumed; planned 10:00 has passed.)` using the supplied times, then `When are you leaving?` on its own line and a blank line. Never retime a cached brief.

The attribution is one line, last in the report text, with linked provider/licence names: `Weather data by Open-Meteo, CC BY 4.0.` Follow the [single-line attribution rule](WEATHER_REPORT_TEMPLATE.md#attribution). Omit it if no forecast values are shown. Do not print a transformation note, safety tagline, GeoNames credit or fetched time in the report; the unchanged PNG footer retains its own notes. The displayed place comes from the athlete's source; GeoNames attribution remains in API documentation and other geocoding displays. Show matching PNG pages that were actually read directly after the report text, in session/page order.

---

## Conditional Fields

| Field | Rule |
|-------|------|
| Phase | Include only when `phase_detection.confidence` is "high" or "medium". Omit when "low" or phase is null |
| Weather | Outdoor rides/runs only. Use the shared [Point-weather location](../../SECTION_11.md#point-weather-location) rule: route data for the session takes precedence over any home location for that session's weather. For a separate point forecast, use an explicit current-chat athlete statement `(you said)` first, then `athlete_profile.location` in the current `latest.json` `(from Intervals.icu)` as the default, then the current official dossier's Home region `(from dossier)` only when `athlete_profile.location` is null/empty. Always show the place and source. The chat override is valid only for that conversation, never from memory or earlier chats; heartbeat configuration is not a weather-location source. If something indicates the athlete is elsewhere and the location is unresolved, omit weather or ask. City-level text requires [Open-Meteo geocoding](../agentic/EXTERNAL_APIS.md#geocoding-for-point-weather); ambiguity or failure means unavailable with the reason, never a guess or a fallback to a lower-priority location. With no location in any source, say "A home forecast isn't available: no home location. Add your city/country to your Intervals.icu athlete profile, or a Home region in your dossier." Actual weather-fetch capability is still required |
| Prepare (weather) | Include only if actionable (e.g., dress warm, indoor day). When forecast triggers heat stress Tier 1+: Tier 1: note hydration emphasis. Tier 2: specify session modification per Environmental Conditions Protocol session-type rules (e.g., "Threshold intervals planned: keep power targets, consider reducing from 4×8min to 3×8min"). Tier 3: recommend reschedule or endurance-only. See **Environmental Conditions Protocol** in SECTION_11.md for tier definitions and session-type rules. |
| Monotony | Include **only** if > 2.3. Omit entirely when normal |
| Durability | Include if qualifying sessions exist. Omit if 0 qualifying sessions in 7d |
| EF | Include if qualifying sessions exist. Omit if 0 qualifying sessions in 7d |
| TID 28d + drift | Include as separate line **only** if drift is "shifting" or "acute_depolarization". Omit entire line when "consistent" |
| Polarization | Weekly Seiler TID rendered in power-zone labels. Source: `seiler_tid_7d.z1_pct/z2_pct/z3_pct`. Render as `Z1+Z2` (Seiler Easy / below LT1), `Z3` (Seiler Grey Zone / LT1–LT2), `Z4+` (Seiler Hard / above LT2). Do not output raw `Z1/Z2/Z3` labels; they collide with the per-session Power zones line above |
| Load/Recovery context | Include tolerance note only when within 0.2 of threshold |
| Next session | Include only on rest days |
| Distance / Ascent / Terrain / Climbs / Pacing | Terrain and climb detail require `has_terrain: true`, `route_status: "ok"` and matching event ID and complete `route_ref` in `routes.json`. Quote supplied `display.position`, `display.distance` and elevation units; gradients use %. Include each supplied climb on its own line, followed by Pacing. `no_elevation` preserves distance/location in `route_geometry`, but never infer flatness, zero ascent, climbs or terrain-adjusted pacing. Omit unsupported fields. State other route limitations when route advice is requested. Full pre-ride briefing available on request |
| Route weather | Only for an `ok` route with matching event, full route_ref, departure, cache_key and brief_id in the summary/detail. Check tier and expiry at report time even when not printed. Use one fact per labelled line with blank lines between identity, facts and maps; band detail only for a missing/unreadable map or partial brief, copied from forecast `bands` after Feels like, never aggregated from raw sections. Outlooks have no bands: show broad trends with uncertain wind direction/rain timing. Identify missing coverage and actual precipitation-period durations; maxima are not ride totals. For `stale`/`unavailable`, give the limitation without claiming current conditions. Omit when disabled. Do not infer safe roads or exposure, or manufacture a Go decision from missing weather. Avoid duplicating a point forecast when the route brief answers the same question. Required provider attribution overrides citation-free formatting; see SECTION_11 Weather Data Source |
| Modify/Skip rationale | Required when recommendation is not "Go" |
| Same-day continuation | Include only when a session has already been completed today and a further session is in question. When triggered, output the **Same-Day Continuation Block** in place of the standard report body, not alongside it. Omit entirely on a first session of the day |

## Readiness Decision Logic

The `readiness_decision` object in `latest.json` provides a pre-computed go/modify/skip recommendation with priority level and individual signal statuses. Use this as the baseline.

HRV, RHR and device-recorded sleep are optional. Missing overnight HRV and its derived RI alone do not restrict ordinary training or progression. Read `input_context` when present: `no_signals_available` means no physiological evidence was evaluated, not a green light. Use completed training, available observations, current athlete feedback and health context. Ask only what could change the decision and has not already been answered; do not require nightly device use or repeat a questionnaire for missing HRV. A `go` is not confirmation of recovery. Preserve P0/P1 protections and Health Context clarification; see Optional wearable data and athlete feedback in SECTION_11.md.

**Signal statuses** are in `readiness_decision.signals` (hrv, rhr, sleep, tsb, acwr, ri, each with green/amber/red/unavailable and raw values).

Check `derived_metrics.readiness_observations` for dates, current status, baseline coverage and issues. Mention limitations only when they affect the decision; do not turn sparse HRV into demands for more nights. Device/protocol provenance may be unknown. `input_context.health_clarification_required: true` requires the existing Health Context clarification regardless of a physiological `go`; null is unknown, not no illness. `signal_count_review` is an audit-only comparison and must not replace the active recommendation. Current Feel must come from the athlete, with relevant current answers reused.

**Phase-adjusted thresholds** are in `readiness_decision.phase_context` (shows which phase modifier shifted the amber threshold).

**Modification guidance** is in `readiness_decision.modification` when recommendation is "modify" (trigger categories + adjustment directions: intensity/volume/cap_zone).

> The `readiness_decision` is the deterministic baseline. The AI may adjust it only under the override rules in **Feel/RPE Override**: athlete-reported state escalates (Go → Modify → Skip) unconditionally; de-escalation is permitted at P2 only, with no more than 2 ambers and an attributed non-training cause; **P0 and P1 are not overridable**. Where contextual factors support a permitted adjustment, state them directly after Recommendation, with no separate Interpretation header.
>
> `signals.acwr` is the **start-of-day** value (the same windows with today's activities excluded), so it does not move when a session is completed today. `derived_metrics.acwr` is live and today-inclusive: retrospective load context only, never used to approve, modify or veto a later same-day session or tomorrow's.
>
> **Sourcing the ACWR status line:** value from `readiness_decision.signals.acwr.value`, label from `derived_metrics.acwr_start_of_day.interpretation`. Do not read `derived_metrics.acwr` for this line; that is the live figure and belongs in the post-workout report.

For the full priority ladder (P0–P3) and signal classification thresholds, see **Readiness Decision** in the protocol.

## Same-Day Continuation Block

Use when a session has already been completed today and a later session is in question. When this block applies it **replaces the standard report body**. Do not also emit Current Status Summary, Today blocks or Recommendation. See **Same-day Continuation** in SECTION_11.md for the decision rules.

```
Same-day continuation: [Go / Modify / Skip]

Morning readiness: [recommendation] P[priority]: [one-line reason]
Completed session: [type, duration]: [within/above/below intent; goal attained?]
Response: [RPE vs work performed; Feel at the time; power-to-HR evidence if the session passes the validity gate, otherwise "not eligible"]
Current state: [solicited: Feel now, soreness, any new pain or symptoms]
Remaining session: [planned/added; purpose and cost]
Decision: [one sentence]
ACWR: start-of-day [X.XX]; live post-session value excluded from this decision
```

- Current Feel must be solicited, not read from `recent_activities[].feel`
- Quote decoupling or EF only when the session passes its gate (`variability_index` ≤ 1.05 and > 0; `duration_formatted` ≥ 90 min for decoupling, ≥ 20 min for EF). Otherwise state that the evidence is not eligible rather than omitting the line silently
- `effort_response: null` is expected on an easy session and is not a data gap. The classifier is calibrated only at IF ≥ 0.65; `intensity_factor` is emitted on a 0–100+ percentage scale, so the cut-off reads as 65 in the JSON and 0.65 as a decimal IF

When comparing completed work to today's prescription, read `recent_activities[].structure_summary` and compare the same identified windows using actual means and durations. Keep intended targets separate, check method/status and issues, and state unavailable structure or roles. No detail fetch is required for this summary comparison. If more detail is needed and `has_structure` is true, load the activity's `session_structure` from intervals.json. After detail expiry the summary is the last captured comparison, not a fresh check. Whole-session average/NP cannot establish main-set power; broad window agreement is not formal adherence or permission to progress.

## Brevity Rule

- **Route weather:** Each eligible Today session gets one labelled weather block. Moving time and Total time are separate; keep the assumed-start question on its own line. Add a blank line before Prepare and before Note, omitting either when unsupported. Use `bands[].display` for necessary forecast fallback detail after Feels like, separating facts with semicolons rather than middle dots. Wind, gusts, temperature and rain use one decimal and collapse equal displayed endpoints; below 0.05 mm with positive probability use `<0.1 mm/h` (retain the actual native period). Render fully supported dry weather as `Rain: dry, 0%`. Reformat labels without changing values. No multi-day comparison here; use WEATHER_REPORT_TEMPLATE.md on request.
- **Weather basis:** Inspect the selected ETA method, calibration counts, stop model, extrapolation, model inputs and route-consistency transfer. Print only material limitations: thin history, generic defaults, aggregate-history proxy or transferred correction, partial coverage, fallback provider or near expiry. Personal windows are planning allowances, not guaranteed coverage or independently validated mountain timing. Main outdoor FTP only; mention a likely stale FTP/zones flag without changing settings or inferring corrected FTP.
- **Weather preparation and departure:** Apply Environmental Conditions Protocol to actionable clothing/fuelling/fluid advice without inventing thresholds or personal tolerances. For assumed reason `unset_time`, the configured default is normally 10:00 local because midnight/date-only is unset. For `start_passed`, retain the rolling departure and original passed `planned_local` on Start, with the question on the next line. With verified agentic capability, preview the exact push.py time update, execute only after confirmation and re-read the next sync's binding. Never silently retime weather. Outlooks use compact `display_wind_from`, not long sector lists.
- **Normal metrics, Go recommendation:** Keep interpretation to 2-3 sentences
- **Threshold breach or Modify/Skip:** Expand with specific reasoning
- **Rest day:** Brief: confirm recovery status, preview next session

## Formatting Rule

- **Durations and sleep:** Always use `_formatted` fields from JSON (e.g., `sleep_formatted`, `duration_formatted`, `total_training_formatted`). Never convert decimal `_hours` fields to display format; the formatted values are pre-calculated from raw seconds and avoid rounding errors.
