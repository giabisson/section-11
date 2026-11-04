# Report Hierarchy Overview

Section 11-compliant AI coaching reports follow a layered structure. Each level builds on the one below it.

---

## Default delivery

**Default coaching reports are quick briefs.** Lead with an explicit decision/result,
then the session/key result, one reason, next action and at most one focused question.
Use consistent, sparing emojis (✅ proceed, 🔧 adjust, 🛑 skip/stop, ❓ answer needed)
and short labelled lines. Morning/post-workout target 80–120 words; weekly 120–180;
block 150–220; season 180–250. These are targets, not safety truncation limits.
Use at most two supporting numerical observations, excluding prescription targets
and essential safety facts. Omit normal dashboards, routine missing-wearable lists,
priority codes and repeated caveats. Read/check all relevant evidence internally;
only show limitations that affect the decision. Pending health clarification leads
with Hold/check needed, never a green Go with a later caveat. Preserve all P0/P1,
health, optional-wearable, source and validity rules. Assess completion, goal and
response separately without requiring separate visible sections. Keep validated
managed reviews complete; concise delivery does not reduce durable evidence.
Detailed layouts below and legacy examples apply only on an explicit request for
detail. Use the compact sections at the start of each report template by default.

## Detailed Report Types & Length Norms (only on request)

| Report Type | Trigger | Target Length | Purpose |
|-------------|---------|---------------|---------|
| **Pre-Workout** | Before each session | Four status groups, then a Today block per session; weather under outdoor rides/runs only | Readiness check, Go/Modify/Skip followed immediately by interpretation |
| **Post-Workout** | After each session | ~25-30 lines | Session analysis, execution quality |
| **Weekly** | End of training week | ~35-45 lines | Compliance, trends, weekly fitness delta |
| **Block** | End of 3-5 week block | ~45-60 lines | Phase assessment, progression decision |
| **Season** | On-demand only | ~55-70 lines | Annual-arc trajectory, YoY metrics comparison |
| **Weather** | On request only | One fact per labelled line; separate identity, facts and maps; one line each for comparison/coach/no-route in mixed-route reports; explicit no-route case otherwise | Five-day route forecast/outlook and practical preparation |

---

## Information Flow Between Reports

```
Pre-Workout → Post-Workout → Weekly → Block → Season
    │              │             │         │       │
    │              │             │         │       └─ Annual arc + YoY metrics (on-demand)
    │              │             │         └─ Phase progression decision
    │              │             └─ Aggregates post-workout data
    │              └─ Quality metrics feed weekly detail
    └─ Readiness informs session execution
```

**Key principle:** Data flows upward. Each report level summarizes and contextualizes the level below.

**Weather is a parallel planning report**, sourced directly from matching current route-weather briefs, not aggregated from completed sessions. It covers all relevant rides in the next five days and may inform the same-day pre-workout block. It does not replace readiness, infer a Go decision, reschedule training or promote an outlook into section-level certainty. Missing/stale/disabled data stay explicit. Read and show accessible matching PNG pages in their listed order; never describe an unseen image. Expand into band detail only for missing/unreadable pages, JSON-only access or partial briefs, reading forecast `bands` directly rather than aggregating raw sections, one line per band after Feels like. Use separate labelled identity/weather facts, including Moving time and Total time, and an assumed-start question on its own line. Strongest gusts at and dominant wind effect by distance require supported band locations; omit them when unsupported. Wind effect estimates air resistance relative to calm air: Headwind adds it, Tailwind reduces it, Crosswind is roughly neutral (can slightly help or hinder), and Calm requires 0 m/s. Use supplied 80°/110° classes under the weather template's coverage and tie rules. Add blank lines before optional Prepare and material Note lines. Separate blocks with blank lines; no middle-dot separators or hyphen continuation lines. Weather clocks use local HH:MM unless a differing zone or UTC fallback needs a label. Always check expiry. End report text with one linked line, "Weather data by Open-Meteo, CC BY 4.0.", without a transformation note or separate GeoNames line. Maps and data labels remain unchanged.

