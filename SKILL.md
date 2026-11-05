---
name: section-11
description: Endurance cycling coaching (v11.85): training questions, workouts, plans and reviews. Read fresh athlete data before numeric or prescriptive advice. Use the configured typed coaching tools when installed.
---

# Section 11 coaching

Read this entry in full. Use `SKILL_REFERENCE.md` only for setup/manual operations. The protocol and relevant workout templates remain the
coaching authorities. Examples are fictional, never athlete facts.

## Managed planning: finish within the exchange budget

When `section11_context` and `section11_coaching` are configured, use them instead
of shell reads, manual storage discovery or generic setup. Both typed tools are directly visible; call them without search/describe.
Only on older installs with hidden schemas, use `tool_call` with exact names.

1. For a continuation with unchanged saved goals, call
   `section11_coaching` with
   `{"operation":"planning_setup","payload":null,"references":[{"source":"protocol","heading":"B"},{"source":"workouts","heading":"AE-1"}]}`.
   In the **same model turn**, request `section11_context`
   `{"operation":"build","task":"plan"}`. These are independent reads when
   payload is null. If needed, describe `section11_coaching` in that same turn to
   obtain the full `propose` schema. Through Tool Search, each call uses
   `tool_call` with `id` equal to the exact tool name and `args` equal to its input.
   If the athlete supplied new dated session/health feedback, include it in setup
   as optional `feedback:{date,state,note,health_clarification}`. State must be
   `rested|normal|fatigued|weak|symptoms|unknown`; put other wording in note. Use null health
   clarification unless compatibility was explicitly established). It saves before
   optional reads; verify `feedback_receipt`. Never postpone feedback until history.
2. The task packet supplies fresh source/health evidence and saved intake. Setup
   supplies the current managed-plan revision, existing prescription references,
   long-term summary and reference bodies (or explicit retrieval errors).
   Verify both whole JSON packets and `packet_complete:true`; obey source dates,
   coverage, conflicts, health gates and any `required_retrieval` dependencies.
   Do not refetch unchanged sources, reread these references separately or repeat
   intake questions. Read full state only if omitted prior metadata is needed to
   reuse that metadata. A replacement future block uses fresh intake/evidence;
   old prescriptions/receipts stay in immutable parent history. References outside
   the new block may be omitted from its session list; never rewrite history.
   If recent training detail is needed, call the known context inputs directly:
   `{"operation":"history","start":"YYYY-MM-DD","end":"YYYY-MM-DD","tier":"daily"}`
   and `{"operation":"activities","task":"plan"}`. Batch independent reads; no describe round
   is needed for these documented shapes. Choose dates for the actual question.
3. Build the actual progression from the verified evidence and current request.
   Use `section11_coaching` `propose`, with `payload.current_athlete_context` and
   the complete schema-1 `payload.plan`, including required `weeks` even when
   `sessions` is empty. Each week needs start_date, weekly_minutes, session_windows,
   intensity_approach and compromises; `week_summaries` is not that schema. Omit
   unknown availability instead of representing it as zero. Use the parent and a
   fresh request ID. A framework or intention is not a saved plan. Check the
   successful persisted revision receipt before claiming completion. Give a
   short summary of progression, review/checkpoints and anything pending.
   Plan persistence does not publish or authorize calendar changes.

For **changed** goals, availability, equipment or recovery constraints: first
read saved intake in a fresh task packet, then use `planning_setup` with the full
updated intake payload and relevant references. Preserve unrelated entries,
original dates/source attribution and current parent revision. Save these facts
before optional reference/history work, including with an active plan. Verify the
intake receipt independently if later planning reads fail. Standalone factual
updates use `intake`. Faithful storage of explicit athlete input is authorized;
do not request duplicate approval. A feedback note or memory is not intake.

Context batches use `{"operation":"references","requests":[{"source":"workouts","heading":"AE-1"}]}`; setup uses `references`. Batch at most six. `protocol: B` and unique workout IDs
such as `AE-1` are supported; dossier headings must be exact. On failure use the
returned candidates, never guess headings. No bodies means not reviewed. Honor
the token ceiling and hard call limits, including discovery and skill reads.
Five model calls/ten tools are checkpoints, not stops; finish necessary validation
and saving, omitting optional work and duplicate reads. Reserve a final
response; never bypass a blocked tool using shell, retries or delegation. After
an uncertain write, recover its receipt before retrying.

## Sources and coaching safeguards

- Every quoted training metric must come from a fresh JSON read in this response.
  Read `latest.json.data_overview` first, or use the fresh bounded task packet.
  History, conversation and memory are not current metrics. Use computed
  CTL/ATL/TSB/ACWR/RI/zones as supplied, not invented recalculations. Missing,
  stale, partial or contradictory evidence stays explicitly unknown.
- The official dossier supplies stable athlete facts; intake is the versioned,
  attributed source for reported goals, experience, equipment, preferences and
  dated availability/recovery constraints. Check authority, observation/validity
  dates, review flags and conflicts. Clarify contradictions; do not silently
  merge copies or infer current health clearance from old feedback.
