# Heartbeat Configuration Template

Copy this file to your agent workspace as `HEARTBEAT.md` and fill in the bracketed values.

---

## Setup

| Setting | Value |
|---------|-------|
| Timezone | [TIMEZONE, e.g., "Europe/Copenhagen"] |
| Notification hours | [START]-[END], e.g., 09:00-22:30 |
| Notification channel | [CHANNEL, e.g., "telegram"] |
| Notification ID | [CHANNEL_ID] |

> Weather is configured separately. See [Weather: moved to cron](#weather-moved-to-cron) below.

### Data Sources

| Source | URL/Path |
|--------|----------|
| Latest JSON | [URL to latest.json] |
| History JSON | [URL to history.json] |
| Archive folder | [URL to archive/] |

---

## Daily Checks

### Training & Wellness
- Fetch latest data from configured JSON source
- Look for patterns and trends over time, good and bad
- Flag anything per Section 11 protocol
- Reference goals from DOSSIER.md
- Follow the athlete's configured notification preference. By default stay quiet when unchanged/non-actionable; notify on a material change or a decision-relevant unresolved question.

---

## Weekly Checks

### Background Analysis
- Run once per week between training weeks (suggested: Saturday 14:00–22:00 or Sunday 20:00 – Monday 10:00)
- Use latest.json for current status, history.json for longitudinal trends, intervals.json for structured session detail, archive/ for recent snapshots
- Compare current week vs previous weeks, current month vs previous months
- Track consistency patterns (sessions per week, missed days)
- Note long-term CTL trends (building, plateauing, declining)
- Identify recurring patterns (e.g., always tired on Mondays)
- Ask athlete about changes in sleep, travel, stress, or illness when you see unexplained shifts
- With a configured durable private plan store, use `coaching_plan.py show --compact` and the shared [adaptive review](../ADAPTIVE_REVIEWS.md) command. Persist reviewed data/revision identities; unchanged reruns produce no duplicate revision/message. Never infer a private path or enable scheduling implicitly.
- Review intended work, authoritative completion pairing, response and causes; keep formal adherence separate. Use a concrete candidate revision when warranted, then obtain separate calendar-publication approval.
- If materially new patterns, decision-relevant questions or anomalies emerge, add them to `topics.md`; do not repeat an already pending question merely because HRV is absent.

### Open Topics (when active topics exist)
- Read `topics.md`
- Pick 1 active topic and advance it with fresh data or new context
- Don't force progress. Skip if nothing new to add
- When a topic reaches conclusion, message athlete and move to Resolved
- New topics are seeded during weekly background analysis

---

## Weather: moved to cron

For planned rides with a route, read sync.py's route weather through `latest.json.data_overview` and the weather report. Neither heartbeat nor cron fetches a separate forecast for those rides.

A separate cron is optional for general/home-location weather when there is no route. Its timing and notification policy are the athlete's choice. An athlete may prefer "silence = not rideable"; that is a notification preference, not a Section 11 rule or a safety assessment.

Use the shared [Point-weather location](../../../SECTION_11.md#point-weather-location) rule: explicit current-chat location first, valid only for that conversation; otherwise `athlete_profile.location` in current `latest.json`, then the current official dossier's Home region only when that profile location is null/empty. Show the place and `(you said)`, `(from Intervals.icu)` or `(from dossier)` in the point-forecast output. Do not store or read a weather location in heartbeat configuration, or carry a chat travel override into a later cron run. If travel is indicated but unresolved, omit weather or ask. Geocode city-level text using [EXTERNAL_APIS.md](../EXTERNAL_APIS.md#geocoding-for-point-weather); ambiguity or failure means unavailable, never a guess.

---

## Notes

- Planned-route weather uses sync's brief/maps; an optional general/home-location cron must not duplicate it (see above)
- Background analysis window should fall between training weeks to avoid mid-week disruption
- Configure scheduling in your agent platform (cron, heartbeat system, etc.) to run checks within notification hours

**Note:** The heartbeat is fully opt-in and disabled by default. It must be explicitly configured by the user. When active, it only performs scheduled analysis (read training data → run protocol checks → write summaries/plans to your chosen location).

