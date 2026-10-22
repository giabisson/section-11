# Coaching deployment verification

The checkout contains a release candidate, not a deployed Telegram coach. Protocol 11.85, sync 3.150 and push 0.9 carry the coaching changes; the workout library/catalog are 0.9.0. The normal manifest is regenerated for the candidate. `sync.py --init`/`--update` fetch the configured official upstream, so they do not retrieve an unmerged local branch merely because local code changed. No commit, push, deployment, message or real calendar write was performed for these checks.

## What has been checked

- Full developer tests include the coaching contracts and existing sync/push behavior.
- Fresh initialization is replayed using the actual new module/library bytes in a synthetic archive through the real installer. Installed-path imports, local plan persistence and catalog discovery are exercised.
- Update is replayed through the real updater with synthetic HTTP responses and explicit test approval. New runtime dependencies arrive together; private data outside `section11/` remains unchanged.
- Manifest generation includes the runtime modules, library/catalog, policy documents and synthetic examples, and excludes root maintainer code, local publisher research copies and private coaching database/journals. An explicitly listed private/research path is rejected before installation/update.
- Missing dependencies, hash drift and fictional data masquerading as current runtime data fail local checks. No tests connect to Intervals.icu, OpenClaw, Telegram or a model provider.

## Read-only local check

```bash
python3 examples/agentic/coaching_check.py --install-root /path/to/section11
python3 examples/agentic/coaching_check.py --install-root /path/to/section11 --data-dir /private/coaching-data --workspace /actual/agent-workspace --latest-json /actual/training-data/latest.json
```

The command checks manifest hashes, required runtime dependencies, the 26-template catalog binding, distribution exclusions and optionally existing private-store permissions/version/integrity. It can inspect the presence of workspace instruction files and current data shape/date. It does not initialize, migrate, write a plan, call a service, trigger a schedule, print private configuration/athlete contents or send a message. Missing real data is not replaced by examples. `bundle_ready` describes the artifact; `live_runtime_verified` remains false because local paths cannot prove a running service's behavior.

The [saved local result](../json-examples/coaching_check_output.example.json) documents the checked development checkout. The separately authorized server checks below establish more about the existing installation; they do not deploy the candidate or establish its conversational behavior.

## Server verification — 22 October 2026

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

## Remaining live checks

Use actual configuration and existing sanitized logs where possible. Do not copy keys, Telegram tokens or private athlete records into the repository. A test message or calendar write needs explicit authorization; this implementation task did not authorize sending messages to others.

| Check | Required evidence |
|---|---|
| Runtime and persistence | Host/workspaces and candidate cross-process persistence verified; deployment still needs separate durable private stores, explicit athlete/timezone settings and every candidate dependency on the actual execution paths |
| Instruction/context loading | Existing tool references verified; candidate skill/protocol and compact stored plan must be loaded after installation, with prescriptions retrieved selectively and source dates respected |
| Telegram exchange | Historical ingress/tool interaction verified; candidate feedback handling still needs an authorized controlled exchange |
| API/model wiring | Current calendar GETs and configured models verified; fresh candidate model/tool execution, failures and approval boundaries remain untested |
| Reviews | Existing schedules verified; migrate them explicitly to the shared review path, then demonstrate unchanged-data silence and no duplicate revision/message |
| Calendar | Real read-only create previews passed; pairing and any authorized test write still need exact payload, ID retention, null-field, partial-failure and reconciliation verification in a designated test environment |
| Trainer/export | Confirm supported native watts/ramps/cadence and maximal-sprint free-effort mode on the actual trainer/software; local compilation alone cannot establish device behavior |

The [synthetic conversation rubric](../json-examples/coaching_conversations.example.json) lists contrasting budgets, experience, absent wearables, missed sessions, symptoms, event changes and strength tradeoffs. It records that LLM/runtime evaluation is unexecuted and model version unknown. Deterministic replay tests do not substitute for executing those conversations against the configured coach. No token, cost, latency, output-quality score or training-effectiveness result is invented.

## Acceptance boundary

Repository implementation, packaging, server-side tests, cross-process temporary persistence and real calendar read-only previews have passed. **Candidate deployment acceptance remains pending** for instruction loading, a controlled Telegram/model exchange, migrated review execution, remote write semantics and trainer behavior. Those require the later installation and/or separately authorized integration actions. Do not label the candidate deployed or clinically/scientifically validated from passing these checks. Research-access gaps remain in the literature access list.
