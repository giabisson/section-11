# Adaptive coaching reviews

`coaching_plan.py review --json review.json` closes the stored-plan loop: read a frozen prescription, observe recorded completion and the athlete's response, choose an explained action, validate a concrete future revision, and persist both atomically. The command uses the configured private `--data-dir`, needs no API credentials and sends no calendar writes or messages. Managed calendar publication still requires its own preview and approval.

Exact doses are supplied by the coach within checked templates. This is not an algorithm that infers a universally optimal progression from an RPE, a readiness score or a fixed calendar interval. Its evidence, identity, uncertainty and capacity guards are deterministic; goal attainment, response, causes and health compatibility remain explicitly sourced assessments. See the [coaching evidence register](../../COACHING_EVIDENCE.md).

## Workflow

1. Read current training/readiness data and `coaching_plan.py show --compact`; obtain the relevant immutable prescriptions, actual activity/event records and decision-relevant athlete feedback. Current saved workouts and whole-session averages cannot reconstruct an old main set.
2. Assemble a schema-1 review. Keep current state separate from completed-session feedback. Missing overnight HRV, RHR and sleep are not mandatory questions or restrictions. Ask only unresolved questions that change the decision.
3. Select maintain, progress, reduce, substitute, reschedule or request_context. Give reasons, observation references and the next observation that would support another change. An adjustment needs an executable `candidate_plan`, not just narrative advice.
4. Run the local review. It checks the reviewed parent, observation/prescription pairing, concrete affected sessions, current adverse/uncertain evidence and candidate feasibility. It commits a valid revision and review together or neither. Inspect unresolved questions and original/current revision IDs.
5. Present the intended work, what happened, response and resulting future changes. If calendar changes are wanted, use the separate managed preview/confirmation flow. Publication is never proof of completion.

```bash
python3 examples/agentic/coaching_plan.py --data-dir "$coaching_data_dir" review --json review.json
```

The [synthetic input](../json-examples/coaching_review.example.json) and [worked output](../json-examples/coaching_review_output.example.json) were evaluated against a temporary store and fake calendar. Their revision/prescription/event IDs belong to that demonstration; replace them with actual currently read identities before use. A fresh store has its own namespace. No live coach conversation or LLM output was evaluated by these fixtures.

## Input contract

| Field | Meaning |
|---|---|
| `schema_version` | Integer 1 |
| `review_id`, `parent_revision` | Unique request identity and currently reviewed stored revision |
| `trigger`, `schedule_opt_in` | `athlete` or `scheduled`; scheduled requires explicit true opt-in |
| `assessed_date`, `period` | Current local day; ordered start/end of training reviewed, never future |
| `snapshot` | Athlete ID, source, as_of date, coverage (`complete`/`partial`/`unavailable`), raw activities/events and readiness envelope |
| Snapshot activities | Intervals activity `id`, `paired_event_id`, timezone-qualified `start_date`; use authoritative records, not a guessed date/name match |
| Snapshot events | Intervals event `id`, `paired_activity_id` when supplied; preserve contradictory or duplicate records rather than choosing the convenient one |
| Snapshot readiness | `date`, `recommendation` (`go`/`modify`/`skip`/`unknown`), priority 0–3, `health_clarification_required`; copy the current producer's envelope |
| `observations[]` | session_id, prescription_id, activity_id (nullable), status, cause, goal_attainment, response, source, feedback date and note |
| Observation status | `completed`/`modified`/`missed`/`unknown` |
| Observation cause | `none`/`work`/`availability`/`illness`/`injury`/`fatigue`/`equipment`/`preference`/`unknown` |
| Goal and response | `met`/`partial`/`not_met`/`unknown`; `tolerated`/`unexpectedly_hard`/`adverse`/`unknown`, respectively |
| `current_feedback` | Nullable; current date/state/source/note and nullable explicit health clarification (`compatible`, reason). States: rested/normal/fatigued/weak/symptoms/unknown |
| `decisions[]` | Action, affected future session IDs, reason, supporting observation session IDs and next_observation |
| `candidate_plan` | Null for maintain/context request, otherwise a complete revision using the reviewed parent and fresh proposal request ID |

The source snapshot is supplied by the configured agent, not fetched by this command; its source truth is not independently authenticated. A typical agent reads the actual Intervals activity/event objects using its connected API or raw pull capability and combines them with current sync readiness and dated athlete feedback. `latest.json` compact comparison blocks alone do not supply every required identity/role. Missing raw records produce unresolved evidence, not fabricated matches.

## What is checked

Activity pairing requires one exact activity, one identified event, no conflicting reverse pairing, a timezone-qualified execution time in the observation window, and the applicable stored publication version before execution. A later plan edit is not substituted. Pairing confirms a recorded activity; **formal adherence remains unknown** without the existing typed compliance evaluator. Goal attainment and response are separate, labeled caller assessments. Absence is unknown, even with calendar coverage marked complete. An explicitly sourced missed-session report is useful evidence; it is not training debt or an automatic fitness reduction.

Unexpected difficulty, fatigue, injury/illness context, unresolved pairing or stale readiness cannot support progression. Repeated difficult comparable templates produce an operational review flag for fitness reference, recovery, placement and fueling, not a diagnosis. Two distinct occurrences within the observation lookback trigger that flag; these are engineering choices, not validated overtraining cutoffs. Expected high RPE alone is not an adverse response.

Under adverse/uncertain evidence, an alleged reduction cannot increase aggregate future duration, demanding work time (configured Z3+ intent) or peak work target. These are conservative dose checks, not equivalences of physiological cost. Changed/new/removed sessions must be attributed to decisions, historical selections remain intact, and complete candidate capacity/template checks still apply. Context changes such as availability or event dates create attributable revisions. There is no automatic percentage ramp, missed-session catch-up, FTP reduction or mandatory long ride.

Same-day publication also checks the latest dated review: a stop/current weakness, unresolved health compatibility or missing current data prevents new same-day training writes. A morning modification needs an explicitly reviewed adjusted prescription. Deleting a future session remains possible. Good feedback cannot erase P0/P1; a compatible minor health issue does not itself mean all training is cancelled. These guards do not use today's post-workout load or today's review as tomorrow's readiness. The coach must still review actual symptoms, suitability and the whole plan; metadata is not medical clearance.

## Repeated and scheduled reviews

The journal records the data/decision fingerprint, reviewed and resulting revisions, source snapshot and report. Retrying the same evidence/choices, including after the review's own revision or through a different opted-in trigger, returns the stored result without another revision. Reusing a review ID for changed evidence fails. An external new plan revision needs a new review. Review and proposal writes share one transaction; a failed final journal write rolls both back.

`notify` is an output instruction for the external runtime, not a send operation. Scheduled maintain-only reviews stay quiet; unchanged reruns do not produce another notification. Material changes/unresolved questions can be surfaced according to the configured notification policy. The repository does not enable a schedule, know the Telegram destination, or authenticate opt-in. Both athlete-requested and scheduled paths call the same review command. Never configure a heartbeat to send unchanged status on every run.
