# Bounded coaching context

Long-term history is available through bounded on-demand monthly, activity and
managed-review reads; see [source, coverage and refresh contract](LONG_TERM_HISTORY.md).

`context_packet.py` normally reads current local files for one task, prints a compact JSON projection and exits. Routine operations make no network/model calls, send no messages, change no calendar, store no athlete data and read no credentials. The configured `workout_inputs` operation also reads owned sport settings (see WORKOUT_INPUTS.md). The explicitly enabled `activity_analysis` operation uses: account-owned API GETs, private credential loading and a bounded local result cache, as documented below. No operation calls a model or mutates remote activities/calendar. It is an alternative **fresh read** of the actual source, not an LLM summary, persistent athlete memory, training algorithm or replacement protocol.

## What is loaded

| Task | Current data | Historical data | Further dependencies |
|---|---|---|---|
| `morning` | Complete readiness/health envelopes, source rollups, relevant load/baseline fields, three calendar dates of wellness/activities, today's planned events | None | Exact protocol/report section if interpreting or changing a rule; route/weather when relevant |
| `weekly` | Current rollups/metrics, matching recent rows, next seven dates of supplied plans | All daily projected rows matching the previous 14 dates, with intersecting weekly bins | Managed revision/review and detailed execution when used; no invented compliance |
| `workout` | Current state, constraints and supplied future plans | Previous 28 dates | Exact selected workout-library template before prescribing; environmental/fueling details when relevant |
| `plan` | Current state, goals/constraints and supplied future plans | Previous 28 dates | Existing managed plan/review, selected workout templates and additional weekly history as needed |
| `post_workout` | Exact activity ID, current health/readiness, matched local interval detail/fetch state | None automatically | Relevant execution windows/streams, report/protocol section; no substitution of session averages for interval work |

All windows use explicit profile/source timezones and the current clock. No row-count prefix or first-N-file-lines query is used. Multiple sessions on the same date are preserved. A matching activity must be unique; duplicate/conflicting interval identities fail. Missing details remain unavailable, not successful execution. Free text is labelled data and supplies no instructions or write authority.

`READ_THIS_FIRST`'s repeated instructions and unrelated JSON blocks are omitted; categorical wellness scales are retained. Full readiness/health objects, observations (when supplied), null values, source dates, source units and start-of-day versus live ACWR stay distinct. No new readiness score or physiological calculation is performed. Missing HRV/RHR alone never becomes a restriction. Packet freshness and source coverage are not health clearance.

Dossier sections are **explicitly selected by exact heading in a private operator profile**. Each selected section is copied whole, including descendants; no biography is guessed or LLM-generated. Routine reports can exclude dated plans, calibration logs, dynamic metrics, API configuration and changelog. Read an omitted relevant section on demand; omission never proves absence. Source SHA256, headings, header/revision text and authority status remain available. A declared official path conflict fails; a legacy dossier without an authority header is labelled `operator_selected_legacy_header_unverified`, not silently promoted to a verified canonical dossier. The helper never edits a dossier or resolves conflicting copies. If that authority uncertainty materially affects advice, clarify it.

## Profile and commands

Create a private `context-primary.json` with these keys (absolute, explicitly verified paths):

```json
{
  "schema_version":1,
  "data_dir":"/home/ATHLETE/training-data",
  "protocol":"/home/ATHLETE/training-data/section11/SECTION_11.md",
  "workout_reference":"/home/ATHLETE/training-data/section11/examples/workout-library/WORKOUT_REFERENCE.md",
  "reports_dir":"/home/ATHLETE/training-data/section11/examples/reports",
  "dossier":"/home/ATHLETE/training-data/DOSSIER.md",
  "dossier_sections":{
    "morning":["2. Coaching and communication preferences","4. Private profile and goals","5. Health, medication and supplements","7. Practical training context and essential equipment"],
    "weekly":["2. Coaching and communication preferences","4. Private profile and goals","5. Health, medication and supplements","7. Practical training context and essential equipment"],
    "workout":["4. Private profile and goals","5. Health, medication and supplements","6. Fueling, hydration and recovery","7. Practical training context and essential equipment"],
    "plan":["2. Coaching and communication preferences","4. Private profile and goals","5. Health, medication and supplements","7. Practical training context and essential equipment"],
    "post_workout":["4. Private profile and goals","5. Health, medication and supplements","6. Fueling, hydration and recovery","7. Practical training context and essential equipment"]
  },
  "timezone":"Europe/Zurich",
  "source_timezone":"Europe/Zurich"
}
```

