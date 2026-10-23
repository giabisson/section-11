# Managed plan and review integration

The interactive Telegram coach uses the typed `section11_coaching` tool. Its fixed
private profile binds one account, source checkout, data directory and private
store. No operation publishes an event, sends a message, reads arbitrary paths
from model input or treats a stored plan as permission to train.

## Current primary status — 23 October 2026

The primary bridge, context reader and weekly supervisor integration are installed.
Plugin/skill discovery, eight isolated native SDK operations, synthetic review/revision
recovery and three report dry runs passed; the full suite passed 1,317 tests on
both machines. Verified post-cutover Telegram onboarding answers are saved in the
private intake store. A fresh process dated 24 October recovered the same entries
through state and task packets, with previous-day health marked historical.
Keyword-only Gateway memory search works. No real managed plan has been created
(`onboarding_stage:intake_saved_plan_pending`).
The later authorized primary cutover cleared active personal context and the derived
memory index while preserving the original 104-file archive, a current-context
backup, prior conversation records and training history. Telegram onboarding can
continue in the existing chat. Do not reset it again to repair a tool schema.
Current plan state comes from the tool, never from this dated deployment note.
The first actual model-led coaching/review cycle remains a real-use acceptance check.

## Tool-schema compatibility repair

The original plugin declared payload/draft as bare object schemas. In installed
OpenClaw 2026.10.6, normalizeOpenAIStrictCompatSchema converts those to empty closed
objects; nonempty feedback was therefore rejected before Python ran. Direct
execute/registration tests bypassed that validation and missed the defect.

[schemas.mjs](coaching-tool/schemas.mjs) now exposes explicit closed feedback,
proposal/plan/prescription and review-draft contracts. Nullable health clarification
and candidate plans remain explicit. Root-local definitions reuse plan and bounded
repeat-step shapes instead of duplicating them. The root stays a provider-compatible
object; the operation-specific request gate and Python backend still enforce which
payload belongs to which operation. Do not relax additionalProperties or accept
caller-owned safety snapshots to work around conversion errors.

The read-only maintainer check in dev/openclaw_coaching_schema_smoke.mjs reproduces
the old failure and checks valid/invalid fixtures across the declared schema,
installed compatibility conversion, normalization, strict normalization, runtime
projection and provider projection. The isolated SDK save test must validate the
converted arguments before executing the tool. These checks add no model calls,
real feedback, calendar writes or messages. Existing conversation feedback must be
explicitly retried by the coach after a successful reload; a schema repair does
not itself save earlier failed requests.

## Fresh onboarding

Read `{"operation":"state"}`. `onboarding_required` means no real plan has been
proposed, **not** that intake answers were lost. `onboarding_stage` distinguishes
`intake_required` from `intake_saved_plan_pending`. Read the returned `intake`
before questions. Ask only for missing/changed facts, due reviews and current
health/response; do not repeat answered onboarding questions. Existing training
records remain useful evidence; old goals, old conversation summaries and fictional
examples are not current intentions. Missing HRV/RHR does not block onboarding or
progression. Never initialize a sample/default plan to make the store look ready.

### Save intake before a plan exists

Explicit answers supplied for onboarding authorize faithful private recording;
no second permission prompt is needed. First read state, then invoke:

```json
{"operation":"intake","payload":{"request_id":"unique-request-id","parent_revision":null,"entries":[{"key":"equipment","kind":"equipment","text":"Actual athlete-reported equipment, not a default","observed_on":"YYYY-MM-DD","source":"Actual message/date reference","valid_from":null,"valid_until":null,"review_on":null}],"open_questions":[]}}
```

The example is shape only. Supply the actual answers and explicit account-bound
source attribution; never copy sample facts. `parent_revision` is the current
intake revision from state, or null for the first save. Each revision is a complete
snapshot: preserve unchanged entries with their original observation dates and
sources, and use a fresh request ID for changes. Prior revisions remain in private
`state_dir/athlete_intake.sqlite3`; a repeated identical request is idempotent,
conflicting IDs or stale parents fail closed. This store is never distributed.

