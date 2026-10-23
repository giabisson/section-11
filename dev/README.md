# Developer validation

After syncing the server repository, run `python3 dev/check_primary_parity.py`
to verify it against this working tree. `--include-runtime` additionally checks
separate runtime/skill/unit copies. Private data/configuration is excluded. See the
[deployment policy](../examples/agentic/COACHING_DEPLOYMENT.md).

Maintainer validation material for this repository.

**If you are setting up Section 11 as an athlete, you do not need anything in this
folder.** From `sync.py` v3.138, `--init` and `--update` no longer install this
maintainer material. Nothing in the setup path, the protocol, the report templates
or any user workflow reads it or runs it. A copy left by an older install can be
ignored entirely.

The tests exist so that a change to `examples/sync.py` or
`examples/agentic/push.py` can be shown not to have broken behaviour that a live
run does not reach.

## Repository snapshots and updater scope

`--init` installs exactly the files listed in the update manifest, plus the
manifest itself, after checking each file against the hash the manifest records.
`--update` refreshes the same list. The manifest generator excludes `.github`,
other hidden paths, this repository-root `dev/` folder, dependency directories and
cache directories. It also excludes `literature/cycling-training/sources/` and private coaching database/journal filenames; reviewed summaries remain distributed. None of the maintainer or local research/private records reaches an athlete installation. New tests are
still committed here; they are not shipped through athlete updates.

Installations created by an older `--init` may still hold `section11/.github` and
`section11/dev`, which `--update` does not refresh. Where `section11/` is not a
Git checkout, `--update` offers to move them to `section11-legacy-github/` and
`section11-legacy-dev/` beside `section11/`. It asks only in an interactive
terminal, moves them only when the word `move` is typed there, and never deletes
them. A `dev/` folder that stays is left out of
the orphan cleanup.

For development or reviews that depend on the tests, the website or GitHub
workflows, use a current Git checkout or a verified, commit-pinned
full-repository snapshot. Do not treat a manifest-updated coaching installation
as a complete current repository. This distinction requires no change to athlete
setup.

## Running

`test_openclaw_credential_guard.py` runs ten dependency-free Node tests for credential-file gates, encoded-secret filtering before model replay/persistence, failure behavior and retained delivery metadata. Node is required for these OpenClaw-specific checks. `test_runtime_safety.py` checks private multi-consumer key replacement and a read-only delivery audit against synthetic files and mocked HTTP; no live message is sent.

`test_coaching_release.py` checks explicit taper arithmetic without a required subgroup percentage, unknown event duration, mechanical work versus dietary calories, qualified durability windows, strength tradeoffs and actual new module bytes through fresh initialization/update. It checks publisher/private-record exclusion, installed-path plan/catalog imports and the read-only artifact audit; it does not contact a live runtime.

`test_coaching_review.py` replays successful progression, costly sessions, work-related misses, health uncertainty, changing availability/event dates and a multiweek plan. It tests exact pairing/publication-version selection, unknown formal adherence, preserved historical selections, current-day guards, optional wearables, atomic revision/review commits, opted-in scheduled execution and semantic idempotency without duplicate notifications or calendar writes. It executes no LLM or live service.

`test_coaching_plan.py` checks private transactional plan persistence, reloads,
immutable historical prescriptions, goal/date/availability revisions, request
idempotency, stale-parent and process-lock conflicts, session/day/week capacity,
explicit time overlap, rest weeks, optional wearables and other-sport accounting.
The real push outcome helpers run against synthetic HTTP verbs: exact previews,
single-use approval binding, stable event updates, removals, partial/refused/
unknown writes, post-send disk failures and process interruption, read-only
reconciliation and explicit externally attested manual resolution. It verifies
no duplicate writes, no retrospective deletion/rewriting, catalog/payload drift
rejection, selective context retrieval and local CLI use without credentials.
No live calendar, OpenClaw runtime or real athlete data is accessed.