These headings fit the current dossier template; older dossiers need their **actual** headings, not these names. Do not use the public template or fictional JSON examples as athlete data. Configuration selects sources; it does not verify their truth. A missing dossier is labelled unavailable while current safety data can still be reported. A missing selected heading fails rather than quietly dropping a constraint after a source edit.

```bash
python3 context_packet.py --profile /private/context-primary.json build --task morning
python3 context_packet.py --profile /private/context-primary.json build --task weekly
python3 context_packet.py --profile /private/context-primary.json build --task post_workout --activity-id EXACT_ID
python3 context_packet.py --profile /private/context-primary.json history --start 2026-10-05 --end 2026-10-18
python3 context_packet.py --profile /private/context-primary.json history --tier weekly --start 2026-07-01 --end 2026-10-18
python3 context_packet.py --profile /private/context-primary.json headings --source protocol
python3 context_packet.py --profile /private/context-primary.json section --source protocol --heading 'Health Context (v11.61)'
python3 context_packet.py --profile /private/context-primary.json headings --source workouts
python3 context_packet.py --profile /private/context-primary.json section --source workouts --heading EXACT_TEMPLATE_HEADING
python3 context_packet.py --profile /private/context-primary.json section --source dossier --heading EXACT_HEADING
```

Source SHA256s and section headings/line numbers identify the current read; `profile_sha256` binds packet selection. A protocol pointer with `loaded:false` does not claim that the protocol was read. `headings` skips bodies, so browsing no longer starts with hundreds of changelog lines. `section` copies an exact ATX Markdown section and its descendants, ignoring fenced code headings; ambiguous/missing titles fail. For report sections use `--source report --task morning|weekly|post_workout`.

## Completeness and failure handling

- Daily queries allow at most 42 dates; weekly queries allow 182. They return **all matching source rows** (daily fields explicitly projected, weekly bins retained whole). Missing/invalid/duplicate dates and boundary bins are visible. `coverage_complete` concerns row/date presence, not measurement completeness, endpoint reliability or a fully observed current day/week. Null HRV is a missing measurement, not a missing training date.
- History retains its own `generated_at` and data range. Newer latest data does not refresh history. Source rollups retain their original periods: never relabel a seven-day summary as a 14/28-day total or double count overlapping history/latest data. A missing historical day never becomes zero training. Week bins are Monday-based producer bins, not prorated daily observations.
- Current snapshot freshness requires a valid timestamp, the current local calendar date and age <=24 hours, with up to five minutes future clock tolerance. This is an operational source-age check, not a physiological threshold. Naive producer timestamps use **explicit `source_timezone`**; ambiguous/nonexistent DST times are unknown. Unknown/stale/future snapshots request refresh before new prescriptions; current subjective feedback remains a separate decision input.
- Each source read is bounded at 8 MB. All output, including sections, is bounded at **49,152 UTF-8 bytes**. Over-budget output fails with a fixed error code; it never quietly clips a row, section, health decision or constraint. Narrow an explicit history query, retrieve an exact section, or use morning core plus targeted dependencies. Do not fall back to raw whole-file dumps or fictional examples. Individual source files are read fresh but not in a cross-file transaction; retain material generation-time conflicts.
- A successful JSON object ends with `packet_complete:true`. Require valid complete JSON and this marker from the tool. This indicates transport/projection completeness only, not complete history or permission to train. Tool-side truncation, a missing marker or a nonzero exit is an unusable packet. The deployed OpenClaw exec library's normal output cap is above the packet limit; other installations must verify their own tool/harness caps. The helper is not an OS sandbox and does not restrict the surrounding agent's other tools.
- Errors contain fixed codes, never private file text. Packets contain private athlete information **by design** for the configured coach; do not put them in this repository, telemetry, public logs or messages to other recipients. Production prompts use the builder's stdout directly, not a stale saved packet. Existing credential-output protection still applies.

