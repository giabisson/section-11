#!/usr/bin/env python3
"""Read-only installed-bundle/private-runtime audit; no service calls or setup."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import stat
from datetime import datetime
from pathlib import Path


REQUIRED = ("coaching_plan.py", "coaching_review.py", "coaching_context.py", "coaching_check.py", "workout_validation.py", "push.py")


def check(root, data_dir=None, workspace=None, latest_json=None):
    root = Path(root).expanduser().resolve()
    checks = []
    def add(name, state, detail):
        checks.append({"check": name, "state": state, "detail": detail})
    manifest_path = root / "manifest.json"
    bad = []
    try:
        manifest = json.loads(manifest_path.read_text())["files"]
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("empty manifest")
        for name, entry in manifest.items():
            if not isinstance(entry, dict):
                bad.append("malformed manifest entry")
                continue
            if (not isinstance(name, str) or "\\" in name or ":" in name or any(p in ("", ".", "..") for p in name.split("/"))
                    or Path(name).is_absolute()):
                bad.append("unsafe manifest path")
                continue
            p = root / name
            if not p.resolve().is_relative_to(root) or p.is_symlink() or not p.is_file():
                bad.append(name)
            elif hashlib.sha256(p.read_bytes()).hexdigest() != entry.get("hash"):
                bad.append(name)
        add("manifest_hashes", "fail" if bad else "pass", bad or f"{len(manifest)} installed files match")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        manifest = {}
        add("manifest_hashes", "fail", str(exc))
    required = ["examples/agentic/" + name for name in REQUIRED] + ["examples/workout-library/workout_constraints.json", "examples/workout-library/WORKOUT_REFERENCE.md"]
    missing = [name for name in required if name not in manifest or not (root / name).is_file()]
    if "examples/training_history.py" not in manifest or not (root / "examples/training_history.py").is_file():
        missing.append("examples/training_history.py")
    add("coaching_dependencies", "fail" if missing else "pass", missing or "all runtime modules and matching library/catalog are shipped")
    try:
        catalog = json.loads((root / required[-2]).read_text())
        library = (root / required[-1]).read_bytes()
        matches = catalog["library_sha256"] == hashlib.sha256(library).hexdigest()
        add("workout_catalog", "pass" if matches and len(catalog["templates"]) == 26 and not catalog["not_yet_checked"] else "fail",
            "library hash and all 26 template constraints")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        add("workout_catalog", "fail", str(exc))
    excluded = [name for name in manifest if name.startswith("literature/cycling-training/sources/")
                or Path(name).name.startswith(("coaching_plan.sqlite3", "athlete_intake.sqlite3")) or Path(name).name in {"coaching_plan.lock", "coaching_plan.json", "coaching_decisions.jsonl"}]
    add("private_and_publisher_exclusion", "fail" if excluded else "pass", excluded or "no private store or publisher research copies in distribution")
    add("requests_dependency", "pass" if importlib.util.find_spec("requests") else "unavailable", "calendar transport needs requests; local review/store uses stdlib")
    if latest_json is None:
        add("current_data_contract", "unverified", "no actual latest.json supplied; fictional examples are never athlete data")
    else:
        latest = Path(latest_json).expanduser()
        if latest.name.endswith(".example.json") or "json-examples" in latest.parts:
            add("current_data_contract", "fail", "a fictional schema example cannot verify an athlete runtime")
        else:
            try:
                data = json.loads(latest.read_text())
                stamp = datetime.fromisoformat(data["metadata"]["last_updated"])
                if stamp.tzinfo:
                    stamp = stamp.astimezone()
                present = all(k in data for k in ("readiness_decision", "derived_metrics", "health_context"))
                current = stamp.date() == datetime.now().date()
                add("current_data_contract", "pass" if present and current else "unverified",
                    {"required_blocks_present": present, "dated_today": current, "scope": "shape/freshness only, not data truth or health clearance"})
            except (OSError, ValueError, TypeError, KeyError) as exc:
                add("current_data_contract", "unverified", str(exc))
    if data_dir is None:
        add("private_store", "unverified", "no runtime data directory supplied")
    else:
        directory = Path(data_dir).expanduser()
        database = directory / "coaching_plan.sqlite3"
        if not directory.is_dir() or not database.is_file() or directory.is_symlink() or database.is_symlink():
            add("private_store", "unverified", "no ordinary existing private plan store; nothing was initialized")
        elif stat.S_IMODE(directory.stat().st_mode) & 0o077 or stat.S_IMODE(database.stat().st_mode) & 0o077:
            add("private_store", "fail", "private directory/database permissions required")
        else:
            try:
                with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
                    version = db.execute("PRAGMA user_version").fetchone()[0]
                    integrity = db.execute("PRAGMA quick_check").fetchone()[0]
                    initialized = db.execute("SELECT count(*) FROM identity").fetchone()[0] == 1
                    add("private_store", "pass" if version == 1 and integrity == "ok" and initialized else "fail", "read-only version/identity/integrity check; no personal contents printed")
            except sqlite3.Error as exc:
                add("private_store", "fail", str(exc))
    executable = shutil.which("openclaw")
    add("openclaw_executable", "present_unverified" if executable else "unverified", "found on PATH; not executed" if executable else "not found here; remote deployments may differ")
    if workspace is not None:
        folder = Path(workspace).expanduser()
        names = [name for name in ("AGENTS.md", "HEARTBEAT.md", "SKILL.md") if (folder / name).is_file()]
        add("runtime_workspace", "present_unverified" if names else "unverified", {"instruction_filenames": names, "scope": "file presence does not prove loading, schedule opt-in or execution"})
    else:
        add("runtime_workspace", "unverified", "no actual agent workspace supplied")
    add("telegram_models_schedule_live_api", "unverified", "requires actual configuration/log evidence; no messages, model calls, calendar writes or schedules were triggered")
    return {"bundle_ready": not any(c["state"] == "fail" for c in checks if c["check"] not in ("private_store",)),
            "live_runtime_verified": False, "checks": checks, "calendar_writes": 0, "messages_sent": 0,
            "scope": "Local artifact/path checks only. Present files and configuration are not proof of live service behavior."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--workspace")
    parser.add_argument("--latest-json")
    args = parser.parse_args()
    result = check(args.install_root, args.data_dir, args.workspace, args.latest_json)
    print(json.dumps(result, indent=2))
    return 0 if result["bundle_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
