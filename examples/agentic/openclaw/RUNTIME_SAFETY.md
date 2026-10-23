# OpenClaw delivery and credential protection

This optional integration uses OpenClaw's tool-policy hooks and pre-model tool-result middleware. It does not replace Section 11 or call an LLM. It targets the OpenClaw plugin API inspected in version 2026.10.6; check plugin contracts and runtime registration before enabling it on another version.

## Credential guard

`credential-guard/` is a local, dependency-free plugin using the installed OpenClaw SDK. Explicitly enable it and declare private JSON credential sources. Each source must be an absolute, ordinary file with no group/other permissions. The guard rereads sources on each call so a key replacement takes effect without a stale credential cache.

```json
{
  "plugins": {
    "load": {"paths": ["/private/runtime/credential-guard"]},
    "entries": {
      "section11-credential-guard": {
        "enabled": true,
        "hooks": {"allowConversationAccess": true},
        "config": {
          "credentialFiles": ["/private/athlete/.sync_config.json", "/private/openclaw/openclaw.json"]
        }
      }
    }
  }
}
```

Merge this configuration with existing plugins. Install the plugin in a durable private directory outside the source checkout and agent workspace. Keep a private rollback copy before changing configuration. Validate the proposed OpenClaw configuration and inspect runtime registration; the `plugins validate` authoring command in the inspected version expects tool/feature authoring metadata and does not validate a hook-only plugin.

The guard blocks direct credential-file inspection, recognized shell dumps, symlink aliases to configured sources and tool arguments containing known credentials. Tools such as `push.py` still load their credentials privately. Known JSON credentials, their JSON/URL encodings and Basic-auth forms are removed from OpenClaw-owned tool results before model replay, new transcript records and outbound message text. Unreadable sources block tools or withhold results rather than returning unprotected content. No secret values are logged by this plugin.

This is output protection and an accidental-access guard, **not OS isolation**. Arbitrary host execution, transformed/unknown credentials, binary attachments, direct network egress and Codex-native canonical records need separate runtime restrictions. OpenClaw-owned dynamic tools are the middleware boundary; do not claim coverage of native harness tools merely because a runtime id appears in the manifest. Restrict tool/host access in the execution-hardening step. Historical transcript bytes, backups and already submitted provider context are not rewritten. Rotate exposed credentials; redaction does not revoke them.

The agent must not inspect `.sync_config.json`, `.env`, OpenClaw credentials/configuration, environment dumps or process environments to learn credentials. Use configured tools and report missing access without asking for a key in ordinary chat. A private file with mode 0600 is still readable by unrestricted tools running as the same OS user.

## Read-only delivery audit

```bash
python3 /private/runtime/runtime_safety.py audit \
  --config /private/openclaw/openclaw.json --data-dir /private/athlete
```

The audit reads the existing SQLite cron store in read-only mode, calls Telegram `getMe`/`getChat` and reports destination access without printing bot tokens, chat IDs or athlete data. It reports generation status and delivery status separately. `routing_ready` checks both named report jobs, allowlisted destinations, access and required delivery. It does not prove that a message was delivered or that a scheduled report ran after a repair. Keep historical failure state until a new execution supplies new evidence; never edit it into a success.

Repair delivery through OpenClaw's CLI/API, preserving job payloads, schedules, timezone and model settings. For personal private-chat reports, verify the correct profile's bot, its explicitly allowed recipient and an existing private chat. Do not select a destination simply because another bot can reach it. Use required delivery (`--no-best-effort-deliver`) and verify the saved job after editing. Explicit user authorization is required for delivery-test messages. A direct message receipt verifies that send path; a subsequent scheduled execution must separately establish scheduler delivery. Do not rerun model analysis merely to retry delivery.

## Hidden-input key replacement

Regenerate/revoke each exposed key in Intervals.icu Settings → Developer Settings. This script cannot establish revocation. Inventory all consumers first: Fitbit sync may use the same key in a separate `.env` file. Restrict each consumer file to its owner before replacement.

```bash
ssh -t your-server 'python3 /private/runtime/runtime_safety.py replace-key --data-dir /private/athlete --extra-env-file /private/fitbit/.env'
```

Omit `--extra-env-file` when there is no extra consumer. Enter the new key twice in the hidden terminal prompt, never in chat or command arguments. The tool verifies access to the explicit athlete through a read-only request before changing any consumer, preserves unrelated preferences and atomically replaces each file with mode 0600. Updates across multiple files are not a transaction: interrupted updates require repair. Repeating with the same new key can finish a consumer updated before the main config. Verify both Intervals sync and Fitbit sync afterwards.

Verification sends an explicit application User-Agent: the default Python header was observed receiving HTTP 403 before reaching the authentication check. Expected input and API failures report fixed error codes and, when available, an HTTP status, without provider bodies or entered values. A 403 alone does not establish key revocation. Share only the sanitized result when troubleshooting; never share the key.

Backups and old transcript records remain private until a separately agreed cleanup. Do not delete active OpenClaw SQLite rows manually. A new key, stored only in approved private consumers, is the containment boundary for retained old records.
# Supervised report routing (Step 4)

After the primary [report supervisor](EXECUTION_RELIABILITY.md) is installed,
include `--report-profile /private/report-primary.json` with `audit`. It verifies
that both scheduler commands exactly select that supervisor/profile and that
scheduler fallback delivery is disabled. Bot/allowlist/chat access checks then
use the pinned supervisor destination. `delivery_owner:report_supervisor` means
actual outcomes must be read from its ledger; scheduler success is not model
success or proof of delivery. Without the explicit profile the audit does not
treat disabled scheduler delivery as a ready report route. This read-only audit
sends no messages.