## Primary integration

Step 4 supersedes the scheduled-message/post-reporter invocation below with the [bounded report supervisor](EXECUTION_RELIABILITY.md). Interactive source selection and the packet contract stay the same. The installed `section11_context` tool accepts the same operations as typed JSON (`operation`, `task`, `source`, `heading`, `start`, `end`, `tier`, `activity_id`), with no arbitrary paths or shell. Prefer that tool where available. Scheduled reports receive the fresh packet directly and use the tool for additional exact dependencies.

The primary morning/weekly job messages call the installed builder once, use the task-specific packet and request additional exact dependencies only when they affect the decision. The primary workspace directs interactive workout/plan tasks to the same fresh entry point. The primary external post-workout reporter's **prompt only** calls the builder with its observed activity ID; existing detection, state, retry, model and delivery behavior remain outside this change. In particular, its historical CLI-exit-versus-delivery ambiguity is still Step 4 work.

On the current server, the reporter entry point was a symlink into the old checkout. Its original source is preserved; the entry point is redirected to a private runtime copy containing the prompt change. AST comparison verified that only prompt construction and its standard-library quoting import changed, and relocation checks verified there were no local imports or `__file__` dependencies. The original symlink target is recorded in private rollback state. Future installation/cleanup must account for this explicit runtime override.

Private installation/rollback records preserve the old messages, workspace text and reporter script. Job schedules, destinations, model choices and reasoning stay unchanged. The secondary profile is untouched. No packet cache, transcript rewrite, growing summary injected into every turn, full coaching release installation or automatic calendar publication is added.

OpenClaw still stores ordinary tool results in its private conversation transcripts. The builder does not remove earlier packets from a long conversation or replace the runtime's history/compaction behavior. Context retention/pruning remains later work; the packet bound is not a guarantee that the entire model context fits its limit.

Routine morning reports target one context tool call followed by the answer (normally two model responses). This is a target, not an enforced loop limit or measured saving. Step 2 telemetry can measure the next real runs; controlled quality evaluation is still required before claiming that fewer tokens/calls preserve quality. Tests validate deterministic selection, safety/data preservation and failure handling, not live model judgment.

When full intake makes a task packet too large, the builder explicitly defers the
daily/weekly history rows to a separate dated `history` read, retaining complete
intake and readiness/health envelopes. The packet labels deferred counts, the
required window and an evidence digest; omitted rows do not imply absent training
or complete coverage. Retrieve the stated history before a prescription or a
judgment that depends on it. The original byte limit and exact history reader
remain unchanged; oversized remaining content still fails explicitly.

### Native tool transport budget

The optional private profile key `tool_packet_bytes` (8,192–49,152 bytes) caps CLI
responses before OpenClaw can silently trim them. Primary uses 30,000 bytes under
the full 1,050,000-token Sol working context. The 30,000-byte per-result
bound remains separate from conversation capacity. A build can
explicitly defer bulky history, selected dossier sections and intake to their
existing exact readers. `intake` is an additional read-only operation returning
the complete account-bound onboarding revision; it accepts no model-selected path.
Read required_retrieval before using deferred facts. Full readiness/health envelopes
remain intact; an oversized remaining response fails without a partial packet.
The internal Python builder/report supervisor continues to receive its complete
source packet. The coaching bridge also honors the smaller output cap: receipts
are never shortened to fit it; uncertain persistence still requires a recovery read.

If a build still exceeds the transport budget, recent activities are explicitly
deferred to `activities` with the same task (and activity_id for post_workout).
The reader returns the exact fresh selected rows and source hashes. Retrieve them
before interpreting completion, and refresh core health/readiness if source
identity changed between reads. Core readiness and health are never dropped.

### Batched exact references and primary exchange budget

Use `section11_context` operation `references` with `requests` containing one to six
`{source, heading}` objects (report references may also specify `task`). Read known
relevant protocol/template/dossier sections together. Duplicate references are read
once; each source is read once and retains its hash. Missing, ambiguous or oversized
batches fail whole; split oversized batches. Never substitute references for fresh
health, intake, plan state or calendar approval.

