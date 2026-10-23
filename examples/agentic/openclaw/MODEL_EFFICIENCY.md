# Primary model, cache and context policy

The operator policy of 23 October 2026 fixes primary coaching on GPT-6.1 Sol at medium reasoning. GPT-6 Luna handles utility work, compaction and explicitly delegated bounded tasks; it does not independently own training strategy. Astra is excluded from the closed primary model allowlist, fallbacks, active aliases and report routing. The original authentication pin is retained. Historical experiment records below remain historical; their routing cannot override this instruction. Model names alone do not establish price, latency or coaching quality. The primary account currently uses OpenAI OAuth/ChatGPT-backed Responses through the OpenClaw runtime; the main-agent model overrides the different global default. Its utility model is separate. The secondary account remains outside the current primary deployment scope.

## Active context and caching changes

`efficiency_config.py` builds the primary configuration without changing its main/utility model or requested reasoning level:

- `cacheRetention:short` is explicit for the main agent. Installed OpenClaw keeps the session cache key on ChatGPT-backed Responses and omits OpenAI API lifetime fields on that route. Anthropic cache settings, a paid keep-warm heartbeat or a speculative extended TTL are not added.
- Autonomous reports use a fixed private working directory. Configuration/prompt files remain separate mode-0600 ephemeral files, deleted after the run. Their current report template and instructions precede athlete data; lossless JSON ordering moves volatile timestamps/provenance behind substantive fields. No facts, safety envelopes, dates, nulls or source metadata are removed, and every report still reads fresh evidence. This improves the opportunity for prefix reuse; it does not guarantee cache hits or measured savings.
- Cache-TTL pruning is enabled after 5 minutes for **only** historical `section11_context` results. Installed OpenClaw also gates pruning on context pressure and protects the latest three assistant turns. It preserves original transcript entries and replays a consistent projection. Write/calendar receipts and arbitrary exec results are excluded. Soft-trimmed historical JSON is unusable as a complete packet; source-recovery instructions require a fresh whole read before using numbers or prescribing.
- Safeguard compaction retains three recent turns, strict opaque identifiers, quality checks with one retry, and the existing compaction notifications. A 256 KiB active-history byte guard requests semantic compaction before a new run. This is a history budget, not a tokenizer estimate, model-context guarantee or on-disk deletion policy. If native compaction times out or cannot reduce history, OpenClaw can omit older whole turns; missing asks/decisions must be clarified, not reconstructed. The recovery section is reinjected after compaction. The configured Sol working context is 131,072 tokens, keeping the native model window intact. Native mid-turn pressure checks run after appended tool results and before the next model call. The recent-tail target is 8,192 tokens. Luna is explicitly selected for compaction and pre-compaction memory flush; strict identifier preservation and the existing one-retry quality guard remain enabled.
- A small `MEMORY.md` indexes the current dossier, current data and current managed-plan/review sources. An active, dated `USER.md` directive records the athlete's stated preference for optional overnight Fitbit HRV, optional RHR and current subjective feedback. These files contain no copied metric snapshot or old schedule. Existing daily notes are retained as historical context. Durable changes need explicit athlete provenance; temporary symptoms, feedback and availability need observation dates and expiry/recheck. Unresolved asks, confirmation state, corrections and exact revision IDs must survive; unavailable state requires clarification.

