# Coaching deployment verification

## Canonical primary deployment policy — 23 October 2026

The user authorized the home-server repository checkout to match the local
working tree from this date onward, including uncommitted changes. Transfer one
tested source snapshot to the primary checkout, keep a private rollback backup,
and verify file hashes after promotion. Do not run the official-upstream updater
over this branch snapshot unless deliberately switching to that upstream release.
Separate installed skill/runtime copies are not implicitly replaced by syncing
the repository. Existing services already pointing at the repository will use
the updated files on their next invocation.

Credentials, OpenClaw/account configuration, athlete data/dossier, plan databases,
report receipts and logs stay outside source control and outside the code parity
contract. Preserve model choices, account identities and existing schedules unless
a task explicitly changes them. The secondary account remains outside the current
deployment scope.

Run `python3 dev/check_primary_parity.py --host home-server` from the canonical
local checkout after each transfer. It compares every tracked/nonignored source
file. Use `--include-runtime` separately to detect drift in installed helper code,
primary skill and shipped units; that option does not install anything. It reads
no private profiles or athlete records. Local uncommitted source changes are
included; parity does not claim those changes have been committed or pushed.

## Current primary deployment — 23 October 2026

The primary implementation is installed and verified: protocol **11.85**, sync
**3.150**, push **0.9** and library/catalog **0.9.0**. The server checkout matches
the canonical working tree; separate runtime helpers and the installed skill were
also hash-checked. The skill is a normal installed copy of the tested distribution,
not a symlink. The distribution contains **201 files**.

| Executed check | Evidence and limit |
|---|---|
| Developer suite | **1,306 tests passed locally and on home-server**; synthetic tests do not establish production model quality |
| OpenClaw loading | Actual SDK/plugin registration, declared typed tool contract, matching eligible skill and configuration validation passed |
| Managed coaching loop | Six isolated native SDK operations saved and recovered one synthetic review; unchanged retry created no duplicate. A fuller synthetic replay exercised managed publication history, paired completion/tolerability, a justified revision and later retrieval |
| Scheduled review integration | Weekly/block supervisor now prepares source evidence and saves a validated review before delivery; three report dry runs passed. Tests cover quiet unchanged reviews and cached-receipt revalidation; no actual athlete block review has run yet |
| History and sync | Primary long-term history service/reader is configured, monthly facts reconciled against API records, and the installed sync completed successfully |
| Preservation | Primary models, account/channel identities and schedules were preserved; the secondary account was not migrated |

The typed `section11_coaching` tool and bounded history reader use the same
explicit private store. Scheduled report agents retain read-only tools; the
supervisor owns the validated save. No new model call is needed solely to save or
retrieve a review. Publication still has separate preview/approval requirements.
Private installation records and rollback material remain on the server.

**Fresh-start cutover remains on hold at the user's request.** A private archive
of **104 coaching-context/old-plan files** has verified hashes and restore
instructions. Active personal context and the current conversation have not been
reset; no new agent was started and no real managed plan was created. The actual
state is `onboarding_required`. Current goals and availability must be collected
through subsequent Telegram onboarding, rather than importing stale plans or
seeding examples. Credentials, training records and the secondary account remain
outside the cutover.

Code deployment is complete for the primary; real-use acceptance remains bounded
by the checks below. The dated 22 October record preserves the earlier candidate
state and is not a description of the current primary installation.

## Historical verification — candidate state on 22 October 2026

The checkout contains a release candidate, not a deployed Telegram coach. Protocol 11.85, sync 3.150 and push 0.9 carry the coaching changes; the workout library/catalog are 0.9.0. The normal manifest is regenerated for the candidate. `sync.py --init`/`--update` fetch the configured official upstream, so they do not retrieve an unmerged local branch merely because local code changed. No commit, push, deployment, message or real calendar write was performed for these checks.

### Candidate checks

- Full developer tests include the coaching contracts and existing sync/push behavior.
- Fresh initialization is replayed using the actual new module/library bytes in a synthetic archive through the real installer. Installed-path imports, local plan persistence and catalog discovery are exercised.
- Update is replayed through the real updater with synthetic HTTP responses and explicit test approval. New runtime dependencies arrive together; private data outside `section11/` remains unchanged.
- Manifest generation includes the runtime modules, library/catalog, policy documents and synthetic examples, and excludes root maintainer code, local publisher research copies and private coaching database/journals. An explicitly listed private/research path is rejected before installation/update.
- Missing dependencies, hash drift and fictional data masquerading as current runtime data fail local checks. No tests connect to Intervals.icu, OpenClaw, Telegram or a model provider.

### Read-only local check

```bash
python3 examples/agentic/coaching_check.py --install-root /path/to/section11
python3 examples/agentic/coaching_check.py --install-root /path/to/section11 --data-dir /private/coaching-data --workspace /actual/agent-workspace --latest-json /actual/training-data/latest.json
```

The command checks manifest hashes, required runtime dependencies, the 26-template catalog binding, distribution exclusions and optionally existing private-store permissions/version/integrity. It can inspect the presence of workspace instruction files and current data shape/date. It does not initialize, migrate, write a plan, call a service, trigger a schedule, print private configuration/athlete contents or send a message. Missing real data is not replaced by examples. `bundle_ready` describes the artifact; `live_runtime_verified` remains false because local paths cannot prove a running service's behavior.

The [saved local result](../json-examples/coaching_check_output.example.json) documents the checked development checkout. The separately authorized server checks below establish more about the existing installation; they do not deploy the candidate or establish its conversational behavior.

### Server verification — 22 October 2026