Primary-only `exchangeBudget` defaults: 6 observed model attempts (one reserved for
final response), 10 admitted tools, 300,000 estimated cumulative tokens. It blocks
new tools at the first limit, including parallel admissions; admitted writes finish
and their receipts are never edited. Report pending work and wait for another user
exchange rather than retrying blocked calls. Runs, not sessions, own counters.

**Scope:** OpenClaw 2026.10.6 exposes model hooks as best-effort notifications and
usage as an end-of-attempt aggregate. This is a tool-admission guard, not a hard
provider-call/token or ChatGPT-quota cap. Token admission uses UTF-8 bytes / 3 plus
16,384 output allowance per observed request, explicitly an estimate. Actual
input/output/cache usage is logged separately as `section11_exchange_attempt` in
private gateway logs; cache is not added again to reported `total`. No quota or
currency conversion is assumed. Retries/internal compaction may escape observation;
a provider-level cancellable admission API is required for a strict cost ceiling.
No prompts, athlete text, destinations or receipts are included in these metrics.
Report-only agents retain their existing read-only six-call policy.

### Quiet bounded-history maintenance

Primary-only `quietBoundedContextNotices:true` cancels the exact standalone native
Telegram bounded-context notice at outgoing delivery. OpenClaw 2026.10.6 forces
that phase despite `compaction.notifyUser:false`; that flag alone is insufficient.
The filter preserves health warnings, errors, replies with other text and media.
Quiet maintenance never means complete conversational recall: recover current
intake, managed plan and health from the normal fresh readers and ask for genuinely
missing evidence before advice. Canonical history and write receipts remain saved.

## Opt-in historical block analysis

The primary integration exposes `section11_context` operation `activity_analysis`
with one `activity_id` matching `i` plus digits. It is disabled unless the private
context profile has an absolute `activity_analysis_profile` path. Ordinary local
context reads remain network-free; this one operation performs bounded GETs and
writes only its own private result cache. No calendar or activity mutations exist.

The owned mode-0600 analysis profile has exactly:

```json
{"schema_version":1,"install_root":"/absolute/source","data_dir":"/private/data","state_dir":"/private/historical-analysis","facts_store":"/private/history/facts.sqlite3","athlete_id":"i123456"}
```

Data directory, account and facts store must match the parent context profile.
The activity must already appear in that account's durable facts or latest mirror.
Credentials use pull.py's explicit private directory loader, never model arguments,
working-directory discovery or another account's environment. API hosts/paths and
stream types are fixed; no arbitrary URLs, paths, dates or code are accepted.

On a miss, at most four GETs retrieve activity, resolved paired event (when present),
intervals and time/power/HR/cadence streams. There are no automatic retries or
redirects. Responses are bounded at 16 MB each / 32 MB total; stream arrays at
100,000 samples each. Fetching has a 48-second budget with short connection/read
timeouts; the native subprocess has a 60-second bound for this operation only.
All other context calls retain 15 seconds and exchange admission limits remain.

The existing sync analyzer runs directly, outside the normal detail-retention
gate. Returned output is at most 8 KiB, with actual elapsed windows, targets,
measurements, coverage and method/status/issues. No raw streams or source prose
enter the model context. These results do not supply medical clearance or formal
adherence. Missing HR stays null. Missing/contradictory pairing stays explicit;
unpaired intervals/thirds are descriptive, not prescribed main-work roles.

A private atomic result cache holds at most 64 activities. It stores no credentials
or raw streams. Every hit rechecks activity/event/interval metadata; fingerprints
also include analyzer/helper code. Changed metadata or six-hour expiry requires
new streams. Computation and revalidation times, stream reuse, source/stream hashes
and API-call counts are returned. This is bounded stream reuse, not a guarantee
against an upstream stream change with unchanged metadata. Failed revalidation
never substitutes an old cached success. A nonblocking lock prevents duplicate
fetches; busy/HTTP/authentication/rate-limit/timeout errors return explicit states.
An unavailable analysis never proves that historical workout data is absent.

Scheduled reports still do not load historical analysis routinely. Retrieve exact
old detail only when its block comparison is needed. This is data retrieval and
analysis; automatic similar-session selection/comparison is a separate layer.