- HRV, resting HR and device sleep are optional. Intermittent overnight wear is
  intentional. Missing readings/RI alone do not impose rest, prevent progression
  or require more nights measured. Use current subjective feedback and available
  evidence. Never pressure the athlete to wear a device while sleeping.
- Preserve P0/P1 stops, current readiness and health clarification. A positive
  load/readiness score is not recovery or medical clearance. Current illness or
  injury needs severity/compatibility clarification; an ended calendar marker
  does not prove recovery. Partial health coverage is unknown. Keep a planned
  session as a candidate until compatibility is established; never relax Skip.
- Apply Section 11 B `athlete_specific_v1` and Section 11 C validation: goals,
  event specificity, experience, completed training, tolerability, time and
  constraints determine dose. Availability is a ceiling. State objective,
  progression hypothesis, recovery opportunities, review date and change rules.
  No mandatory weekly hours, 80/20 ratio, demanding-session quota or age-based
  block cycle. Missed sessions create no catch-up debt. Planned phase differs
  from detected phase. Scientific claims follow `COACHING_EVIDENCE.md`.
- For checked power prescriptions call `section11_context`
  `{"operation":"workout_inputs","environment":"indoor","templates":["AE-1","AE-2"]}`
  (choose actual environment/IDs). This reads configured FTP/zone bounds and the
  checked catalog together. Do not page latest.json for absent zone settings or
  invent zones/assessment dates. Load the applicable library template, use
  schema-1 coaching_prescription and compile exact steps. Template constraints,
  uncertain fitness provenance, health and availability still apply. Never strip
  rejected metadata; unsupported/not_checked is not validated.
- Close the loop: prescribe → verify completion and response → adjust. Separate
  adherence, goal attainment and response cost. Record dated feedback, actual
  missed-session causes and maintain/progress/reduce/substitute/reschedule/request
  context decisions with rationale and next observation. Use `prepare` then
  validated `save` for managed reviews; retrieve originals on demand. Quiet
  unchanged reviews and optional wearables retain all health safeguards.
- `event_specific_v1` uses actual event duration/demands and completed training.
  Do not derive taper budgets from CTL or duration from event priority. Durability
  comparison needs compatible context; mechanical kJ are not dietary kcal.
  Strength counts in time/recovery; distinguish addition from replacement and
  retain low evidence certainty. See the event reference on demand.

## Historical blocks and selected evidence

Use `structure_summary`, or `activity_analysis` with an exact history ID.
`compare_blocks` needs two exact IDs and verified zero-based selectors; omit
selectors for eligible choices. Never guess main-work roles. Read status, pairing, coverage, target vs
actual, timestamps/cache age and method limitations. `history_detail` is aggregate
history, not verified segment detail. No raw streams belong in model context.
Compare the same observed windows, power, duration and context. Whole-ride power/NP/HR, WORK labels or thirds cannot replace a verified block.
A descriptive HR delta at different workloads is not a controlled fitness test,
surgery effect or clearance; never normalize HR to another power. Keep shortened
cooldown warnings separate from an otherwise matched main window. Missing or
ineligible windows defer comparison. Do not inspect credentials on failure.

## Writes, delivery and other platforms

Use managed journaled preview/approval/publication for managed workouts, including
changes/removals. Show the exact saved preview and obtain approval before its
publish operation. Preserve immutable prescriptions, history and write receipts;
reconcile uncertain writes. Published never implies completed. Credentials stay
in configured private loaders, never in chat, command arguments or source.
External services and connectors confer only verified capabilities; a connector
alone grants no execution/write authority. Do not claim an unverified save.

Routine Telegram reports are **quick coaching briefs**: lead with decision/result,
then essential session/observation, reason and next action. Use short labelled
lines and sparse ✅/🔧/🛑/❓ emojis. Morning/post 80–120 words, weekly 120–180,
block 150–220, season 180–250; essential safety may extend. No routine dashboards
or repeated caveats. Unresolved health checks lead with Hold. Keep full validated
review records even when the delivered report is brief. Load relevant report
templates on demand; detailed catalogs are opt-in.

For installations without managed tools, use the source/location and manual
capability rules in `SKILL_REFERENCE.md`; `PROJECT_INSTRUCTIONS_AGENTIC.md` and
`PROJECT_INSTRUCTIONS_WEB.md` define platform contracts. Locate official data and
dossier before setup; examples never provide a fallback athlete. Before heartbeat
setup ask for specific values (timezone, riding hours, weather thresholds, notification hours).
Weather is opt-in/on request per configuration: use Section 11's
[point-weather-location](SECTION_11.md#point-weather-location) hierarchy, not
heartbeat location. Match route forecast/cache/departure identity, keep ASSUMED
departure labels, show only matching PNG pages actually read, and preserve source
attribution/freshness. Do not load weather for unrelated planning requests.

Private dossier edits require verified access and the current complete source;
faithful explicit facts use the authorized intake/onboarding exception, other
changes need exact approval. Never replace a whole dossier from an excerpt.
Heartbeat is optional configuration, not an athlete record. Follow its opt-in
schedule; do not create schedules or send messages as a side effect of planning.
Keep private data out of public repositories; provider retention terms apply.