`test_workout_validation.py` checks complete step expansion, final recoveries,
work/set counts, every checked catalog entry, time budgets, template/version/hash
binding, power denominators, absolute/relative targets, reference uncertainty,
native-description consistency, bounded expansion and the common preview/write
boundary. It verifies local rejection before HTTP, exact confirmed payload and a
single send with synthetic transport, and distinguishes FTP setting dates from
unknown assessment provenance. No server parser or trainer is contacted.
The catalog coverage check requires all 26 library IDs. Eleven complex worked
examples have independently counted totals and one-second budget failures;
negative cases exercise cadence/technique, progressive targets, over-under
ordering, descending recoveries, free-effort sprint bounds/reference, mixed-ride
Z2 recovery and opener sequences. AN-3's full dose is 90.5–103.5 minutes, not the
old approximate hour. Labels cannot inject executable target/mode overrides.

`test_training_distribution.py` checks that changes in intensity distribution
emit informational context rather than automatic fatigue warnings, moderate time
alone does not trigger a restriction, and independent safety stops remain active.
It does not execute an LLM or certify complete training plans. The synthetic
planning-policy examples document expected coaching behavior for manual review.

`test_readiness_quality.py` checks calendar-aligned current readings, prior-day
baselines and coverage, duplicates/conflicts, invalid/future dates and values,
gaps in HRV/RHR persistence, yesterday's RI, and unknown device provenance. It
checks that grouped counts remain audit-only, health clarification reaches the
decision alongside favorable physiology, and completed-session Feel is not used
as current feedback. Full-producer wiring is also covered by `test_sync_facts.py`.

`test_optional_wearables.py` checks intermittent/missing overnight HRV, unavailable RI,
RHR and device sleep, absent physiological evidence, and preservation of adverse
RHR/sleep observations and P0/P1 stops. It uses synthetic inputs and no network.
The additive input context reports availability, not health clearance; athlete
feedback and health clarification remain consumer responsibilities.

`test_weather_demand_workflows.py` covers new point/hour demand through a closed refresh gate, unchanged-demand throttling, failure/Retry-After migration, point batching, bounded timeout splitting and cached repeats. It also checks optional repository-variable wiring and the push workflow's time argument construction, including malformed inputs. The bounded shell check runs only the extracted argument builder with synthetic inputs, never push.py or a dispatched workflow.

`test_data_overview.py` exercises companion discovery, relative paths, output placement, local-time/DST labels, 16-point wind directions and compact snapshots after display additions. It extracts the exact self-contained Python publication rules from `auto-sync.yml` for offline validation, fallback, deletion and reset/retry restoration tests. No GitHub or Git operation is needed. The workflow embeds the tested rules so users replace only sync.py and the workflow for 11.80, with no third bootstrap file.

`test_weather_map_design.py` covers name fitting/wrapping/ellipsis, unchanged full names, distance-dominant labels, ordered pagination and publication, page cleanup/symlinks, size bounds and the embedded antialiased glyph atlas. Synthetic extra bands test pagination without changing the six-point weather sampler. The atlas derives from supplied Lato Regular with geometric arrow fallbacks; its OFL licence is inline in sync.py and in the root third-party notices.

`test_weather_bands.py` checks the single forecast-band producer, exact map consumption, outlook omission, size bounds, coverage and wettest-period semantics, display decimals and report-template consistency. Weather/ETA preservation is also compared against the staged v5 review fixtures outside the suite.

`test_weather_final.py` checks trace-rain rounding, fixed one-decimal labels, equal endpoints, native periods and incomplete-rain handling without value mutation. It exercises the exact 120-hour boundary, all routed statuses beyond it, excluded unrouted counts, the 64-ride cap, near-term off/expired/partial states and stale map exclusion. Paired JSON examples are parsed and checked against the production brief identity, band producer, planned summary, map-page and overview contracts using synthetic weather only.

`test_route_weather_map.py` checks standard-library PNG encoding and determinism,
wind direction, forecast/outlook rendering, brief binding, off switches, bounded
file lifecycle and no-network behavior. Run with
`python3 -m unittest discover dev/tests -p test_route_weather_map.py` or the full
suite below. Its provider data are synthetic; no live forecast is tested.

`test_terrain_segmentation.py` covers native terrain segmentation boundaries, persistent
valleys, bounded exit extension, directional symmetry and admission/formatting
with hand-derived profiles and the offline network guard. Run it alone with
`python3 -m unittest discover dev/tests -p test_terrain_segmentation.py`, or as
part of the complete suite below.

From the repository root:

```
python3 -m unittest discover dev/tests
```

