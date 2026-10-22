# Report Examples

Reference templates and examples for Section 11-compliant AI coaching reports.

---

## Output Format Guidelines

AI systems should structure athlete reports consistently.  
See templates and examples below for annotated reference.

**Pre-Workout Reports must include:**
- Readiness assessment (HRV, RHR, Sleep vs baselines)
- Load context (TSB, ACWR, Load/Recovery, Monotony if elevated)
- Capability snapshot (Durability 7d mean + trend; TID drift if not consistent)
- One Today block per planned session in calendar order (or rest day + next session preview)
- Go/Modify/Skip recommendation with rationale

**Post-Workout Reports must include:**
- Bold dated header and local Data updated (zone only when different from athlete timezone or UTC fallback)
- One-line session summary
- Completed session metrics (power, HR, zones, decoupling, VI, TSS vs planned)
- Plan compliance assessment
- Weekly running totals (polarization, durability 7d/28d + trend, TID 28d + drift, CTL, ATL, TSB, ACWR, hours, TSS)
- Interpretation (2-4 sentences: compliance, key quality observations, load context, recovery note)
- One block per activity with blank-separated time, distance/context, climbs, power, HR and energy groups; separate Terrain, Temperature and Wind lines; descriptive activity power peaks
- Tomorrow as one session per line in start-time order, with sport and time when present; preserve all sessions

Post-workout duration displays round to whole minutes, while eligibility gates retain exact duration_formatted. Use labelled facts without middle-dot separators or hyphen continuation lines; power and HR zones each occupy one line with labels first. Weekly totals has four unlabelled groups: Phase; capability/TID; load/recovery; Hours/TSS. Missing fields stay omitted under the template's existing rules.

**Weekly Reports must include:**
- Session breakdown with compliance status (✅/⚠️/❌)
- Quality session detail (top 2-3 intensity sessions: target vs actual, decoupling, VI)
- Polarization with Grey Zone and Quality tracking, plus TID 7d and TID 28d with drift status
- Durability subsection (7d/28d mean(X) counts, trend, high-drift count)
- Fitness deltas (CTL, ATL, TSB start → end with Δ)
- ACWR with acute/chronic components shown
- Wellness trends with directional arrows and threshold labels
- Section 11 flags (surfaced immediately, not deferred to block)

**Block Reports must include:**
- Week-by-week volume progression with CTL trajectory
- Compliance with reasons for misses/modifications
- Key performance markers with target comparison
- Intensity distribution by week (compare with planned purpose), plus TID 28d as block-scale classification
- Durability by week (catches aerobic efficiency regression across the block)
- Wellness block-over-block comparison with assessment labels
- Phase Progression Check (criteria met Y/N, recommendation, rationale)
- Next block plan with specific targets

See `POST_WORKOUT_REPORT_TEMPLATE.md` for field reference and rounding conventions.  
See `REPORT_HIERARCHY.md` for how data flows between report levels.

**Weather Reports are on request only:** cover all relevant planned outdoor rides in the next five days using matching current route-weather briefs. Use the route name followed by separate Date, Distance and Ascent lines. Give Start, Moving time, Total time, Wind, Gusts, Rain, Temperature and Feels like one labelled line each. Strongest gusts at and the dominant wind effect by distance require the template's supplied-band evidence; omit unsupported claims. Relative to calm air, Headwind estimates added air resistance, Tailwind reduced resistance and Crosswind roughly neutral effect (can slightly help or hinder); Calm requires 0 m/s. Use the producer's 80°/110° classes with the existing coverage, location and tie rules. Put the assumed-start question on its own line, followed by a blank line. Separate identity, facts, maps and rides with blank lines, including before optional Prepare and material Note lines. Use no middle-dot separators or hyphen continuation lines. Weather times use local HH:MM, adding a zone only when different from the athlete's or a UTC fallback; maps/data retain zones. Check expiry even when omitted from text; preserve outlook uncertainty. End report text with one linked line, "Weather data by Open-Meteo, CC BY 4.0." No transformation note, safety tagline, GeoNames line or fetched timestamp belongs in report text; PNG footers stay unchanged. Comparison, Coach note and No route each take one line. Read and show accessible matching PNG pages in order; never describe an unseen map. Only JSON-only, partial or missing/unreadable-map paths add forecast band detail after Feels like, one line per supplied `bands` entry, never aggregated from raw sections. Pre-workout uses the same weather layout directly under each outdoor ride or run only. No forecast report data or maps when route weather is disabled.