When no planned ride has a usable route within 120 h, use the [template's explicit no-route case](WEATHER_REPORT_TEMPLATE.md#no-planned-ride-has-a-usable-route-within-120-h), including the ride list and GPX/TCX hint. Only actual fetch capability plus a location resolved under the [shared point-weather rule](../../SECTION_11.md#point-weather-location) allows a separate **Weather at home** block with labelled Place and Time lines; it never substitutes for route weather inside a ride block. Always show the place and source: current-chat statement first `(you said)`, then current `athlete_profile.location` `(from Intervals.icu)`, then dossier Home region `(from dossier)` only when the profile location is null/empty. Without fetch capability, say "A home forecast isn't available in this setup." No planned rides at all gets the single no-rides line, with the home block optional under the same capability/location and planned-day gates.

For fallback data, the single final attribution uses the actual provider name: "Weather data by MET Norway, CC BY 4.0." Name and link both providers on that line only when separate report blocks use both.

- **Post-Workout** metrics (decoupling, VI, target compliance) appear in **Weekly** Quality Session Detail
- **Weekly** fitness deltas (CTL, ATL, TSB) appear week-by-week in **Block** Volume Progression
- **Section 11 Flags** surface at the **Weekly** level and are summarized with resolution in **Block** reports
- **Wellness trends** use week-over-week at Weekly level, block-over-block at Block level
- **Capability metrics** (durability, EF, TID drift) appear as one-liners in Pre/Post, get full treatment in Weekly/Block:
  - **Pre-Workout:** Durability 7d mean(X) + trend (one line). EF 7d mean(X) + trend (one line). TID 28d + drift as separate line, only if not "consistent"
  - **Post-Workout:** Per-session EF. Durability 7d/28d mean(X) + trend in weekly totals. EF 7d/28d mean(X) + trend in weekly totals. TID 28d classification + drift
  - **Weekly:** Durability subsection with mean(X) counts + high-drift count. EF subsection with mean(X) counts + trend. TID 7d + TID 28d on separate lines
  - **Block:** Durability by Week with mean(X) (trajectory across block). EF by Week with mean(X) (trajectory across block). TID 28d as block-scale classification. Per-week classification conditional (only when diverging from block TID)
  - **Season:** Capability metrics (durability, EF, HRRc, sustainability) intentionally absent in v1: `weekly_180d` rows do not carry rolled-up capability means. Adding them requires a separate weekly capability rollup; parked for v2

---

## Detailed layout consistency rules (only on request)

All report types share these formatting principles:

1. **Data first, prose for interpretation only**: structured line-by-line, not bullet summaries
2. **Scannable in 30 seconds**: most important info at the top
3. **Assessment labels in parentheses**: (good), (optimal), (flag) after metrics
4. **Directional arrows**: ↑/↓/→ for trends with threshold-based labels
5. **Section 11 flags surface immediately**: never deferred to a later report
6. **Capability metrics scale with report scope**: one-liner in pre/post, subsection in weekly, by-week breakdown in block
7. **Interpretation at the end**: 2-5 sentences of coaching interpretation

---

## Files

| File | Description |
|------|-------------|
| `PRE_WORKOUT_REPORT_TEMPLATE.md` | Pre-workout briefing template |
| `PRE_WORKOUT_REPORT_EXAMPLES.md` | 4 anonymized pre-workout examples |
| `POST_WORKOUT_REPORT_TEMPLATE.md` | Post-workout analysis template |
| `POST_WORKOUT_REPORT_EXAMPLES.md` | 4 anonymized post-workout examples |
| `WEEKLY_REPORT_TEMPLATE.md` | Weekly summary template |
| `WEEKLY_REPORT_EXAMPLES.md` | 2 anonymized weekly examples |
| `BLOCK_REPORT_TEMPLATE.md` | Block report template |
| `BLOCK_REPORT_EXAMPLES.md` | 2 anonymized block examples |
| `SEASON_REPORT_TEMPLATE.md` | Season report template |
| `SEASON_REPORT_EXAMPLES.md` | 2 synthetic season examples |
| `WEATHER_REPORT_TEMPLATE.md` | On-request five-day route-weather report |
| `WEATHER_REPORT_EXAMPLES.md` | Synthetic forecast, outlook, partial and unavailable examples |