**Run the suite with the same interpreter that runs `sync.py`.** The tests
themselves use only the standard library, but they import `sync.py`, which imports
`requests` at module scope. So the requirement is interpreter identity, not machine
identity: having a working `sync.py` somewhere on the machine is not enough if the
tests are launched from a different interpreter. `python3` above is a generic
example, and many platforms have no `python` executable at all.

If `sync.py` runs from a virtual environment, invoke that environment's Python, for
example `/path/to/.venv/bin/python -m unittest discover dev/tests`, or activate the
environment first.

Nothing else to install, no arguments, no configuration.

Local and manual by design. No CI, no hooks, no coverage tooling, no test
dependency.

## Offline route ETA evaluation

From a complete source checkout, use the same Python environment as sync.py:

```sh
python3 -I -B dev/evaluate_route_eta.py /path/to/route_eta_history.json --as-of 2026-10-19 --outdoor-ftp-w 250 --body-weight-kg 75
```

The date, FTP and weight are synthetic examples. Supply the existing main
`thresholds.sports.cycling.ftp` and current wellness/profile weight, never eFTP or
indoor FTP. Optional `--power-zone-upper-pct 55 75 90 105 120 150 999` accepts
existing outdoor zone percentage upper boundaries. Omitted/invalid main inputs
report physics unavailable; they are not guessed. Omit `--as-of` for the current UTC date. This reads the
local record without modifying it or using the network and emits aggregate JSON
only. No IDs, ride rows, coordinates or credentials are printed. Each fold removes
the held-out activity ID before fitting both the ETA model and stop ratios; the
evaluation compares unrounded moving-time bounds with actual moving time. It
reports coverage, median width in seconds, median width divided by central time,
median absolute relative error, method counts and excluded/insufficient counts.
The empirical target is about 70 to 85% coverage with narrow windows; it is not a
future guarantee. Stops and five-minute rounding are excluded from these scores.

The top-level scores retain the legacy v6 evaluator for comparison.
`physics_comparison.methods` adds three side-by-side methods on identical rides:
`pace`, `ftp_zones_physics` (wide 0.7 to 1.4 default window) and
`ride_power_physics`. Physics evaluation requires existing aggregate power and
ascent; producer ascent is preferred, recorded ascent remains a labelled proxy.
No held-out ride's power or time enters its target-power/time-factor fit or its
residual band. The band uses nested leave-one-out residuals from training only.
The safeguard needs at least 12 rides, no lower coverage and median widths in
seconds and relative terms at most 1.10 times pace. It also requires a complete
record comparison; partial power/ascent coverage cannot switch in-range routes.
History geometry is an explicit symmetric climb/descent aggregate proxy, not
observed gradients. These scores cannot validate a GPX profile, new-terrain
coverage, stop timing or actual forecast performance. Missing power still leaves
the legacy evaluation available. Fields arrive through normal existing fetches.
Descending physics now compares flat-target-powered speed with coasting speed,
under the unchanged 50 km/h cap. The three-method scores include that change.
They do not include the separate route-geometry consistency factor: the record
has no historical polylines. That factor compares familiar attached-route
physics with supported pace, and transfers only a bounded, halved deviation to
unfamiliar terrain. Agreement is not an additional measured coverage result.
At least four eligible rides are needed for a fold with three training rides. The window is 180 days;
future, old, indoor and malformed rows are excluded, duplicate IDs collapse.
Run on private data locally and share only the aggregate result. No real record
belongs in the repository. This developer tool is not installed by athlete updates.

## Conventions

**Standard library only.** `unittest` and `unittest.mock`, nothing else. No test
ever makes a network call: every HTTP boundary is patched, and each test module
installs a guard that raises a `BaseException` subclass if a call escapes anyway.
A guard deriving from `Exception` would not do, because both modules under test
catch broadly and would convert an unmocked call into an ordinary failure result,
letting the test pass without exercising anything.

**No real athlete data.** Every fixture is synthetic and built inline by a helper.
Real `latest.json` or `intervals.json` output must never be committed as a
fixture, including anonymised. If a test needs a shape that is awkward to
construct by hand, construct it by hand anyway. Scratch files a test writes go to
a `TemporaryDirectory` and are discarded with it.