The [official OpenAI caching guide](https://developers.openai.com/api/docs/guides/prompt-caching) supports stable instructions/reference material before dynamic input and distinguishes cache behavior across API/model families. It does not establish how this account's OAuth route is billed. Native route behavior above was checked against the installed OpenClaw 2026.10.6 documentation/source. A provider cache is not a saved coaching response: fresh health evidence and ordinary generation/delivery checks remain necessary.

Primary interactive Code Mode is disabled: fresh `section11_context` reads use their own typed tool identity, so the existing read-only pruning rule can recognize them. Legacy mixed `exec` results remain excluded because they can contain write receipts; `section11_coaching`, write/edit tools and arbitrary execution results are explicitly denied pruning. Existing canonical transcripts are retained. TTL pruning is gated by both expiry and pressure, and protects the latest three assistant turns; it is not an always-running within-turn token cap. The separate mid-turn native pressure check handles growth during a long exchange. Compaction and fresh readers recover saved intake, managed plan/review identities and pending publication decisions; they do not authorize calendar changes.

## Primary keyword-memory policy

The primary agent deliberately uses local keyword search. In installed OpenClaw
2026.10.6 the override is `agents.entries.main.memory.search`, not the retired
`memorySearch` spelling:

```json
{"provider":"none","sources":["memory"],"rememberAcrossConversations":false}
```

`configure_keyword_memory` constructs this explicit, primary-only override while
preserving model/auth/channel settings, other agents and unrelated memory options.
Apply it intentionally; the ordinary cache/context constructor preserves it. This
policy does not enable session transcript indexing/backfill or import retired
personal context. It leaves Section 11's deterministic training history, dossier
and managed plan/review readers in their existing stores.

OpenClaw defaults to OpenAI embeddings when the provider is unset. An index built
in FTS fallback mode can then report `model fts-only, expected
text-embedding-3-small` and disable retrieval. Explicit provider none aligns the
configuration and local index, without an embedding API call. Once the proposed
configuration passes the installed validator and is active, refresh with
`openclaw memory status --index --agent main --json`; verify provider none,
searchMode fts-only and a compatible index identity. Test both CLI and running
Gateway memory.search against known active notes, checking result paths without
publishing private snippets. Do not reset the conversation or clear training data.

Keyword recall does not provide embedding-based semantic ranking. A future switch
to embeddings needs an explicit provider/model choice, working billing/auth and a
compatible rebuilt index; an untested fallback is not a cost-free semantic index.

## Measured model/reasoning comparison

`model_benchmark.py` runs the twelve Step 2 synthetic cases against the configured main baseline and a candidate, preserving the existing primary authentication pin. The experiment compares **model plus requested effort as a package**; changing both does not isolate the effect of either. Current candidate: `openai/gpt-6.1-sol` at requested `low`; baseline: the configured `openai/gpt-6-astra` at requested `medium`. The returned envelope must confirm the actual model/provider. Requested effort is recorded separately; the envelope does not independently attest the wire-level effort.

The comparison has two concurrent workers, fixed per-case inputs, alternating arm order, a 120-second model deadline and 160-second outer deadline. A single repeat has 24 invocation slots; two repeats have 48. Provider-internal retries remain unobservable. A persisted intent consumes its slot even after a crash; existing unknown slots are never silently rerun. The first pair must complete with the correct model and zero tools before later pairs run. There are no judge-model calls, athlete input, report sends, calendar writes or application retries. Tool-denial is explicit, with the report-mode hook as an additional boundary. Each invocation uses isolated headless state and a fixed private benchmark workspace.

Private records retain original structured answers, input hashes, requested model/effort, observed model, status and actual envelope usage/latency/cost fields. Case/contract/evaluator/runner/config hashes identify provenance. Missing/zero price is unknown, not free. The native token fields and sample counts are preserved without inventing costs or merging them into unrelated Gateway metrics. Concurrent pilot timings are exploratory; one repeat does not establish stable performance or production report equivalence.

```bash
python3 model_benchmark.py --output /private/benchmark-primary --profile /private/report-primary.json --repetitions 1 run
python3 model_benchmark.py --output /private/benchmark-primary assess
```

The evaluator now supplies a shared uncertainty-ID vocabulary to every prompt. The initial pilot exposed that the older harness expected exact IDs such as `current_state` without defining them. Those label mismatches cannot be interpreted as coaching failures. That pilot is retained separately, with its original source; corrected-prompt experiments have different context/evaluator hashes and must not be pooled with it.

## Guarded routing

`model_policy.py` defaults to the configured main model. A private `routing-primary.json` must explicitly enable a candidate and bind it to an experiment manifest:

```json
{
  "schema_version":1,
  "enabled":false,
  "benchmark_dir":"/private/benchmark-primary",
  "manifest_sha256":"SHA256_OF_EXPERIMENT_MANIFEST"
}
```

Enabling the flag alone is insufficient. The policy recalculates the assessment and requires current fixture/evaluator/runner provenance, at least two repeats, every automated check and every answer-bound independent human review for both arms, matching baseline model/requested effort, an experiment less than 30 days old, and a measured benefit (at least 10% lower complete positive reported cost or 20% lower median wall time with all invocations completed). These are conservative operational thresholds, not statistical proof. Human review files use the Step 2 four-dimension rubric and response hash; no scores are generated automatically. Operator attestations are trusted, not independently authenticated human identities.

Even then, a candidate is eligible only for a routine morning report with current sources, a normal P3/go decision and established non-triggering health context, without alerts, race-week deferral, modifications or athlete notes requiring interpretation. Missing HRV/RHR alone does not affect routing. Missing/partial health coverage, complex cases, weekly review, post-workout interpretation and interactive planning keep the baseline. This is model selection, not health clearance. Auth identity, read-only tool limits, output validation and supervisor delivery remain fixed. Unknown/invalid/expired evidence fails back to baseline; there is no automatic cross-model retry of a generation or send.

The historical pilot is one repeat and unreviewed. The current operator policy fixes Sol medium regardless of promotion eligibility; benchmark construction rejects Astra and Sol at a different effort when that policy is active. Any future promotion needs a fresh confirmatory experiment and original-answer review; synthetic contract passes alone cannot certify coaching quality. A single gate failure is a reason to retain the baseline, not proof that a model is generally unsafe.

## Installation and validation

Install the three Step 5 helpers alongside `report_runner.py`, the revised evaluator and telemetry collector in private runtime storage. Add the recovery block to primary workspace `AGENTS.md`, create the small memory index without overwriting existing memory, and append the active preference directive to `USER.md` without replacing prior content. Backup each original file/config and record an absent original memory file explicitly for rollback. Never edit or delete existing transcripts/daily memory to reduce costs. Keep experiment records and reviews outside Git.

Validate the proposed/installed configuration with the installed OpenClaw validator. Test pruning against the installed library using synthetic large tool results: TTL gating, latest-turn preservation, receipt exclusion, transcript immutability and projection replay. Test actual no-tool benchmark/model routing, private report-workspace/prompt handling and unchanged safety/delivery invariants. Full developer tests run locally and on the server. Telemetry records report route and **requested** thinking separately from observed model/provider; compare future real scheduled runs before claiming savings or equivalent quality.

### Durable onboarding recovery

A versioned private `athlete_intake.sqlite3` stores explicitly reported goals, experience, equipment and dated constraints independently of daily feedback or a plan. `section11_coaching state` and bounded task packets recover the same account-bound revision after a session reset. Read temporal/review flags; old health observations never establish current clearance. `MEMORY.md` remains a small source index, and keyword-only search remains deliberate. See [the intake save contract](MANAGED_REVIEWS.md#save-intake-before-a-plan-exists).

Native tool output compatibility: at a 64k model working context OpenClaw caps live tool text at 16k characters. The tested primary budget is therefore 128k, with a private context-profile `tool_packet_bytes:30000` limit below its native 32k tool cap. The CLI emits complete JSON or an explicit failure; it defers bulky history, selected dossier sections and, when necessary, intake to labelled exact reads. `section11_context intake` recovers the complete saved record with source dates and temporal flags. Required deferred reads must precede advice relying on those facts. Internal deterministic report building retains its full source packet. The working-context limit is a native pressure budget, not a claimed hard bound on all provider accounting or per-exchange calls.

If a build still exceeds the transport budget, recent activities are explicitly
deferred to `activities` with the same task (and activity_id for post_workout).
The reader returns the exact fresh selected rows and source hashes. Retrieve them
before interpreting completion, and refresh core health/readiness if source
identity changed between reads. Core readiness and health are never dropped.

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
