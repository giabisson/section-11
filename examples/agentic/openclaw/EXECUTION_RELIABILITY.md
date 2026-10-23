# Bounded primary report execution

Step 4 supervises autonomous morning, weekly and post-workout reports. It does not install the broader coaching release or change the secondary account. Interactive Telegram coaching still runs through the existing Gateway/main agent; these report restrictions are not an OS sandbox for that interactive agent.

## Workflow and authority

Morning/weekly OpenClaw schedules run a fixed argv invoking `report_runner.py`. The existing post-workout detector entry point hands off to `section11-post-primary.service`. A five-minute user timer processes queued requests and eligible known failures, at most one report per invocation. A private nonblocking lock serializes generation/delivery. Busy scheduled requests get small idempotent queue records; no athlete data is queued.

The supervisor builds the fresh Step 3 task packet before any LLM invocation. Its fingerprint ignores source-file hashes, build times, age counters and dossier line numbers, while retaining actual health/readiness, dated evidence, source coverage and stable constraints. Policy/model/template changes invalidate the gate. A delivered report with unchanged evidence is skipped; an already reported activity is never reported again just because later readiness changes. A date alone is not evidence of unchanged physiology across different reporting days.

For a new eligible report, an isolated `openclaw agent exec` invocation receives the current packet and current report template. It inherits the configured main model, utility model, reasoning and credentials; no model/reasoning tuning is performed here. Headless execution intentionally skips workspace bootstrap and does not reuse the long interactive conversation. The prompt carries the task and safety/data policy. Protocol/library/dossier sections and date-filtered history can be retrieved through `section11_context`; unavailable companions or managed-plan records must be disclosed rather than claimed reviewed. This report path cannot fetch arbitrary files, network sources, weather maps, or update a managed plan/calendar. Interactive coaching remains available for those workflows.

The private per-run config allows only `section11_context` globally and for every configured agent. Both Code Mode and automatic Tool Search wrappers are disabled for this run: the installed version otherwise exposes wrapper names (`exec`/`tool_call`) to the policy hook. The plugin uses fixed Python/argv with `shell:false`, explicit operations and operator-selected sources. It enforces 15 seconds, 49,152-byte JSON output and no usable partial packet. A report-mode hook allows at most six context tool calls and blocks all other names. The returned generation envelope must confirm direct mode and only the expected tool names/counts, without unresolved tool failures. A CLI exit code alone is insufficient.

Generation deadlines are 180 seconds for morning/post-workout and 300 seconds for weekly; an outer process-group supervisor adds 40 seconds for startup/cleanup, then TERM/10-second KILL escalation. Command/user-service limits are 420 seconds. Generation stdout is capped at 1 MB; stderr at 64 KB and never published. Global primary agent and shell defaults are explicitly 600/90 seconds, with OpenClaw loop detection enabled. Provider-internal retries are not individually observable or limited by the two-invocation cap; time/tool limits are not a dollar or exact paid-request budget.

## Delivery and retries

The supervisor caches a successful plain-text report privately before sending it. Reports fit one Telegram message (prompt target 3,400 characters, hard cap 4,000 UTF-16 units); irrelevant template metrics are omitted. It rechecks evidence immediately before delivery, holds advice if data changed during generation, and expires pending reports after two hours. Stale/unknown current snapshots require refresh; missing HRV/RHR alone does not cause that failure.

Delivery is a deterministic Telegram Bot API call, outside the LLM. The private profile pins the existing primary bot ID and private destination; the destination must still be allowlisted and `getMe` must match the pinned bot before sending. Only an `ok:true` acknowledgement with a positive message ID and matching chat counts as delivered. Scheduler fallback delivery is disabled to avoid sending supervisor status JSON or duplicating its message. Thus scheduler `not-requested` is expected; consult the supervisor ledger for actual generation/delivery outcomes.

| Outcome | Action |
|---|---|
| Confirmed model failure | Up to two generation invocations per reporting period/activity, at least five minutes apart |
| Confirmed Telegram rejection | Retry cached text, up to three delivery attempts; respect at least five minutes and Telegram `retry_after` |
| Changed evidence before delivery | Discard cached advice; rebuild within the same attempt/expiry limits |
| Transport loss, malformed/partial acknowledgement, killed/inflight operation | Mark unknown; no automatic regeneration or resend |
| Expired report | Hold; do not send an old recommendation late |