The user supplied SSH access to `home-server` and authorized a temporary test folder. Candidate files and maintainer tests were copied explicitly from the distribution manifest and `dev/`, excluding publisher research copies and private runtime records. The transferred archive's SHA-256 matched before extraction. All test artifacts remain in `/tmp/section11-coaching-test.nRV5JY4l/`; this is disposable test storage, not a proposed durable deployment location. No live files, schedules or services were changed.

| Executed check | Measured result |
|---|---|
| Server environment | Linux; Python 3.12.3; `requests` available; installed OpenClaw package 2026.10.6 |
| Full developer suite in temporary candidate | **1,119 tests passed in 69.892 seconds**; HTTP remains guarded/mocked by the developer test harness |
| Candidate distribution audit | All **161 manifest files** matched; all 26 workout templates and runtime dependencies present; publisher/private exclusions passed |
| Real current-data contract, both athlete slots | Actual `latest.json` files were dated the check day and contained readiness, derived-metric and health-context blocks; this verifies shape/date, not the truth of every observation |
| Temporary private plan stores, both slots | CLI proposal followed by a separate CLI process recovered the same revision; directory 0700/database 0600; read-only SQLite version/identity/integrity checks passed |
| Candidate managed preview against real calendars | Three synthetic future create-actions per slot previewed successfully; **six GET requests returned HTTP 200** in total. A transport guard rejected every non-GET method. No publication was invoked |

The smoke drafts used fictional training prescriptions, with only the real athlete identity supplied privately to bind each read client. They are not recommendations or a migration of existing plans. Inputs/stores stayed inside the private temporary folder; credentials were read into process memory, never placed in command arguments or copied into the repository. `tests.log`, `audit-primary.json`, `audit-secondary.json` and `smoke-summary.json` remain there for review/cleanup. There were **zero calendar writes, messages or new model calls** during these checks.

Read-only configuration, service and existing transcript inspection established the following:

- Two OpenClaw gateway profiles are running. The primary workspace's instructions reference its `training-data/section11` installation; the two sync services use separate athlete data directories and separate source checkouts through symlinks. Live protocol versions are **11.67 and 11.68**, with producer version **3.132**. The primary installed skill is also 11.67. None of those inspected installation paths contains the new plan module. A candidate copied into `/tmp` cannot change this routing.
- The primary profile currently configures `openai/gpt-6.1-sol`; the secondary profile configures `meta/muse-spark-1.3-contributor`. Recent recorded assistant calls in both profiles used Meta. The primary history also records OpenAI calls. Configuration and historical execution must remain separate evidence; no fresh call verified the newly configured primary model.
- Existing primary state records completed Telegram ingress, Section 11 skill use, and transcript tool calls referring to `latest.json`, the protocol, workout library and push tool. This supports historical Telegram → agent → local data/tool interaction, not candidate instruction loading or successful application of every requested calendar change.
- Both active profiles have morning readiness at 08:00 daily and a weekly review at 20:00 Sunday, configured in `Europe/Rome`, with latest recorded status `ok`. Periodic heartbeat is disabled. Their stored job definitions do **not** reference the new `coaching_plan.py`/`coaching_review.py` path. A successful old job does not establish new review persistence, semantic deduplication or quiet notification behavior. Preserve the existing schedule/timezone until an authorized migration deliberately reconciles it with the athlete's preferences.

Do not update just one checkout and assume the skill, sync services, second profile and schedules follow it. The later installation must explicitly reconcile those paths, choose separate durable private stores, load the candidate instructions and route reviews through the shared implementation. No existing loose plan files were imported, deleted or treated as completed training.

## Remaining real-use checks — 23 October 2026

Keep the fresh-start cutover on hold until the user resumes it. Read-only status
checks and synthetic/native SDK tests do not require a new agent. Do not copy keys,
Telegram tokens or private athlete records into source control. Any external test
message or calendar write must stay within the user's explicit authorization.

| Check | Completed evidence and remaining action |
|---|---|
| Onboarding and real plan | Private archive verified; active context retained. After the hold is lifted, complete the cutover and collect current goals/availability through Telegram before saving a real plan |
| Telegram/model coaching | Plugin/tool transport and synthetic persistence verified. Observe a real model-led exchange using current feedback, optional wearable data and selectively retrieved plan/history |
| Scheduled weekly/block review | Save-before-delivery integration and idempotency/quiet behavior tested. Observe the first actual review with a real plan, validate its rationale, saved record, later retrieval and delivery outcome |
| Calendar | Real read-only create previews passed. Exact live write/null/upsert behavior, pairing, ID retention, partial failures and reconciliation still need a designated authorized integration check |
| Trainer/export | Confirm supported watts/ramps/cadence and maximal-sprint free-effort mode in the actual trainer/software; local compilation alone cannot establish device behavior |
| Model quality and operating cost | Telemetry and repeatable evaluation harness are installed. Complete independent answer review and confirmatory comparisons before enabling cheaper-model routing; do not equate estimates with billing or production savings |

The [synthetic conversation rubric](../json-examples/coaching_conversations.example.json)
remains an unexecuted live-conversation rubric. Later exploratory model experiments
are recorded separately in [the LLM implementation record](../../LLM_UPDATE_PLAN.md);
they do not certify the live coaching loop or training effectiveness.

## Acceptance boundary

Primary code deployment, packaging, server tests, installed instruction/tool loading,
synthetic/native SDK persistence and real calendar read-only previews have passed.
The held onboarding and real-use checks above remain. Do not claim physiological
effectiveness, satisfactory model judgment, verified billing savings, remote write
semantics or trainer compatibility from passing software checks. Research-access
gaps remain in the literature access list. The secondary account remains deferred.
