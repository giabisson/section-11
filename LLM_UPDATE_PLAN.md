# LLM efficiency and reliability implementation

Based on the read-only repository and home-server review of 22 October 2026. Implement in order and report after each step. Cost reductions are expected benefits to measure, not established savings.

| Step | Scope | Status |
|---|---|---|
| 1 | Repair profile-specific Telegram delivery, protect credentials, provide hidden-input replacement and record explicit installation paths | Complete for primary; secondary rotation deferred by user |
| 2 | Per-workflow telemetry and repeatable coaching evaluations | Complete for primary; collector active and evaluation harness verified |
| 3 | Bounded task-specific context and date-filtered complete history | Complete for primary; packet entry points installed and verified |
| 4 | Execution deadlines, restricted tools and outcome-based retries/deduplication | Complete for primary; supervisor and retry timer active |
| 5 | Measured model/reasoning routing, provider-specific caching and durable context | Complete for primary; cache/context policy active, model promotion held pending reviewed validation |

## Current primary status — 23 October 2026

All five implementation steps, long-term history and managed plan/review integration
are deployed. The full suite passed **1,306 tests locally and on home-server**;
installed plugins, skill discovery, report dry runs and source/runtime parity passed.
The dated sections below preserve earlier states and test totals; the final managed
reviews section and [deployment record](examples/agentic/COACHING_DEPLOYMENT.md)
supersede their earlier statements that the coaching release was not installed.

The subsequently authorized fresh-start cutover is complete. The original
104-file archive, a current-context backup, prior conversations and training history
are preserved; active personal context and derived memory were reset. Primary
Telegram onboarding is available; the subsequently saved intake and active managed
plan are preserved. Real coaching effectiveness still requires review of current
answers and athlete response. Primary coaching is fixed to Sol medium, with Luna
for utility work; benchmark promotion cannot override this operator policy. Reported
experiment estimates are not verified billing or production savings. Secondary-account
migration and key rotation remain deferred.

## Step 1

The [runtime safety integration](examples/agentic/openclaw/RUNTIME_SAFETY.md) adds a pre-model credential-output guard, direct credential-file access checks, a read-only Telegram routing audit and a hidden-input key replacement command. Developer tests cover blocked reads, encoded credentials, private-file requirements, failed-source behavior, preserved delivery metadata, cross-consumer replacement and separate generation/delivery status.

The runtime changes are limited to this safety integration and delivery repair. The new coaching release is not installed by this step. Existing profile identities, source checkouts, data directories, schedules and model choices remain explicit; no loose training plans are imported. Installation paths and rollback material belong in private server state, not this repository.

Known limits: no key revocation through this tool, no removal of historical exposure or provider-held copies, and no OS sandbox supplied by a redaction hook. Account-side regeneration and execution hardening remain necessary. Never call the credential rotation complete solely because output is redacted.

### Verification on 22 October 2026

- Both proposed OpenClaw configurations passed the installed validator. The plugin loaded through the installed SDK and hot-reloaded in both running profiles without a Gateway restart. Runtime inspection confirmed the tool, transcript and outbound hooks; the declared pre-model middleware contract registered without error.
- Private process tests using the actual configured credential sources verified filtering, blocked credential-file reads and allowed ordinary Section 11 tool commands without placing a credential in a model request or transcript.
- Both existing report jobs in each profile now use an allowlisted, reachable private Telegram destination and explicit required delivery. Payloads, schedules, timezones and models were compared before/after and preserved. Historical failed-delivery records were retained.
- With explicit user authorization, one temporary scheduled command per profile delivered a short test message. Both scheduler states recorded `ok`, `delivered` and `lastDelivered: true`. These command payloads made zero model calls or calendar writes. Temporary test jobs were removed after verification.
- The primary Fitbit consumer's credential file was restricted to mode 0600. The hidden-input helper updates that consumer and the primary Intervals configuration together, with per-file atomic replacement and explicit partial-failure limits. Backups and installation-path records remain in private server state.
- All **1,129** Python-discovered developer tests passed locally (37.097 seconds) and on the actual server (70.049 seconds), including nine runtime-safety tests and the wrapper executing ten Node credential-boundary cases. After the verification-header/diagnostics fix, all twelve focused runtime-safety tests passed locally and on the server. The 169-file distribution manifest and saved artifact audit were regenerated.
- Independent read-only checks after hidden terminal replacement verified the new primary key against the configured athlete, confirmed the previously exposed key now receives HTTP 401, and confirmed the Fitbit consumer contains the new key and no longer contains the old key. Private process checks also confirmed the credential guard filters the new credential, blocks direct credential-file reads and allows ordinary tool commands without model calls.