Entry kinds: goal, availability, equipment, experience, preference,
recovery_constraint, health_observation, follow_up. All fields shown above are
required (nullable dates permitted). Goals, availability, recovery constraints
and follow-ups require `review_on`. Health observations require `valid_until`
equal to `observed_on`; they cannot become timeless clearance. Label inferred
relative dates, preserve reported clearance conditions, and distinguish an
operator-selected recheck date from an actual clinician appointment. Restriction
expiry or a due review never establishes recovery.

Require a successful commit/readback receipt, then read state and verify the
same revision and the actual entries before saying answers are saved. State and
every bounded task packet return the intake independently of plan existence.
Optional context-profile keys `intake_store` and `intake_athlete_id` must be supplied
together, match the private store/account, and point to the runtime state store.
Missing/unavailable intake remains unknown; a failed source read is not permission
to substitute chat memory. The plugin/backend enforce shape, private permissions,
account binding and dates; message attribution is caller-attested, not cryptographic
Telegram authentication. Neither saving intake nor a current-looking record
establishes today's medical clearance, a prescription or calendar approval.

After saving and reading back context, use:

```json
{
  "operation":"propose",
  "payload":{
    "current_athlete_context":{
      "date":"YYYY-MM-DD",
      "source":"Current athlete statement; include its message/date reference",
      "goals_and_availability":"Actual stated goals and constraints, not an inferred schedule"
    },
    "plan":{}
  }
}
```

`plan` is the complete schema-1 `athlete_specific_v1` object from
[COACHING_PLANS.md](../COACHING_PLANS.md): account ID from `state`, plan_id,
revision (request_id/current parent/reason/evidence), goals, block, weeks and
sessions. Use checked templates for exact doses and retrieve the exact applicable
workout reference before prescribing. The synthetic example documents shape only;
never copy its athlete, goals, schedule, fitness reference or prescriptions.
The bridge requires current data/current-day athlete-context attestation, checks
account identity and runs existing plan/capacity/template validation. It cannot
independently authenticate that an LLM's quoted statement came from Telegram;
that limitation is recorded. Proposals remain unpublished.

## Feedback and athlete-requested reviews

Record explicitly supplied **current** feedback:

```json
{"operation":"feedback","payload":{"date":"YYYY-MM-DD","state":"normal","note":"Actual athlete words and observation reference","health_clarification":null}}
```

States: rested/normal/fatigued/weak/symptoms/unknown. Optional health clarification
is `{compatible:boolean,reason:string}`, supplied only when the athlete actually
clarified compatibility. Feedback expires after its local calendar date. It never
removes a producer P0/P1 stop, diagnoses an illness, or replaces completed-session
response with an inferred normal value. Treat interrupted/lost write replies as
uncertain: retrieve state/review records before retrying.

Prepare a past date window, at most 42 dates:

```json
{"operation":"prepare","start":"YYYY-MM-DD","end":"YYYY-MM-DD"}
```

The server reads actual Intervals activities/events with two bounded GETs and
current local readiness/health. It returns the current plan, prescription summaries,
exact identity records and a capture_id. Original snapshots are private and expire
for saving after 15 minutes. Current safety/feedback and plan parent are rechecked
on save; changed evidence requires preparation again. API failures do not become
empty successful snapshots. Pairing remains uncertain without actual applicable
managed publication history. No session is retroactively claimed to have been
prescribed by the new store.

```json
{"operation":"save","capture_id":"CAPTURE_FROM_PREPARE","draft":{"observations":[],"decisions":[{"action":"request_context","session_ids":[],"observation_ids":[],"reason":"Actual unresolved context from this review","next_observation":"The specific athlete response needed"}],"candidate_plan":null}}
```