## Explicit two-block comparison

`section11_context` operation `compare_blocks` takes current `activity_id` and
`reference_activity_id`, plus optional integer `step_index` and
`reference_step_index` (zero-based, 0–31). It shares the historical-analysis
opt-in/account binding. Both IDs must be distinct primary-account activities.
Only these typed arguments are accepted: no URLs, private paths, credentials,
thresholds or user-supplied measurement snapshots. With selectors omitted it
returns eligible constant-target windows for explicit selection, never an
inferred main set or an automatic similarity ranking. No eligible choice is an
explicit failure. Ramp, range-target, repeated-set, unmeasured and unpaired
windows cannot be silently substituted for constant-target continuous steps.

It calls the existing analysis helper at most twice, with at most eight API GETs
and zero model/remote-write calls. Source metadata is revalidated and stream
caching follows the six-hour policy above. Transport allows at most 120 seconds
for this operation only; individual analysis fetch budgets remain 48 seconds.
All other tool/exchange limits remain unchanged. At most 8 KiB is returned,
containing the selected windows rather than full rides or raw streams.

Power coverage must be at least 95%; HR/cadence deltas additionally require
positive measurements with at least 95% coverage in both windows. These are
engineering quality gates, not scientific thresholds. Actual window length and
prescribed duration are kept separate; transition trimming is not formal failure
to complete. A shortened cooldown/whole-session `partly_followed` warning is
retained but does not erase a valid selected main-window comparison. Clipped or
off-target selected windows remain explicitly flagged. Analyzer versions/code
must match; ambiguous pairing or invalid timing prevents numeric comparison.

Every delta is **current minus reference**. `workload_match` is `different` or
`same_at_reported_precision`, determined only by equality of recorded mean power
and measured duration. Neither is a claim about identical traces or a controlled
experiment. The result is always `descriptive_only`: show power, duration and HR
for both sides, actual/planned mismatches, differences in lead-in duration,
recording device/environment/FTP setting, missing context and source provenance.
A recording-device difference does not identify the power sensor or trainer app.
Unknown conditions stay unknown; do not require optional wearable data to compare.
Do not normalize HR to a common wattage or infer fitness, surgery effects or
medical clearance from the difference. The LLM may explain the observed result
briefly but cannot upgrade it to an exact matched or causal comparison. Further
similar-session search and physiological modeling are outside this operation.

## Reference identifiers and actionable errors

Exact titles take precedence. Protocol `B`, `11B` and `11 B` resolve only to
`11 B. AI Training Plan Protocol`. Workout IDs such as `AE-1`, `AE-4`, `TH-2`
and `WU-STD` resolve only to a unique heading beginning with that ID plus colon;
identifiers are case-insensitive. These are documented identifiers, not fuzzy
body searches. Dossier headings remain exact. Returned `resolved_heading` and
source provenance make alias resolution visible. Missing/ambiguous requests fail
the whole batch; no successful reference bodies are returned alongside failures.

The bounded native transport preserves sanitized backend error codes and bounded
candidate-heading metadata, marked `isError`, `context_complete:false` and
`packet_complete:false`. It discards arbitrary output fields and still rejects
malformed, oversize, incomplete or timed-out results. Use candidates to correct
a request without another discovery round; do not treat errors as source evidence.
Budgets and full source/health/publication validation remain unchanged.

Planning packets include save-first guidance. Explicit goal/schedule/setup updates
must be saved through validated intake before optional history or references,
including when a managed plan already exists. The complete saved snapshot retains
unchanged entries and source dates. Recovered state and receipts distinguish
saved athlete intent from a plan still pending construction or publication.

Planning packets prioritize full intake and readiness/health within the existing
wire cap. When needed they explicitly defer detailed capability, raw older wellness,
companion inventory, dossier sections and activity rows; none is treated as absent.
Capability-dependent advice needs its deferred read. Current three-calendar-day
wellness rows retain full fields; full readiness/health envelopes are unchanged.
Use `section11_coaching planning_setup` to combine an authorized intake update
(or null for unchanged saved intake), compact managed-plan state, bounded long-term
history and reference reads in one call. Full prior plan prose/evidence is
explicitly deferred, with a state-read pointer; all historical prescription
references and selected goal/feasibility fields remain. Saving happens first and its receipt survives failed/deferred reads.
This reduces sequential tool/model rounds without loosening exchange budgets.