**Modules are loaded by path.** `sync.py` and `push.py` live outside a package and
are not importable normally, so `importlib.util.spec_from_file_location` is used
against a path derived from `__file__`. Tests must not depend on the working
directory.

**Shared helpers live in `_harness.py`.** The loader, the `NetworkBlocked` type,
the verb-seam installer and restorer, and the `RefuseEverything` object-seam
sentinel are shared by all six modules. There is no single guard installer,
because the two seams are not the same mechanism: the verb seam swaps named
attributes on a real module and restores them, while the object seam replaces one
lazily-bound object with `RefuseEverything` and assigns the saved original back. The leading underscore keeps the file outside
`unittest discover`'s `test*.py` pattern, so it is imported and never collected.
What it deliberately does not share is the seam: `sync.py` needs its named verbs
replaced with `requests.exceptions` left reachable, and `push.py` needs its
lazily-bound `_requests` object replaced wholesale. Those protect different code
and stay separate, and each module still owns its own `setUpModule` and
`tearDownModule`.

**Test behaviour, and say so when you cannot.** Assertions target state
transitions, retry deadlines, what survives a merge, and what a preview path is
allowed to do, so a refactor that preserves behaviour does not break the suite.
Where a helper is private and has no public entry point, the test binds it
directly on purpose. Much of the fetch-state suite does this, so this is not an
implementation independent suite and should not be described as one.

**Name the defect.** Where a test exists because something was once wrong, the
assertion message says what would break. "429 Retry-After leaked into a later
request" is more useful in a failure log than "assertion failed".

**Put back what you replace, and swap nothing at import time.** Each module
captures whatever it swaps on the HTTP layer when it is imported, installs the
guard in `setUpModule` and restores the saved value in `tearDownModule`, including
after a failing run. Installation is deferred deliberately: `unittest discover`
imports every test module before running any of them, so a guard installed at
import time would mutate the process-wide `requests` module while unrelated modules
are still importing, and anything that bound a verb by name in that window would
keep the blocker even after it was restored.

## Current coverage

`test_intervals_fetch_state.py` covers the per-endpoint fetch state in `sync.py`:
Retry-After parsing in both header forms and the guarantee that a value cannot
leak into the next request; the retry ladder and its boundaries; deadlines derived
from activity start; the paired-planned extension applying to intervals but never
to streams; expiry to tombstone; strict ID pairing with no date or sport fallback;
`zone_basis` resolution including the ambiguous and unresolvable cases;
partial-success handling in both orders; streams success requiring a usable
`dfa_a1`; `compute_error` held distinct from `no_data`; timeout and 5xx handling;
due-endpoint isolation; sibling-only merging without duplicate activity IDs; stale
`zone_basis` removal; state persistence across a restart; cache invalidation on
`script_hash` change; pruning by `present_activity_ids`; string key normalisation;
and retries reaching outside the 72-hour scan window.

It was written against `sync.py` v3.121 and Section 11 v11.53. That pairing is
provenance only. Behaviour is validated against the current `sync.py`.

`test_http_policy.py` covers the HTTP policy added in `sync.py` v3.133 and
`push.py` v0.6. An AST guard walks `sync.py`, `push.py` and `pull.py` and fails if
any direct request carries no timeout, with a negative control that removes one
timeout from a copy of the real source and proves the same checker catches it.
Beyond that: retry eligibility by exception and status; the admission cap measured
from the start of the call, including time spent inside the request; the decision
to retry taken before sleeping, so an oversized `Retry-After` cannot buy a long
sleep followed by no request; the per-instance extra-attempt budget, shared across
a run and never reset; preservation of the original `RequestException` subclass so
`_build_health_context` still degrades rather than raising; the conditional
`chat_notes_status` marker and its consecutive-failure circuit breaker; the
`publish_to_github` pre-read gate, where only a confirmed 404 permits a create and
every other failed pre-read stops before the PUT; verification after an ambiguous
write on both services; and the `applied` / `not_applied` / `unknown` outcome
contract with its 0/1/2 exit codes. The load-bearing case is
`TestNoAutomaticReissue`, which drives all seven `push.py` write operations through
an ambiguous transport and asserts each verb was issued exactly once.

`test_push_smoke.py` covers the preview boundary in `push.py`: `preview_push`
makes no HTTP call at all; the read-only previews (move, delete, set-threshold and
both annotate forms) issue GET and never POST, PUT or DELETE; a negative control
proves the write blocker actually fires; and the CLI dispatches to preview by
default, with `--confirm` selecting the write path.