No system can infer whether a lost Telegram acknowledgement means the message was delivered. This policy prefers holding an uncertain report over sending duplicates. A crash after generation but before its cache commit also requires reconciliation. SQLite atomic commits provide durable local outcomes, not a distributed transaction with Telegram. Supplied credential values are redacted before submission/cache/send; neither tool policies nor redaction isolate an unrestricted same-user agent from private files.

## Private operator files

Install `report_runner.py`, `reporter_entry.py`, `context_packet.py`, its sibling `athlete_intake.py` and `context-tool/` under the explicit private runtime directory. Enable the plugin through the installed SDK/manifest (`contracts.tools` must declare `section11_context`). Ordinary interactive plugin config has `reportMode:false`; only the private report config enables the restrictive hook. The global coding tool surface includes the bounded context reader.

Create a mode-0600 `report-primary.json` with exactly:

```json
{
  "schema_version":1,
  "state_dir":"/home/ATHLETE/.local/state/section11-runtime/reports-primary",
  "openclaw_config":"/home/ATHLETE/.openclaw/openclaw.json",
  "openclaw_bin":"/absolute/installed/bin/openclaw",
  "context_profile":"/home/ATHLETE/.local/share/section11-runtime/context-primary.json",
  "target":"VERIFIED_PRIVATE_NUMERIC_CHAT_ID",
  "bot_id":"VERIFIED_NUMERIC_BOT_ID",
  "legacy_reported_ids":"/home/ATHLETE/training-data/.reported_activities.json"
}
```

IDs are operator-selected private strings, never model input or a model-selected destination. Initialize once to import existing reported IDs before switching the detector. If no legacy file exists, initialization seeds current recent activities to avoid unsolicited backfill. Keep the original reporter target and all source/job/config/unit backups privately. The old checkout source is not edited. Do not reset the database/reinitialize to recover unknown outcomes; that can erase duplicate protection.

```bash
python3 report_runner.py --profile /private/report-primary.json initialize
python3 report_runner.py --profile /private/report-primary.json morning --dry-run
python3 report_runner.py --profile /private/report-primary.json scan --dry-run
python3 report_runner.py --profile /private/report-primary.json status
python3 runtime_safety.py audit --config /private/openclaw.json --data-dir /private/training-data --report-profile /private/report-primary.json
```

`status` exposes only counts and hashed IDs for uncertain runs. An operator can reconcile one after verifying the original process has stopped and checking the actual private chat/provider records:

```bash
python3 report_runner.py --profile /private/report-primary.json resolve --report-id HASH --outcome delivered --evidence-ref 'Verified original message receipt'
python3 report_runner.py --profile /private/report-primary.json resolve --report-id HASH --outcome not_sent --evidence-ref 'Verified no send and generation process stopped' --confirm-stopped
```

These commands record an operator attestation, not independently verified delivery. They send nothing, do not reset attempt limits/expiry, and cannot declare a nonexistent generated report delivered. Never resolve `not_sent` based solely on the absence of a CLI success code.

The private SQLite ledger stores report text and receipt metadata. Cached text is purged seven days after expiry; operational records are retained 90 days. State directory mode is 0700, files 0600. Keep it outside Git/backups exposed to models. The telemetry collector's optional `--report-state` reads explicit status/count/metric columns only; it never selects cached text. Headless usage/model/provider/turns/tool counts/latency are reported separately from main-agent transcript telemetry to avoid double counting. Missing/zero prices remain unknown. The headless usage field names retain their native semantics; don't blindly merge them with normalized Gateway token fields or call them provider billing.

Tests exercise synthetic timeouts, stale/changed data, lost acknowledgements, cached retries, exact targets, crash recovery, queue/lock behavior and all attempt limits. A headless smoke test verifies actual plugin routing without delivery; it does not establish coaching quality or operating-cost savings. Observe real scheduled outcomes and use the Step 2 answer-bound evaluation process before claiming either.