Primary credential replacement and verification are complete. This verifies read-only authentication and consumer configuration; it does not establish that a subsequent scheduled Intervals or Fitbit sync has completed successfully. Secondary credential exposure remains unresolved and outside the current implementation scope, as requested by the user. The broader coaching release remains uninstalled. No model selection or reasoning/caching policy changed in this step.

Further efficiency and reliability implementation will focus on the primary account until the user expands the scope.

Verification uses an explicit application User-Agent: the default Python header was observed receiving HTTP 403 before the authentication check. The helper also emits fixed input/API error codes without provider bodies or credentials; HTTP 403 alone is not treated as proof of revocation.

## Step 2

[Telemetry and evaluation operation](examples/agentic/openclaw/TELEMETRY_AND_EVALS.md) documents the read-only collector, primary-only timer and offline coaching evaluation harness. Telemetry is collected outside the agent loop; no report prompt, model/reasoning choice or existing coaching schedule changes. Output contains only operational metadata/counters, never raw conversations, tool arguments/results or athlete data. The collector separates observed generation, conservative receipt association and delivery evidence. Unknown/zero cost remains unknown rather than free; utility/internal calls and absent compacted history are explicit coverage limits.

The twelve synthetic evaluation scenarios have reference answers and failing controls. Automated factual/dose/decision checks require independent, answer-hash-bound human review before any quality pass. Self-test success is evidence about the harness, not a baseline measurement of the current model. Future model comparisons must retain original answers, context/model/reasoning provenance and repeat-run results. Live answers remain ungraded until that experiment is performed.

### Verification on 22 October 2026

- Installed the primary-only collector and offline evaluation artifacts in private runtime storage. The systemd user units passed validation; the 15-minute timer is enabled/active and its first service run finished with `Result=success` and exit 0. OpenClaw configuration was hash-compared before/after and unchanged. The secondary profile was not installed or modified by this step.
- Saved a private baseline and installation/hashes record. The initial rolling 14-day projection contained 193 active events, 19 observed model/tool turns and 16 report scheduler receipts. The service collector took 392 ms in that run; this is collector overhead, not model latency. Morning reports had a median two observed model responses and 14.3125 seconds observed complete wall time; weekly reviews had two and 11.8185 seconds. Window/coverage differences mean these are not directly comparable to the earlier calendar-date audit or evidence of savings.
- Historical report receipt delivery stayed unknown except where matching latest-job state supplied evidence. Positive completion of the Python/CLI process was not converted to delivery success. The initial baseline supplied no complete positive cost totals; cost remains unknown, not zero.
- The snapshot scan found no exact configured credential values; all output files were private mode 0600. Only allowlisted metadata/counters are serialized. Delivery mirrors are excluded from both response counts and timing; storage-details truncation is separate from tool-text truncation.
- All **1,161 tests passed locally** (38.932 seconds) and **on home-server** (72.561 seconds), including 19 telemetry and ten evaluation tests. The installed evaluation self-test also accepted all 12 reference answers and rejected all 12 failing controls. These are offline/synthetic checks; no live model-quality score was claimed.
- The 175-file distribution manifest and saved artifact audit were regenerated. This step made no model calls, Telegram sends or athlete calendar writes. The new coaching release remains uninstalled; prompt/context changes start with Step 3.

## Step 3

[Bounded task context](examples/agentic/openclaw/TASK_CONTEXT.md) adds fresh, deterministic packets for morning, weekly, workout, plan and exact-ID post-workout work. It preserves full readiness/health decisions, optional-wearable missingness, relevant field/date/unit provenance, source rollup periods and explicit history gaps. Dossier selections copy exact stable sections; old dated schedules, dynamic metrics and changelogs are not silently reused as current facts. Legacy dossier authority is labelled unverified rather than invented.

Daily/weekly history is selected by date, with every matching projected row and explicit gap/duplicate/boundary flags. Exact Markdown heading retrieval avoids loading protocol changelogs or the whole workout library. Over-budget sources/output fail without a truncated usable fragment; complete JSON ends in a transport marker distinct from coverage/health clearance. Source data remains private; packets are generated on demand rather than cached or added to persistent model memory.