## Whole-skill read and planning entry repair — 5 November 2026

The next primary Telegram continuation failed before using the bundled workflow:
OpenClaw refused the 35,873-byte entry skill as an incomplete whole-document read.
The coach then described the context tool and fetched AE-1 and protocol B in
separate model turns; its state read was blocked at the fifth model attempt.
This was a skill-delivery/control-flow failure, not missing saved intake.

The entry is now under 12 KiB/200 lines with the exact Tool Search call shapes.
Platform/setup/manual detail remains in SKILL_REFERENCE.md, installed alongside
the entry and checked by source parity. With unchanged intake, request build(plan),
planning_setup(null, reference batch) and any needed propose-schema description in
one model turn. Changed intake still requires its saved snapshot first. Limits,
models and source/health/publication checks are unchanged. The native regression
checks the actual installed whole-skill reader and broker/nested-call budget path.

One isolated real Sol-medium continuation recovered saved intent, current data and
managed state without budget blocks (four observed model attempts). It requested
a current shoulder/recovery update rather than claiming a plan was saved. No
production plan, intake or calendar was changed. This verifies the repaired entry
and retrieval path, not full future coaching quality or a completed six-week plan.


## Planning continuation follow-up — 5 November 2026

A subsequent real Telegram turn loaded the compact skill but still failed:
seven logical operations expanded to dispatcher plus implementation admissions;
three parallel wrapper calls filled the ten-slot guard before any child could
run. The feedback attempt was among those refused. The old model boundary also
refused work on attempt five despite reserving attempt six for final output.
Known native wrappers now count at their actual operation only, the boundary is
corrected, and token estimates exclude transcript-only duplicate metadata.
Feedback can be saved with planning_setup before optional reads, with a separate
receipt and current-feedback recovery readback. No numeric budget increase or
model/account/calendar change is involved. The full native regression includes
the failure branch and a fifth-attempt proposal, rather than only an ideal path.


Verification: 1,384 server tests passed, including installed schema conversion
and native whole-skill/context-pressure checks. An actual Sol-generated proposal
was reviewed and passed through the installed core Tool Search dispatcher and
hooked coaching implementation with a simulated fifth-attempt budget state and
seven earlier logical operations. Save was admitted as operation eight, then independently read
back from the isolated store. This is a native persistence test, not a claim that
every model turn automatically produces valid arguments. Explicit feedback enums,
valid activities(task:plan) examples and required plan weeks are now stated in the
entry skill; malformed arguments remain rejected. The primary requested block
and previously blocked feedback were recovered with private preimage/receipt
backups, immutable history retained and no calendar operations. Exact sessions
remain dependent on actual available windows and review; no unknown time was
encoded as zero and no training/medical clearance was invented.


## Normal planning must fit the work budget — 5 November 2026

The next primary request hit the ten-operation ceiling while retrieving mandatory
workout-validation inputs. Its saved intake update succeeded; its requested plan
revision had not been attempted. A fixed ten-tool cutoff is inadequate for a
complete multi-session revision. The default and generated primary configuration
now use 32 operations/10 model attempts (final response reserved), retain the
300,000 estimated-token guard, and treat ten tools/five calls as nonblocking
efficiency checkpoints. Provider calls in progress cannot be hard-capped by
public hooks. Trace/attempt-aware IDs prevent compaction attempts being deduped
as if they were the same model call.

Both plugins register their owned tools as direct-only. The installed native
catalog check verifies visible schemas with no Tool Search indirection; new typed
reads therefore match the existing read-only cache pruning rule. Canonical
history and write/mixed receipts are untouched.

Actual planning tests also found missing configured power-zone bounds: current
JSON contains FTP settings but not those bounds. `workout_inputs` returns one
account-bound sport-settings GET plus the verified selected catalog. It retains
unknown assessment provenance and supplies no default zone percentages. It also
explains continuous main-step role work, which was an actual rejected draft
metadata error. Known local transactional validation errors now return static
codes/actionable hints and plan_saved:false; arbitrary exceptions remain private
and uncertain acknowledgements still require recovery. Numeric validation and
calendar approval are unchanged.