The draft contains exactly those three fields and at least one sourced decision; the example illustrates shape, not an actual athlete judgment. Observation/decision shapes are in
[ADAPTIVE_REVIEWS.md](../ADAPTIVE_REVIEWS.md). Keep completion, goal attainment and
response separate; missed sessions require sourced causes and create no catch-up
debt. The bridge supplies snapshot, feedback, dates, IDs and trigger. The model
cannot overwrite these fields. Meaningful future adjustments require a complete
validated candidate revision with attributed changes; maintain/request_context
usually has candidate_plan null. The existing transaction commits review/revision
together, deduplicates unchanged evidence and never publishes calendar changes.

Exact prescriptions and managed publication previews remain available through the
existing `coaching_plan.py` CLI with the private store directory. Calendar changes
retain their separate preview/approval requirements. No new calendar write is
performed by this integration.
Interactive tools allow eight operations per identified run, with an 85-second
process bound and 48 KiB complete-output limit. Failed/incomplete acknowledgements
are explicitly uncertain; recover the saved state before another write. The
scheduled report's existing read-only tool limit is unchanged.

## Scheduled weekly and block reviews

The existing weekly supervisor keeps its model, schedule, delivery owner, two-call
generation limit and six **read-only** context-tool budget. It prepares seven
calendar dates normally; when the managed block review date/end is due it uses the
block's observed period. Evidence exceeding 42 dates is explicitly partial. A due
block date does not invent adaptation or automatically progress training.

The same model call returns one bounded JSON object with `report` and `review`.
The supervisor validates the object and saves its review through the same bridge
before caching/delivering the report text. Invalid/rejected reviews fail with no
report delivery. The report agent gains no arbitrary write tool. A cached retry
must still match its saved review, current plan, safety and feedback; an expired
capture or changed dependency prevents delivery. Quiet/unchanged reviews remain
saved but do not send a message or create duplicate revisions. Their receipt is
`not_requested`, never falsely labelled delivered.

With no real managed plan, a weekly report distinguishes saved intake from missing answers; it cannot
claim a block review was saved. The integration is ready before onboarding, but the
real managed plan must come from the athlete's subsequent current Telegram input.
No new model call is added solely to save or retrieve a review.

## Installation and recovery

Install the helper plus `coaching-tool/` and its declared OpenClaw tool contract.
The private `coaching-primary.json` has exactly schema_version=1, install_root,
data_dir, store_dir, state_dir, context_profile, timezone and
scheduled_reviews_enabled. All paths are absolute; records live outside source.
Set `coaching_profile` in the primary report profile and context profile, and set
the latter's `review_store` to the real private store's database path. The reader
returns unavailable until that database exists. New proposals create it; installing
code does not silently import old plans or seed an example.

The current archive preparation is separate from activation. Verify private archive
copies and restore instructions first. Finish/review/test code and deployment
before archiving active context or starting a fresh Telegram session. Preserve
training records, configuration, credentials, existing conversation history and
the secondary account. A prepared backup is not a reset or a new coaching session.

## Validation scope

Synthetic tests exercise the real plan/review store and reader, source ownership,
missing/expired evidence, optional wearables, health stops, idempotency, quiet
reviews, report-save/delivery ordering, source failures and typed transport bounds.
They do not certify model judgment or physiological efficacy. Live deployment
checks must additionally verify plugin registration, private profile paths, actual
stored records in an isolated test store and unchanged primary/secondary routing.

When full intake makes a task packet too large, the builder explicitly defers the
daily/weekly history rows to a separate dated `history` read, retaining complete
intake and readiness/health envelopes. The packet labels deferred counts, the
required window and an evidence digest; omitted rows do not imply absent training
or complete coverage. Retrieve the stated history before a prescription or a
judgment that depends on it. The original byte limit and exact history reader
remain unchanged; oversized remaining content still fails explicitly.