Primary deployment updates the two report messages, workspace entry-point instructions and only the external post-workout reporter's prompt construction. It preserves schedules/delivery/model/reasoning settings and leaves the secondary account and broader coaching release untouched. One context tool call plus final answer is the routine morning target, not an enforced loop limit or a demonstrated savings/quality result.

Telemetry now detects structured tool truncation even when the result text has no marker (`truncation_policy_version:2`). The original Step 2 baseline remains preserved; its older detector undercounted that signal, so cross-version truncation comparisons require recollection under the same detector.

### Verification on 22 October 2026

- All **1,187 tests passed locally** (37.713 seconds) and **on home-server** (72.853 seconds), including 25 context tests and the additional structured-truncation regression case. The distribution manifest contains 177 files; the saved artifact audit was regenerated.
- Five task packets passed through the installed OpenClaw exec library and live credential-output guard without truncation, with successful exit and valid final transport markers. These were direct tool-library checks with zero model calls, not a simulated claim about a real model's subsequent behavior. Installed-source hashes match the tested sources.
- Independent installed-CLI checks passed for all five tasks, recent daily history, longitudinal weekly history, exact health/readiness protocol sections and workout heading discovery. In that read, the morning packet was about 20 KB and weekly about 34 KB; the source latest JSON alone was about 50 KB. These are measured UTF-8 payload sizes, not token/cost savings or a controlled quality comparison.
- The recent daily query returned every matching source row (ten rows for 9–22 October) and correctly flagged the four dates absent from the history snapshot ending 18 October. Newer current data retained its own source/period. No missing date was converted to zero training or falsely complete history.
- Primary report messages were edited through OpenClaw's official CLI. Job schedules, delivery, identities, model/reasoning payload options and global OpenClaw configuration were compared and preserved. The primary workspace uses the same reader for interactive workout/plan tasks.
- The reporter entry point was a symlink into an untracked script in the old checkout. The original source is unchanged; the symlink now selects a private runtime override. AST comparison verified only prompt construction and its quoting import changed. No local-import/`__file__` relocation dependencies were present. Detection/state/retry/delivery logic remains unchanged and its known delivery ambiguity belongs to Step 4. Private backups record the original source/link and old job/workspace definitions.
- Corrected telemetry is active; the original Step 2 baseline hash is unchanged and a separate pre-change baseline using detector version 2 is saved. Installed hashes, original reporter preservation and collector success were independently verified. Secondary runtime files/jobs were not modified by this step.
- This step made no model calls, Telegram sends or athlete calendar writes. The next actual report runs will establish model response counts/usage and reveal any additional retrieval. Long-chat retention, execution hardening and model tuning remain later steps; the broader coaching release is still uninstalled. No live model-quality score or operating-cost reduction is claimed.

## Step 4

[Bounded report execution](examples/agentic/openclaw/EXECUTION_RELIABILITY.md) separates autonomous generation from delivery. Morning/weekly schedules now run an explicit supervisor command; the post-workout entry point hands off to a bounded user service. The supervisor builds fresh context before the LLM, skips unchanged delivered reports, imports legacy reported IDs, caches successful text before delivery and retries only known failures within fixed attempt/backoff/expiry limits. Uncertain generation/sends require explicit operator reconciliation. Evidence is reread before sending, including after generation; changed/stale recommendations are held. Missing wearables alone remain valid missing data, not a freshness failure.

Headless report generation uses the existing primary main model/reasoning/provider configuration, a current report template and the task packet, without reusing the long interactive chat or its bootstrap. Only the typed `section11_context` reader is allowed, with a six-call cap, fixed argv, 15-second reads and complete bounded JSON. Report Code Mode and Tool Search wrappers are disabled so the actual tool name reaches the policy hook. Ordinary interactive coaching retains its coding tools and source-selection policy; global primary deadlines are now explicit (agent 600 seconds, shell 90 seconds), with loop detection enabled. These restrictions are not an OS sandbox or a precise dollar/request budget.

The supervisor sends one plain-text Telegram message only to the verified existing primary bot/private destination, with a matching acknowledgement required for delivery success. Known delivery failures reuse cached text rather than re-run the LLM; transport ambiguity does not trigger an automatic resend. Scheduler fallback delivery is disabled to prevent duplicates/status JSON delivery. Routing audits understand the explicit supervisor profile; its ledger is the delivery authority, not the scheduler's expected `not-requested` status. Headless metric envelopes are collected separately from Gateway transcripts; unknown cost remains unknown.

### Verification