`test_workout_summary.py` covers the planned-workout `workout_summary` renderer in
`sync.py` v3.134 to v3.136 (issue #28): the two-step repeat, nested alternating and flat
alternating emitters assign no step role such as `rec`, however the targets
compare; an expansion oracle turns each summary back into ordered duration and
target steps and compares them with the synthetic `workout_doc`, so a dropped
step, a lost target or a reordering fails; the flat detector no longer skips the
step after a trailing rep. Explicit v3.141 cases add ordered flat summaries and
their telemetry, while repeat availability, compression and hard-session markers
stay pinned. `hard_sessions_planned` remains equal to constants from v3.133.
New flat summaries remove the need for a far-tier description preview; missing
documents still exercise that fallback. The fictional `latest.example.json` interval summaries equal what the
producer emits. Content the renderer cannot show (a step without a duration, a
repeat block it cannot compress, the unmatched final child of a nested repeat, a
target it cannot print as W or bpm: a relative unit, range bounds, an empty or
null target, a string value) must appear as an in-place marker on every output
path. v3.136 adds repeat semantics (a nested repeat is shown as a repeat or marked,
never by its aggregate duration; a malformed repeat shape is marked), repeat-count
and duration validity (zero, negative, fractional, non-finite, boolean and string
values), and the 2 W tolerance checked on raw values before rounding. Every
fixture step and repeat declares its expected rendering when it is built (`P`,
`T`, `A`, `X`, `R`, `XR`), so the oracle never calls `sync.py` and never inspects
a count, duration, target or `steps` shape; it is shown to reject the outputs of
both rejected candidates. An unmarked summary is checked to list every step with
its duration and primary power or HR target, within the stated tolerance
(targets within 2 W and durations within 2 s of the first compressed step);
secondary targets such as cadence are out of scope. The three fixtures whose summary
availability v3.136 changes are listed and justified in the module. The PRE and
POST report templates are checked against the producer: they must name its
markers, keep the labelled-recovery rule and the stated scope of an unmarked
summary, and for a null or marked summary must name the description field that the
producer puts on each row tier, with the near/far boundary and preview length they
state matching the producer's. No report is rendered.

`test_history_refresh.py` covers the `history.json` refresh gate, retention and
failure backoff in `sync.py`: the strict more-than-28-whole-days boundary with no
weekday or midnight window, catch-up after downtime, unusable and future
`generated_at`, aware, naive and DST-crossing timestamps, retention of an existing
file when the activities, wellness or athlete read fails, the atomic write and its
temp-file cleanup, the internal `refresh_state` ladder (1h, 6h, 24h) with
`Retry-After` and its 24h cap, clock regression, malformed state, script-hash
containment, sanitised error kinds, manual `--generate-history`, publication
failures that must record nothing, and the unchanged first-run behaviour. Runs go
through `main()` with a frozen module clock and a pinned host `TZ`, so the same
assertions run against the pre-repair `sync.py` and fail there on behaviour rather
than on a missing name. A GitHub Actions runner is simulated as a fresh directory
holding only the committed `history.json`, which also pins the accepted residual:
a run that is not published loses its state. It also covers the GitHub Actions run
budget: eligibility by run number, event and malformed number, fresh-runner chains
with unpublished failures and successes, its interaction with backoff, the
script-hash trigger and the unbudgeted first run, manual dispatch, re-runs, mixed,
skipped and out-of-order run numbers, and the deferral line. The module removes the
GitHub Actions run variables from its environment while it runs and sets them
explicitly per case, so it gives the same results inside GitHub Actions. It needs
`time.tzset()` and is skipped where it is unavailable.

`test_init_update_distribution.py` covers what `--init` installs and how `--update`
treats folders it no longer manages, in `sync.py` v3.138. Every archive is a
synthetic zip built in memory and every install lives in a temporary directory. For
`--init`: the installed set is exactly the archive manifest's file list plus
`manifest.json`; `.github`, hidden files, unlisted files and the root `dev/` folder
are never written; a missing or malformed manifest, an unsafe path (absolute,
traversal, backslash, drive), a wrong or malformed hash, a missing or duplicated
member, a member or manifest the archive declares as a directory, symlink, FIFO,
device or socket, and a wrong archive root each install nothing and keep the
bootstrap `sync.py`, while entries declared regular or with no declared type
install; an existing `section11/` is left alone. For the generator:
only the repository-root `dev/` is excluded, a nested `dev` folder is still listed,
and what it lists is what `--init` installs. For `--update` on an older install:
the move offer for `.github` and an unmanaged `dev/` is made only when standard
input is a terminal and acts only on the typed word `move`; piped or redirected
input is never read for it, even when it contains that word, and the
interactivity check fails closed; Enter, `y`, `yes`, EOF and Ctrl+C keep both; a taken backup name is never
overwritten; a failed rename keeps the original; modified and added files move
byte for byte; a Git checkout is not offered and a symlink is left alone; `dev/` is
not offered while the upstream manifest still lists it; and a `dev/` that stays is
never listed or deleted by the orphan cleanup, even when that prompt is answered
yes, while an ordinary orphan still is. The Git-checkout test, the terminal check
and the symlink test are substituted, and special file types exist only as modes in
an in-memory zip, so no test creates a `.git` directory, a terminal, a symlink or a
special file.

## DFA drift producer

`test_dfa_drift.py` exercises the actual rollup, summary, profile and fetch/cache
paths with synthetic streams only. It covers original-index thirds and remainders,
the unchanged whole-session gates and TIZ tie-breaking, separate retained and drift
masks, missing artifacts, finite alpha1 normalization, continuous 1 Hz timing,
endpoint and sixth coverage, scaled gap boundaries, deterministic failure reasons,
consumer eligibility, latest-session selection and eligible trailing denominators.
It also checks stream time retention, schema 2, hash-triggered 14-day backfill,
activity flags and crossing preservation. HTTP calls are mocked under the shared
network guard.

The fixtures include long endpoint gaps, a lost synthetic climb response, interval
work with low supra time, and value-dependent loss that passes the numerical
screens despite bias. These are regression and limitation tests, not physiological
validation or evidence that the thresholds generalize to all recordings.

## Completed-session structure

`test_sync_facts.py` covers coupled weekly 7:28 ACWR (including retained legacy history and the 0.68 to 0.74 example), unchanged live/start-of-day values and Overreached thresholds, paired no_steps/name/duration propagation, and descriptive cycling facts. Synthetic cases exercise four disjoint rolling chunks, metric-gate parity, mixed zone bases, exact end-date CTL, chunk-based biggest week, environment splits, missing/zero data, dated maxima, complete producer output, calendar-season partial-week exclusion, short curves, exact ID/date joins, the one-send cap, compact/legacy cache reuse and stale/unavailable fallback. Compact cache tests preserve duration winners, counts, names in summaries and original partial-window provenance, and reject malformed rows. The network guard has a direct negative control. These tests validate the supplied API response contract offline, not live provider behavior or physiological meaning.

`test_session_structure.py` uses synthetic activity/event/stream data to test exact pairing, resolved power bands versus genuine ramps, recording pauses, per-step coverage, zero versus missing data, current-plan comparison, repeated short-recovery sets and the bounded lag alignment in SECTION_11. Controls cover the exact step-start exclusion, offset ties/bounds/additive shifts, shortened recordings versus clipped lagged measurements, unsupported atoms and output caps. It also tests persisted cache reuse, expiry, revisions, late/changed/deleted plans, stale failures, Retry-After and request counts. Placement tests persist only latest.json and intervals.json between runs, exercise the retention boundary and summary carry-forward through day 28 without refetch, preserve interval/DFA flags and retry state, verify dropped-field absence and exclude Walk/Hike structure while retaining other-sport fallback. A structure-only entry cannot suppress an initial interval/DFA fetch. The network guard has a direct negative control. No private athlete fixture or FIT file is committed.

`test_workout_summary.py` keeps its independent expansion oracle and repeat regression constants, with explicit v3.141 flat-list availability changes. Formal adherence, independently verified outdoor boundaries and physiological validity are not validated by these tests.

`test_weather_corrections.py` covers assumed midnight/date-only departures, configured defaults, DST rejection/resolution, labels, effective departure ordering, overview serialization order, compact outlook clustering and push.py v0.8 local-time validation/preservation. Its mocked HTTP cases exercise one PUT, pre-read and exact-time readback, including an unknown outcome and same-date time-only update. These bounded calendar-time cases do not validate live API or client behavior.

## Not covered

`test_context_packet.py` covers bounded task context using synthetic files:
date-window completeness, stale/duplicate/missing history, timezone/DST handling,
preserved full safety envelopes and null measurements, exact Markdown sections,
explicit dossier selection/authority limits, exact activity identity, missing
dependencies, transport markers, output/source bounds and sanitized failures.
Live model choices or coaching judgments are not validated by these assertions.

The OpenClaw telemetry/evaluation integration is covered separately by
`test_workflow_telemetry.py` (synthetic read-only SQLite projections, compressed
events, usage/cost coverage, conservative delivery association, mirror timing,
workflow hints, privacy and failed-collection preservation) and
`test_coaching_evals.py` (12 synthetic coaching cases, independent negative
controls, dose/availability/source checks, missing reviews and response-bound
review hashes). See [operation and interpretation](../examples/agentic/openclaw/TELEMETRY_AND_EVALS.md).
Those tests validate the instrumentation and evaluation machinery; they do not
establish the quality of current production model answers or provider billing.

`test_report_runner.py` covers the private report supervisor with synthetic model
envelopes, Telegram acknowledgements and clocks: attempt/deadline caps, cached
delivery retry, unknown outcome holds, source changes during generation, expiry,
deduplication, legacy IDs, queues, exact destinations and credential filtering.
`test_openclaw_context_tool.py` runs the Node typed-tool/manifest/authority tests.
These test orchestration, not live model judgments or actual Telegram delivery.
See [bounded execution](../examples/agentic/openclaw/EXECUTION_RELIABILITY.md).

`test_model_efficiency.py` covers lossless prompt ordering, fixed private report
workspaces, model/effort/auth preservation, zero-tool benchmark envelopes,
unknown-slot suppression, original-answer review hashes, experiment provenance,
benefit/expiry/repetition gates, optional wearables, complex-case fallback and
bounded source-based memory/config construction. These checks do not simulate a
human quality review or establish production token/cost savings. See
[primary efficiency policy](../examples/agentic/openclaw/MODEL_EFFICIENCY.md).

`test_coaching_runtime.py`, `test_managed_weekly_reports.py` and
`test_openclaw_coaching_tool.py` cover server-owned review captures, current feedback,
plan/review persistence and retrieval, safety/source revalidation, idempotency,
quiet reviews, save-before-delivery ordering and bounded typed-tool transport.
These tests use isolated stores and synthetic sources, not real athlete plans or
live model judgments. The Node wrapper also checks explicit nested schema shapes.
Set SECTION11_OPENCLAW_PACKAGE to the installed OpenClaw package root to exercise
its actual compatibility conversion and validator (otherwise that native check is
explicitly skipped). Run the same native check directly with
`node dev/openclaw_coaching_schema_smoke.mjs /path/to/openclaw`.
It reproduces the old empty-object failure and checks provider/runtime projections;
registration or direct execute calls alone do not verify schema compatibility. See [managed review integration](../examples/agentic/openclaw/MANAGED_REVIEWS.md).

Long-term training facts and bounded retrieval are covered by
`test_training_history.py` and `test_long_term_context.py`, with typed-tool checks
in `openclaw_context_tool.test.mjs`. See
[history contract](../examples/agentic/openclaw/LONG_TERM_HISTORY.md).

Everything else. No live coaching report generation, and no `sync.py`
surface outside per-endpoint fetch state, HTTP policy, the `history.json` refresh
gate, the completed-session structure and descriptive-fact paths above, the DFA producer paths above, the `--init` and `--update` distribution rules and the `workout_summary` renderer with its report-template field contract. `push.py` write paths are
covered for their transport behaviour and outcome classification only, not for
their broader validation rules or calendar semantics beyond the time cases above. Treat this as focused regression guards, not as
coverage of the repository.

## Route-map format

PNG is the sole route-weather image format. SVG was omitted to avoid a second renderer and compatibility surface. See [Weather Data Source](../SECTION_11.md#weather-data-source) for the map contract and [third-party notices](../THIRD_PARTY_NOTICES.md) for the embedded font.