**When no planned ride has a usable route within 120 h**, replace the single No route line with the [template's explicit no-route case](WEATHER_REPORT_TEMPLATE.md#no-planned-ride-has-a-usable-route-within-120-h): clear message, ride list and GPX/TCX hint. Only an AI with actual weather-fetch capability and a location resolved under the [shared point-weather rule](../../SECTION_11.md#point-weather-location) may add a separate **Weather at home** block with Place/source and Time lines, never route detail or a replacement inside a ride block. Without fetch capability, say "A home forecast isn't available in this setup." No planned rides at all gets a single no-rides line; the optional home block follows the template's same gates and planned-day rule.

---

For fallback data, the single final attribution names the actual provider: "Weather data by MET Norway, CC BY 4.0." Name both providers on that same line only when separate report blocks use both. Link each provider and the licence.

## Files

| File | Description |
|------|-------------|
| [REPORT_HIERARCHY.md](REPORT_HIERARCHY.md) | Overview of all report types, length norms, and data flow |
| [PRE_WORKOUT_REPORT_TEMPLATE.md](PRE_WORKOUT_REPORT_TEMPLATE.md) | Template structure for pre-workout briefings (no data) |
| [PRE_WORKOUT_REPORT_EXAMPLES.md](PRE_WORKOUT_REPORT_EXAMPLES.md) | Fictional route, rest-day, indoor, multi-session and outdoor-run examples |
| [POST_WORKOUT_REPORT_TEMPLATE.md](POST_WORKOUT_REPORT_TEMPLATE.md) | Template structure for post-workout analysis (no data) |
| [POST_WORKOUT_REPORT_EXAMPLES.md](POST_WORKOUT_REPORT_EXAMPLES.md) | 8 post-workout scenarios plus synthetic new-field excerpts |
| [WEEKLY_REPORT_TEMPLATE.md](WEEKLY_REPORT_TEMPLATE.md) | Template structure for weekly summaries (no data) |
| [WEEKLY_REPORT_EXAMPLES.md](WEEKLY_REPORT_EXAMPLES.md) | 2 anonymized example weekly reports |
| [BLOCK_REPORT_TEMPLATE.md](BLOCK_REPORT_TEMPLATE.md) | Template structure for block reports (no data) |
| [BLOCK_REPORT_EXAMPLES.md](BLOCK_REPORT_EXAMPLES.md) | 2 anonymized example block reports |
| [WEATHER_REPORT_TEMPLATE.md](WEATHER_REPORT_TEMPLATE.md) | On-request five-day planned-route weather |
| [WEATHER_REPORT_EXAMPLES.md](WEATHER_REPORT_EXAMPLES.md) | Synthetic forecast, outlook and missing-data examples |

---

## Report Types

### Pre-Workout Briefing (grouped status and session blocks)
Generated **before** a planned session. Includes:
- Bold Pre-workout date and zone-labelled Data updated header
- Current readiness (HRV, RHR, Sleep vs baselines)
- Load context (TSB, ACWR, Load/Recovery, Monotony if > 2.3)
- Capability snapshot (Durability 7d mean + trend; TID drift if not consistent)
- Four blank-separated status groups without subgroup headings; preserve all template fields and conditionals
- A Today block per session with available type, route facts, duration, TSS and condensed main set; omit an absent structure rather than printing a no-structure line
- Weather directly under outdoor rides and runs only, with labelled home location/source when no route is supplied
- Go/Modify/Skip Recommendation followed immediately by two-to-three-sentence interpretation without a separate heading; expand Modify/Skip

### Post-Workout Analysis (grouped activity blocks)
Generated **after** a completed session. Includes:
- Execution summary (actual vs planned)
- Key metrics (power, HR, decoupling, VI, carbs)
- Zone distribution (Grey Zone and Quality tracking)
- Load impact (updated CTL, ATL, TSB, weekly totals)
- Capability update (Durability 7d/28d + trend, TID 28d + drift in weekly totals)
- Coaching interpretation
- Descriptive W/kg, work, available exact power peaks, elapsed time and sport-aware pace from sync 3.147; peaks never establish FTP, zones or readiness

### Weekly Summary (~35-45 lines)
Generated **end of training week** (Saturday or Sunday morning). Includes:
- Session breakdown with compliance status for every day
- Quality session detail for top 2-3 intensity sessions
- Polarization (Z1+Z2, Grey Zone, Quality) with TID 7d and TID 28d + drift status
- Durability subsection (7d/28d mean(X) counts, trend, high-drift count)
- Fitness deltas with ramp rate and ACWR breakdown
- Wellness trends with week-over-week comparison and directional labels
- Section 11 flags triggered during the week
- Next week preview with any planned modifications

### Block Report (~45-60 lines)
Generated **end of each 3-5 week block**. Includes:
- Week-by-week volume and CTL progression
- Compliance summary with reasons for modifications
- Performance marker tracking (sweetspot, VO2max, decoupling trends)
- Polarization by week to catch grey zone creep, plus TID 28d as block-scale classification
- Durability by week to catch aerobic efficiency regression across the block
- Wellness block-over-block comparison with assessment labels
- Phase Progression Check with explicit criteria evaluation
- Next block plan with targets and key changes

---

## Brevity Rule

These templates follow Section 11's brevity principle:
- **Normal metrics:** Brief (2-3 sentence interpretation + key data)
- **Threshold breach:** Detailed (full analysis with recommendations)
- **Rest day:** Minimal (confirm recovery status, preview next session)
- **Athlete asks "why":** Deep dive on specific area

---

## Conditional Fields

Some fields appear only when relevant:
- **Weather:** Route data for the session takes precedence over any home location for that session's weather. For point forecasts use an explicit current-chat statement first `(you said)`, then `athlete_profile.location` in current `latest.json` `(from Intervals.icu)`, then the current official dossier's Home region `(from dossier)` only when the profile location is null/empty. Show the place and source under the [shared rule](../../SECTION_11.md#point-weather-location). Chat overrides last only for that conversation, never from memory or earlier chats; heartbeat configuration is not a weather-location source. If something indicates the athlete is elsewhere and the location is unresolved, omit weather or ask. City-level text needs [geocoding](../agentic/EXTERNAL_APIS.md#geocoding-for-point-weather); ambiguity or failure means unavailable with the reason. If all three sources lack a location, say "A home forecast isn't available: no home location. Add your city/country to your Intervals.icu athlete profile, or a Home region in your dossier."
- **Monotony:** Include only if > 2.3; omit entirely when normal
- **Load/Recovery tolerance note:** Include only when within 0.2 of threshold
- **Coach notes** (brief contextual tips) are encouraged to humanize recommendations
- **Quality Session Detail (weekly):** Cap at 2-3 key sessions; if 4+ hard days, prioritize most notable

---

## Notes

- Worked report text uses anonymized/placeholder data; replace with actual values from your JSON feed
- Zone percentages round to nearest whole number (see rounding convention in POST_WORKOUT_REPORT_TEMPLATE.md)
- Data flows upward between reports: post-workout → weekly → block (see REPORT_HIERARCHY.md)
- Section 11 flags surface at the weekly level and are summarized with resolution in block reports