- All **1,226 Python-discovered tests passed locally and on home-server**, including 36 supervisor cases, the Node context-tool wrapper, supervisor telemetry and explicit routing-owner checks. Tests cover source changes during generation, stale cached advice, attempt/time/output limits, crash/unknown states, Telegram rejections versus lost acknowledgements, cached retries, queues, expiry and private diagnostics. These are synthetic receipt tests, not claims of live Telegram delivery.
- An actual headless smoke run on the installed OpenClaw version used the existing configured primary `gpt-6-astra`, direct mode, one `section11_context` call, zero tool failures and two assistant turns. It completed in 31.9 seconds and returned the expected sentinel. Earlier smoke runs exposed wrapper-policy conflicts, which were resolved and are rejected by the generation classifier. Smoke prompts requested public workout headings only; they did not generate athlete coaching advice, send messages or write calendars.
- Proposed/installed configurations passed the installed validator; the plugin loaded with its declared tool contract. Systemd units passed validation, and the report retry and telemetry timers are enabled/active. Three installed dry runs (morning, weekly, post-workout scan) passed. The ledger imported 23 previously reported activity IDs without backfill. Its initial state contained only those legacy records, with no new generation/delivery attempts.
- Source hashes were compared to the tested candidate. Existing model/reasoning/channel configuration, report schedules/identities, secondary config/job definitions, original post-workout source/override, installed coaching protocol/sync and original telemetry baseline were independently compared and preserved. Private installation records and rollback material identify the explicit paths. The full coaching release remains uninstalled.
- The distribution manifest contains **187 files** and the saved artifact audit was regenerated. No additional Telegram test messages or calendar writes were performed. Actual future scheduled receipts, operating costs and answer quality remain observations to collect; this step does not declare a quality pass or measured savings. Model/reasoning/caching tuning remains Step 5.

## Step 5

[Primary model/cache/context policy](examples/agentic/openclaw/MODEL_EFFICIENCY.md) adds a bounded live comparison harness, guarded report routing, provider-appropriate cache behavior and durable source recovery. The configured primary main/utility models, authentication identity and requested reasoning remain unchanged in production. Candidate routing is installed but disabled: a switch requires a manifest-bound, recent, repeated comparison with all automated checks, answer-bound independent human reviews and a reported benefit. Routine morning cases alone can use an approved candidate; complex/uncertain cases, weekly review, post-workout and interactive planning retain baseline. Missing wearables alone do not change routing eligibility.

The actual route is OpenAI OAuth/ChatGPT-backed Responses. The primary now explicitly keeps the provider's default cache window (`cacheRetention:short`); unsupported API lifetime fields, Anthropic tuning and paid keep-warm heartbeats are not added. Reports have a fixed private working directory, ephemeral private prompt/config files, stable templates/instructions first and lossless JSON ordering with volatile metadata last. Current evidence is still freshly read and rechecked before delivery. Prefix stability creates an opportunity for reuse, not proof of cache savings.

Only old typed `section11_context` results are eligible for cache-TTL pruning after 30 minutes and context pressure. The installed library preserves the latest three assistant turns, original transcripts and consistent replay projections. Arbitrary exec/Code Mode wrappers and write receipts are excluded, so not every wrapped interactive read is pruned. Safeguard compaction has strict identifiers, one quality-guard retry, three recent turns and a 2 MiB active-history byte backstop. The existing notifications and compaction/utility model choices are preserved. Native summary failure can still omit older whole turns; recovery instructions require fresh source reads and clarification of missing asks/confirmation state.

A 1,226-byte `MEMORY.md` indexes current sources rather than copying metrics or schedules. `USER.md` retains its original content and gains an active, dated directive for the athlete's intentional intermittent Fitbit HRV, optional RHR and useful current subjective feedback. `AGENTS.md` adds a source-recovery section reinjected after compaction. Dated daily memory and existing transcripts are retained unchanged. This supplies durable source/preference continuity, not an invented managed plan or proof that every old conversational fact can be recovered.

### Verification