The actual Sol-produced sixteen-session draft was validated with only a technical
continuous-role correction, then saved/recovered in an isolated store. Its full
state exceeded the existing 30,000-byte packet cap. State encoding now retains
the entire plan and publication/prescription summaries, explicitly deferring
independently retrievable intake when necessary; no arrays/receipts are cut.
The typed readback fits the original cap. All private test and preimage records
stay outside this repository. No calendar publication was invoked.


Final verification: 1,394 server tests passed; local suite passed with only
installed-runtime checks skipped. Native SDK tests verify direct tool placement,
strict-schema preservation, pruning/receipt protection and hard-budget vetoes.
The configured-settings GET was verified on the primary account. The actual
Sol draft reached propose without a work-budget block. Its continuous-role error
was reproduced as a known, rolled-back validation failure; the same draft with
only that metadata corrected saved all sixteen checked prescriptions and passed
a fresh typed state read (about 23 KiB), retaining the original 30 KiB cap. No
model judgment, dose, watts or health restriction was changed by the correction.

## Compaction model identity — 5 November 2026

The primary Telegram session subsequently failed both automatic and manual
compaction with an unknown Luna model. Luna was available in the installed
account catalog; the failure was not a missing sign-in or a tool-budget veto.
OpenClaw 2026.10.6's compaction override parser splits `provider/model` without
removing an `@profile` suffix, so it tried to resolve that suffix as part of the
literal model ID. The earlier configuration generator incorrectly reused the
primary model's credential-pinned spelling for this separate override.

`configure_primary_models` now sets compaction to `openai/gpt-6-luna`, at low
reasoning, while retaining the primary Sol-medium account pin. Same-provider
compaction inherits the active authentication profile. An installed-runtime
regression checks that exact resolver behavior and the generated configuration;
unit checks alone previously accepted the invalid suffixed spelling. This is a
configuration workaround, with no edits to installed OpenClaw package files.
No changes to model allowances, keyword memory, budgets or calendar approval are
needed. A real native session-compaction check should accompany deployment;
replaying a failed coaching request is unnecessary to test summarization.

The primary native `sessions compact` retry succeeded using Luna: reported
active tokens fell from 87,008 to 9,873. All 2,134 original canonical transcript
events remained byte-identical; only compaction events were appended. The plan,
intake and feedback stores and secondary configuration were unchanged. Fresh
typed state retrieval returned the saved sixteen-session revision and all
checked prescriptions. The summary reflects conversation evidence, so the usual
fresh-state recovery rule remains essential for changes saved outside Telegram.
No coaching tools, calendar writes or Telegram deliveries were replayed.


## Full primary context — 5 November 2026

The operator explicitly chooses the full supported Sol window. The previous
131,072-token working cap, 256 KiB active-transcript compaction trigger and
cache-TTL pruning are superseded: generated primary settings use 1,050,000
tokens, maxActiveTranscriptBytes:0 and contextPruning.mode:off. The window covers
the whole prompt and output reservation, not just Telegram conversation text.
Native pressure checks and Luna safeguard compaction remain for actual capacity
pressure; no near-limit provider acceptance is inferred from catalog metadata.

The competing cumulative estimated-token veto is explicitly disabled for the
primary (estimatedTokens:0), while estimates/actual usage telemetry, 32 tool
operations and ten model attempts remain. Plugin defaults for other accounts
remain unchanged. Fresh source, health and exact calendar approval rules remain.
Large capacity does not require loading irrelevant sources or restoring old
compacted turns, and does not provide indefinite full transcript retention in
every future prompt. Original transcripts and saved coaching sources remain.

Installed native pressure tests accept a synthetic prompt above the former 131k
limit, resolve 1,050,000 tokens from the generated configuration and still reject
an oversized prompt. They verify disabled TTL settings, protected receipt/history
behavior and independent call guards. One isolated no-tool Sol-medium provider
smoke request succeeded with the proposed configuration. It was deliberately
small: maximum-size acceptance and workload quota effects are not measured by
that request. No message, training save or calendar write was involved.
