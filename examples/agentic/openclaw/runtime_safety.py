#!/usr/bin/env python3
"""Private OpenClaw delivery audit and interactive Intervals.icu key replacement.

No model calls, Telegram sends, calendar writes, or transcript deletion.
"""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile
from urllib import error, parse, request


class CredentialError(ValueError):
    """Fixed public diagnostics; never include provider bodies or user input."""

    def __init__(self, code, message, http_status=None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def private_file(path):
    path = Path(path).expanduser()
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise ValueError("Expected a private ordinary file owned by the current user")
    return path


def atomic_private(path, text):
    path = Path(path)
    if path.exists() or path.is_symlink():
        private_file(path)
    fd, temporary = tempfile.mkstemp(prefix=".section11-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def telegram_get(token, method, **params):
    # Never return provider errors: exception strings can contain the token URL.
    url = "https://api.telegram.org/bot" + token + "/" + method
    if params:
        url += "?" + parse.urlencode(params)
    try:
        with request.urlopen(url, timeout=15) as response:
            body = json.load(response)
        return body if isinstance(body, dict) else {"ok": False, "reason": "invalid_response"}
    except error.HTTPError as exc:
        return {"ok": False, "reason": "http_error", "http_status": exc.code}
    except Exception:
        return {"ok": False, "reason": "transport_or_response_error"}


def audit(config_path, data_dir, report_profile=None):
    config_path = private_file(config_path)
    config = json.loads(config_path.read_text())
    credentials = private_file(Path(data_dir) / ".sync_config.json")
    # Shape validation only; neither identity nor credential values are emitted.
    source = json.loads(credentials.read_text())
    if not isinstance(source.get("intervals_key"), str) or not source["intervals_key"]:
        raise ValueError("No usable Intervals.icu credential")
    channel = config.get("channels", {}).get("telegram", {})
    token = channel.get("botToken")
    if not isinstance(token, str) or not token:
        raise ValueError("Audit requires the configured Telegram bot credential")
    identity = telegram_get(token, "getMe")
    supervisor=json.loads(private_file(report_profile).read_text()) if report_profile else None
    if supervisor and Path(supervisor['openclaw_config']).resolve()!=config_path.resolve():
        raise ValueError('Supervisor/config mismatch')
    allowed = {str(v).removeprefix("telegram:").removeprefix("tg:") for v in channel.get("allowFrom", [])}
    jobs = []
    database = config_path.parent / "state/openclaw.sqlite"
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        for name, raw, state_raw in db.execute("SELECT name,job_json,state_json FROM cron_jobs"):
            if name not in {"morning-readiness", "weekly-review"}:
                continue
            job, state = json.loads(raw), json.loads(state_raw or "{}")
            delivery = job.get("delivery", {})
            destination = delivery.get("to")
            supervised=False
            if supervisor:
                operation={'morning-readiness':'morning','weekly-review':'weekly'}[name]
                expected=['/usr/bin/python3',str(Path(report_profile).resolve().parent/'report_runner.py'),'--profile',str(Path(report_profile).resolve()),operation]
                payload=job.get('payload',{})
                supervised=(payload.get('kind')=='command' and payload.get('argv')==expected and delivery.get('mode')=='none'
                            and str(identity.get('result',{}).get('id'))==supervisor.get('bot_id'))
                if supervised:destination=supervisor['target']
            accessible = telegram_get(token, "getChat", chat_id=destination) if destination else {"ok": False}
            jobs.append({"name": name, "enabled": job.get("enabled"),
                         "target_is_allowlisted": str(destination) in allowed,
                         "bot_can_access_chat": accessible.get("ok") is True,
                         "chat_type": accessible.get("result", {}).get("type"),
                         "scheduler_status": state.get("lastStatus"),
                         "generation_status": None if supervised else state.get("lastStatus"),
                         "delivery_status": 'see_supervisor_ledger' if supervised else state.get("lastDeliveryStatus"),
                         "delivery_error_present": bool(state.get("lastDeliveryError")),
                         "delivery_owner": 'report_supervisor' if supervised else 'openclaw_scheduler',
                         "required_delivery": supervised or (delivery.get('mode')=='announce' and delivery.get("bestEffort") is False)})
    ready = identity.get("ok") is True and len(jobs) == 2 and all(j["bot_can_access_chat"] and j["target_is_allowlisted"] and j["required_delivery"] for j in jobs)
    return {"routing_ready": ready, "bot_identity_verified": identity.get("ok") is True, "credentials_private": True,
            "jobs": jobs, "messages_sent": 0, "model_calls": 0, "calendar_writes": 0,
            "scope": "Current bot/target access and stored generation/delivery states; getChat does not prove a message was delivered."}


def verify_intervals_key(athlete, key):
    if not isinstance(athlete, str) or not re.fullmatch(r"i?[0-9]+", athlete) or athlete == "0":
        raise CredentialError("invalid_athlete_id", "An explicit athlete ID is required.")
    auth = base64.b64encode(("API_KEY:" + key).encode()).decode()
    req = request.Request("https://intervals.icu/api/v1/athlete/" + athlete,
                          headers={"Authorization": "Basic " + auth, "Accept": "application/json",
                                   "User-Agent": "Section11/1.0"})
    try:
        with request.urlopen(req, timeout=20) as response:
            body = json.load(response)
        if not isinstance(body, dict) or str(body.get("id")) != athlete:
            raise CredentialError("athlete_mismatch", "The response did not verify the configured athlete. Check that the key belongs to the intended account.")
    except CredentialError:
        raise
    except error.HTTPError as exc:
        raise CredentialError("intervals_http_error", "Intervals.icu rejected the verification request. Check the HTTP status and account API key.", exc.code) from None
    except ValueError:
        raise CredentialError("invalid_response", "Intervals.icu returned an unreadable verification response; no files were changed.") from None
    except Exception:
        raise CredentialError("verification_unavailable", "Could not reach Intervals.icu for verification; retry later. No files were changed.") from None


def replace_key(data_dir, extra_env_files=()):
    config_path = private_file(Path(data_dir) / ".sync_config.json")
    config = json.loads(config_path.read_text())
    old = config.get("intervals_key")
    if not isinstance(old, str) or not old:
        raise ValueError("No existing Intervals.icu credential")
    # Inspect all consumers before prompting or changing any file.
    extras = []
    for name in extra_env_files:
        path = private_file(name)
        text = path.read_text()
        extras.append((path, text))
    new = getpass.getpass("New Intervals.icu API key (hidden): ").strip()
    repeated = getpass.getpass("Repeat new key (hidden): ").strip()
    if not new or any(c.isspace() for c in new):
        raise CredentialError("invalid_key_input", "Paste a nonempty API key without internal whitespace.")
    if new != repeated:
        raise CredentialError("key_input_mismatch", "The two hidden entries did not match; retry the command.")
    if new == old:
        raise CredentialError("unchanged_key", "The entered key matches the configured old key. Use the newly generated API key.")
    if any(old not in text and new not in text for _, text in extras):
        raise CredentialError("consumer_mismatch", "A supplied consumer contains neither credential; resolve the mismatch first.")
    verify_intervals_key(config.get("athlete_id"), new)
    config["intervals_key"] = new
    # Validation precedes every replacement. Each file is replaced atomically;
    # this is not a cross-file transaction. A partial failure requires repair.
    updated = 0
    try:
        for path, text in extras:
            atomic_private(path, text.replace(old, new))
            updated += 1
        atomic_private(config_path, json.dumps(config, indent=2) + "\n")
        updated += 1
    except Exception:
        raise ValueError(f"Credential replacement interrupted after {updated} files; repair remaining consumers before relying on sync") from None
    return {"success": True, "consumer_files_updated": updated, "new_key_verified": True,
            "calendar_writes": 0, "messages_sent": 0,
            "old_key_revoked": "Must be established by regeneration/revocation in Intervals.icu Settings; this tool does not revoke keys."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("audit")
    check.add_argument("--config", required=True)
    check.add_argument("--data-dir", required=True)
    check.add_argument("--report-profile", help="Explicit private profile for supervised report jobs")
    rotate = commands.add_parser("replace-key", help="Hidden terminal input only; regenerate/revoke the old key in Intervals.icu first")
    rotate.add_argument("--data-dir", required=True)
    rotate.add_argument("--extra-env-file", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.command == "replace-key" and not sys.stdin.isatty():
            raise ValueError("Hidden input requires a terminal; use ssh -t")
        result = audit(args.config, args.data_dir, args.report_profile) if args.command == "audit" else replace_key(args.data_dir, args.extra_env_file)
        print(json.dumps(result, indent=2))
        return 0
    except CredentialError as exc:
        result = {"success": False, "error_code": exc.code, "error": str(exc)}
        if exc.http_status is not None:
            result["http_status"] = exc.http_status
        print(json.dumps(result))
        return 1
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError):
        # JSON parse and file/network errors can contain credential-bearing text.
        print(json.dumps({"success": False, "error": "Runtime safety operation failed; check private paths, permissions, consumer consistency and account access. No credential values are printed."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