- All **1,251 developer tests passed locally** (38.132 seconds) and **on home-server** (91.348 seconds), including 24 efficiency cases and the new uncertainty-vocabulary regression. Existing credential, fresh-context, execution/deadline, delivery, coaching and library tests remain passing. The evaluator's 12 reference answers and 12 independent negative controls still pass their harness self-test; this is not a live quality certificate.
- Actual installed-library pruning tests verified TTL gating, recent-turn protection, receipt exclusion, unchanged original transcript content and projection replay, with zero model calls. A source scan found 73 active session projections and two above 2 MiB; the largest decoded event history was 13,519,380 bytes. These are decoded serialized-history sizes, not model input/token counts or proof that all that history was submitted on a particular turn.
- The initial live pilot exposed a pre-existing evaluation defect: exact uncertainty IDs were expected without being defined in model prompts. It was stopped after 16 invocation slots (14 completed, two interrupted with unknown outcome) and retained separately with original source. Shared uncertainty vocabulary is now supplied identically to all cases, without exposing per-case expected checks or reference answers. That pilot is excluded from corrected-comparison scores; its label mismatches are not treated as coaching failures. Total task invocation slots across both experiments were 40; the corrected table below is not a total task-cost estimate.
- The corrected live experiment completed **24 no-tool invocations**, one repeat of twelve cases per arm, using only synthetic facts and the existing primary auth pin. Actual returned model/provider matched the requested arms; model plus requested effort are compared as a package. All original answers, hashes, metrics and blank review forms are retained privately. The baseline missed one structured-session-presence check; candidate passed all automated checks. Neither has an independent reviewed quality pass. One repeat cannot meet the promotion policy, so the candidate remains disabled.

| Corrected exploratory comparison | Baseline | Candidate |
|---|---:|---:|
| Requested model / effort | gpt-6-astra / medium | gpt-6.1-sol / low |
| Completed invocations | 12/12 | 12/12 |
| Automated contract passes | 11/12 | 12/12 |
| Median observed CLI wall time | 39.755 s | 38.567 s |
| Reported input / output | 33,862 / 4,496 | 33,900 / 4,778 |
| Reported cache-read / cache-write | 0 / 0 | 0 / 0 |
| OpenClaw-reported USD estimate | 0.56342 | 0.11558 |

These are exploratory synthetic-run counters and configured pricing estimates, **not verified account charges or production savings**. The corrected cohort excludes the stopped pilot and cannot be pooled with older prompts. Zero reported cache counters are not evidence of free calls. The baseline's failed structured check is not by itself proof of a wearable safety failure; prose and decisions require review.

- Proposed and installed configs passed the installed validator. The primary Gateway logged the change and successful hot reload, with no observed reload rejection/restart requirement. Three installed dry runs and two zero-model generation integration checks passed; fixed private cwd, complete source data, redaction, read-only limits, disabled report memory-flush and baseline routing were verified. Private delivery audit passed without a message.
- Installed sources match the tested candidate. Primary schedules, channels/auth/main/utility model settings and requested effort, secondary config/job definitions, installed protocol/sync, original telemetry baseline and prior workspace content were compared and preserved. The report and telemetry timers remain active. A private pre-change baseline, installation record, source hashes and rollback material are saved.
- The distribution manifest contains **191 files**, and saved/local/server artifact audits were regenerated and verified. No extra Telegram messages or calendar writes were made; no production model downgrade or broader coaching-release installation occurred. Real future cache/cost/latency behavior and model-answer quality remain observations to collect. Review and confirmatory comparison are required before model promotion; automatic tests do not substitute for them.


## Long-term history follow-up: three steps completed

1. Deterministic private activity facts and coverage-aware monthly summaries now
   work without a minimum history age. Reconciliation handles missing metrics,
   duplicate identities and old edits/deletions. Explicit athlete confirmation
   is dated and bound to the confirmed activity identities, never extended to
   future logging completeness.
2. The typed context tool adds an 8 KiB long-term view, dated monthly queries,
   exact activity facts and original managed-review reads. Morning packets do
   not automatically load monthly history. Missing reviews remain unavailable;
   no block intent, adherence or causal response is invented.
3. The primary hourly history service and daily full reconciliation are live.
   A private companion supplies canonical monthly reads alongside the older
   installed sync. Primary model/configuration and report schedules, secondary
   configuration/jobs and the broader installed coaching release were preserved.

Validation: **1,278 tests passed locally and on home-server**. Actual SDK tool
registration and five read-only tool executions passed; the measured primary
long-term packet was **4,932 bytes**. Live API activity counts, duration and load
reconciled with the projection. The service/timer, database integrity/private
permissions, three report dry runs and installed source hashes passed. No model
calls, messages or calendar writes were needed for this follow-up. At this stage no managed
review store was configured on the primary. The subsequent managed-review
integration below configures the store and reader; actual historical reviews
remain unavailable until a real plan and reviews are recorded.

The current distribution manifest contains **195 files**; artifact hashes and
the saved audit were regenerated. See the [history contract](examples/agentic/openclaw/LONG_TERM_HISTORY.md)
for the canonical-source, coverage, retrieval and failure semantics.


