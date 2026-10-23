# Managed plan and review integration

The interactive Telegram coach uses the typed `section11_coaching` tool. Its fixed
private profile binds one account, source checkout, data directory and private
store. No operation publishes an event, sends a message, reads arbitrary paths
from model input or treats a stored plan as permission to train.

## Current primary status — 23 October 2026

The primary bridge, context reader and weekly supervisor integration are installed.
Plugin/skill discovery, six isolated native SDK operations, synthetic review/revision
recovery and three report dry runs passed; the full suite passed 1,306 tests on
both machines. No real managed plan has been created (`onboarding_required`).
The private 104-file archive is prepared and verified, but **fresh-start cutover
remains on hold**: active personal context and the current conversation are intact.
Do not reset them or seed a plan merely because code deployment is complete.
The first actual model-led coaching/review cycle remains a real-use acceptance check.

## Fresh onboarding

Read `{"operation":"state"}`. `onboarding_required` means no real plan has been
proposed. Ask the athlete for current goals/event demands, experience, health and
training response, actual time/day constraints and preferences. Existing training
records remain useful evidence; old goals, old conversation summaries and fictional
examples are not current intentions. Missing HRV/RHR does not block onboarding or
progression. Never initialize a sample/default plan to make the store look ready.

After current context is supplied, use:

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
{"operation":"save","capture_id":"CAPTURE_FROM_PREPARE","draft":{"observations":[],"decisions":[],"candidate_plan":null}}
```

The draft contains exactly those three fields. Observation/decision shapes are in
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

With no real managed plan, a weekly report states onboarding is needed; it cannot
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