## Managed reviews and fresh-onboarding readiness — 23 October 2026

The primary now has a typed `section11_coaching` bridge for current plan state,
current-day athlete feedback, validated plan proposals, server-owned review
preparation and transactionally saved reviews. Account/source paths are fixed in
private configuration. The model cannot supply its own readiness/API snapshot.
Captures expire after 15 minutes; changed safety, feedback or plan state prevents
use of an old review receipt. The tool has a bounded per-run operation budget and
complete-output limits. It never publishes calendar changes or sends messages.

Weekly/block reports retain their existing schedule, model, read-only agent tool
surface and delivery supervisor. They prepare actual source evidence, return one
structured artifact, and save its validated review before report delivery.
Unchanged reviews stay quiet; cached reports need a still-valid saved receipt.
The bounded history reader is configured for the same private store. See
[managed review operation](examples/agentic/openclaw/MANAGED_REVIEWS.md).

Onboarding is deliberately pending: the user chose to describe current goals and
availability through Telegram after code updates. No stale goals, sample plan or
inferred schedule seeded a real managed plan. A private archive with 104 verified
coaching-context/old-plan files and restore instructions is prepared. Active
personal context and the current conversation were not reset, and no new agent
conversation was started. Archive preparation and fresh-start cutover are distinct.

Validation: **1,306 tests passed locally and on home-server**. An isolated actual
OpenClaw SDK registration/transport test executed six typed operations, saved and
read back a real synthetic review and proved an unchanged retry did not duplicate
it. The fuller synthetic loop also verified applicable managed publication,
observed completion/tolerability, a justified stored revision and history recovery.
These are software checks, not live model-quality or training-efficacy claims.

Installed plugin/configuration and matching skill checks passed, alongside three
report dry runs and source/runtime parity checks. The skill uses a normal installed
copy of the tested distribution; the loader did not discover the attempted linked
copy, and the failed attempt was rolled back before the ordinary installation.
Primary models, account/channel identities, schedules and the secondary account
were preserved. The current source snapshot has 273 files and the distribution
manifest has 201 files. No test model calls, messages or calendar writes were
required. Private rollback and installation records remain on the server.


## Coaching tool-schema repair — 23 October 2026

Live onboarding exposed a transport defect: bare payload/draft objects were
converted by OpenClaw's normalizeOpenAIStrictCompatSchema to empty closed objects,
rejecting nonempty feedback before backend validation. Direct SDK execute tests had
not exercised this conversion. Explicit feedback, proposal/plan/prescription and
review-draft schemas now preserve nullable fields and reject unknown input. Shared
root definitions avoid repeating full plan/interval shapes. No backend readiness,
source, capacity, review, publication or approval guard was relaxed.

The native regression reproduces the old rejection and checks valid/invalid
fixtures through compatibility/strict conversion and runtime/provider projection.
The isolated SDK loop now validates converted arguments before each of its six
operations, including feedback persistence and a deduplicated saved review recovered
by the history reader. Synthetic fixtures never enter the actual athlete store.
This repair requires a plugin reload, not another conversation reset or automatic
replay of previously rejected feedback. See [operation and verification](examples/agentic/openclaw/MANAGED_REVIEWS.md).


## Primary keyword-memory repair — 23 October 2026

Onboarding exposed a memory index/configuration mismatch: an FTS-only index was
being compared with the default OpenAI text-embedding-3-small identity, so ordinary
memory search was disabled. The primary now explicitly selects provider none,
sources memory and rememberAcrossConversations false under
agents.entries.main.memory.search. The installed validator accepted the override;
the supported index refresh produced a valid FTS identity, and both CLI and live
Gateway searches retrieved active notes. No embedding request, transcript backfill,
conversation reset, feedback replay or training-data change was required.

The pure primary-only configure_keyword_memory helper and regression checks retain
model/channel settings, other agents and unrelated query options. The normal cache
configuration preserves the explicit memory policy. Keyword-only search has no
embedding-based semantic ranking; semantic retrieval needs a separately configured,
funded provider and a compatible index. See [memory policy](examples/agentic/openclaw/MODEL_EFFICIENCY.md#primary-keyword-memory-policy).


## Durable onboarding repair — 23 October 2026

Onboarding previously saved explicit goals and constraints only in current-day feedback. The dossier and memory index still said intake was pending, and exact-approval instructions conflicted with automatic faithful recording. A new private versioned intake store now accepts explicitly supplied facts before a plan exists, with source/date attribution, validity/review flags, account binding, idempotent requests and committed readback. State distinguishes intake pending from plan pending; every bounded task packet retrieves the saved intake independently of memory search. Health observations expire on their observation date; restrictions never imply recovery or current clearance. Updated instructions authorize faithful onboarding recording without a second permission prompt while preserving approvals for inference, conflicts and calendar publication.

Review evidence and cached acknowledgements are bound to the intake revision. Native schema conversion coverage includes the new operation. Synthetic regressions recover the same record through fresh-process next-day state and context reads. These checks establish persistence and retrieval, not a guarantee of future model compliance. Keyword-only memory remains explicit; no embedding provider is required. Real athlete records stay outside source/distribution.

Deployment validation: 1,317 tests passed locally and on home-server, including the installed OpenClaw schema pipeline. Eight isolated native SDK operations saved/recovered intake before a plan, then saved/recovered a synthetic review with an idempotent retry. The verified primary Telegram answers were faithfully imported into private intake and stable dossier context; a fresh process dated 24 October recovered the same 13 entries through state and task packets. Prior-day health was historical; no clearance was inferred. Real-size testing exposed a packet overflow, now handled by explicitly deferring bulky history to a dated read while preserving full intake and health envelopes, the original byte bound and history evidence identity. Three report dry runs, live keyword-only Gateway search, archive checks and source/runtime parity passed. No test model/embedding calls, messages, calendar writes or conversation reset were required. A first real model-led plan/review cycle remains a separate acceptance check.


## Live usage follow-up, step 1 — 23 October 2026

The live interactive path wrapped reads in Code Mode exec results, bypassing the typed-read pruning selector. The 2 MiB history guard allowed prompts around 210k tokens; mid-turn pressure checks were disabled. Step 1 switches primary interaction to direct tools, retains mixed exec/write receipts, lowers the preflight history guard to 256 KiB, and configures a 131,072-token Sol working budget with native between-call pressure checks and an 8,192-token recent tail. Pruning still requires TTL expiry/pressure, preserves recent results and never changes canonical transcript messages. It is not a provider-token meter or a promise of a hard per-exchange call limit (step 2).

The athlete explicitly requires Sol 6.1 medium for coaching, Luna 6 for simple helper work and no Astra. A separate pure configuration constructor preserves the primary auth pin, sets a closed Sol/Luna allowlist, selects Luna for utility/compaction/flush/delegated helper work and prevents historical benchmark promotion from changing Sol medium. Existing goals, training facts, plan/review/publication stores and original write receipts remain private source records; the model change does not reset them. Tool execution is deterministic and does not need an extra Luna call for each tool. Existing synthetic comparison baselines are retained as historical evidence.

Native tool output compatibility: at a 64k model working context OpenClaw caps live tool text at 16k characters. The tested primary budget is therefore 128k, with a private context-profile `tool_packet_bytes:30000` limit below its native 32k tool cap. The CLI emits complete JSON or an explicit failure; it defers bulky history, selected dossier sections and, when necessary, intake to labelled exact reads. `section11_context intake` recovers the complete saved record with source dates and temporal flags. Required deferred reads must precede advice relying on those facts. Internal deterministic report building retains its full source packet. The working-context limit is a native pressure budget, not a claimed hard bound on all provider accounting or per-exchange calls.

Step 1 rollout validation: the primary configuration passed the installed validator, native projection/pressure tests and the full developer suite. Live Sol medium retrieved the complete saved intake through the direct typed tool; a separate Luna low no-tool check confirmed helper availability. Twenty-seven existing session overrides were cleared through the supported session API without resetting conversation context. Before/after checks preserved all 7,054 pre-existing canonical transcript events, the full private intake revision history, managed plan, daily feedback and training facts. Four actual task packets fit 30,000 bytes, and three report dry runs passed. Keyword-only memory, authentication and secondary-account configuration remain unchanged. Initial smoke checks exposed native result truncation and a staged-schema mismatch; those failed checks are retained privately rather than treated as successful retrieval. No Astra call, message or calendar write was needed for validation. Real workload savings still require subsequent telemetry; total per-exchange call/token limits remain step 2.


## Live usage follow-up, step 2 — 23 October 2026

Implemented primary-only batched exact reference retrieval and exchange work guards.
`section11_context references` accepts one to six closed-schema source/heading
requests, reads each source once, deduplicates selections, preserves provenance,
and returns complete bounded JSON or fails the entire batch. The primary 30,000-byte
transport cap still applies. Fresh health/intake/plan and approval rules are unchanged.

Primary limits are six observed model attempts (the sixth reserved for final
response), ten admitted tools and a 300,000-token estimated cumulative work target.
The gate blocks new tools including concurrent admissions; admitted writes finish,
receipts remain intact, and the coach must report pending work rather than retry.
Counters use run identity, never conversation identity. Report agents retain their
existing read-only policy. Sol medium/Luna, keyword memory and secondary settings
are unchanged.

**Enforcement limitation:** the installed native model hooks are best-effort
notifications, not cancellable provider admission. These are enforced tool gates
and advisory model/token ceilings, not hard provider-call, token, credit or cost
caps. Token admission estimates UTF-8 bytes / 3 plus a 16,384 output allowance per
observed request. Private gateway `section11_exchange_attempt` records separate
actual normalized end-of-attempt input/output/cache/total from that estimate. No
savings or quota conversion is claimed. Strict provider ceilings require native
runtime support; internal retries and compaction may escape these observations.

Validation covers closed batch schemas, source deduplication, all-or-nothing size
failures, per-run isolation, parallel reservations, token-estimate/actual separation,
native schema conversion and native hook vetoes. No model calls, Telegram messages
or calendar writes are needed for these deterministic checks.


## Live usage follow-up, step 3 — 23 October 2026

The original proposal to compare Sol and reserve Astra is superseded by the
operator's fixed policy: Sol 6.1 medium owns coaching; Luna 6 handles simple
utilities/compaction and explicitly delegated bounded execution. Astra is never
eligible in the primary account. Most model configuration was deployed in step 1;
this step hardens the remaining policy checks instead of spending credits on a
prohibited comparison.

Fixed-policy recognition is independent of allowlist order and works at defaults
or main-agent scope. Routing and benchmark guards reject Astra and non-medium Sol
under either representation. Agent-level effort is now explicitly medium and its
override is checked before routing; an invalid override fails rather than being
misreported as default medium. Report telemetry records effective requested effort.
Luna no-tool helper fixtures explicitly set helper effort, avoiding accidental
inheritance of main medium. Invalid/identical benchmark arms fail before scheduling
workers or creating invocation intents. Historical experiment answers remain intact.

Live audit found Sol medium/Luna configured and all 27 existing primary sessions
free of conflicting effort overrides. Session context is retained; no reset or
replay of writes is needed. Configuration allowlists/settings and application
checks are not a provider-level firewall against future operator edits. This step
adds no autonomous helper spawning and makes no model-quality or savings claim;
real coaching quality still requires review of real answers and athlete response.

Validation: 1,326 tests passed on home-server; locally the same suite passed with
one installed-runtime-only check skipped. No test model calls were made.


## Routine context notices and managed publication credentials — 23 October 2026

Native OpenClaw emits its bounded-history notice on every latched bounded-context
turn while compaction.notifyUser is enabled. Primary configuration now sets it
false. The 256 KiB history guard, 128k working context, mid-turn checks, protected
receipts, recovery instructions and persisted transcripts remain unchanged. This
silences routine maintenance notices; missing evidence still requires clarification
in the actual coaching reply. It does not expand model context or restore omitted
chat turns to the prompt.

Managed publication previously resolved credentials only from cwd/environment.
The primary private sync config exists outside the Telegram workspace, causing
preview construction to fail. push.py and coaching_plan.py now accept an explicit
absolute --credentials-dir, distinct from the managed-plan --data-dir. It loads a
complete account pair internally from a private owned ordinary fixed-name file,
rejects missing/invalid/symlinked or mixed sources, and never falls back to another
account. Legacy resolution is preserved without the flag. Credential-file access
protection is unchanged; directory-only CLI arguments are permitted and file
contents never enter model context. Managed athlete binding, exact preview approval,
readback and no-retry safeguards remain authoritative. Primary workspace commands
now include the configured credential and plan-store locations. Source diagnostics
use Python/grep when rg is absent.

Validation: all 1,331 tests passed on home-server; local tests passed with one
installed-runtime-only skip. The exact failed managed revision preview succeeded
through the real CLI from the Telegram workspace, with three GET requests, three
proposed actions and zero calendar writes. HTTP mutations were blocked during this
check. All prior plan/receipt rows, saved intake, feedback, training facts and
7,123 existing canonical transcript events were preserved. Three report dry runs
passed. No test model calls, messages, publication or conversation reset occurred.
