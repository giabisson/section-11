#!/usr/bin/env python3
"""Read-only OpenClaw SQLite telemetry. No network, model calls or chat content output.

Adapter for the 2026.10.6 active-transcript schema. Unsupported schemas fail
explicitly; the previous successful snapshot is preserved. Not a billing meter.
"""
import argparse
from collections import Counter
import ctypes
import ctypes.util
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import sqlite3
import statistics
import sys
import tempfile
import time

MAX_EVENTS = 50000
MAX_FRAME = 16_000_000
JOBS = {"morning-readiness": "morning_readiness", "weekly-review": "weekly_review"}
TOOLS = {"read", "write", "edit", "exec", "process", "apply_patch", "memory_search",
         "memory_get", "web_search", "web_fetch", "browser", "message", "sessions_spawn",
         "sessions_send", "session_status", "cron", "image"}
STATUSES = {"ok", "error", "skipped", "running", "success", "aborted"}
DELIVERY = {"delivered", "not-delivered", "not-requested", "unknown"}


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def identifier(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:24]


def timestamp(value):
    if number(value) is not None:
        return int(value)  # OpenClaw DB/message numeric timestamps are milliseconds.
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000) if dt.tzinfo else None
        except ValueError:
            pass
    return None


def label(value):
    # Only provider/model metadata, never text, arguments, paths or destinations.
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value) else "unknown"


class Decoder:
    def __init__(self):
        self.zstd = None

    def __call__(self, raw, blob):
        if raw is None:
            if self.zstd is None:
                self.zstd = ctypes.CDLL(ctypes.util.find_library("zstd") or "libzstd.so.1")
                self.zstd.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                self.zstd.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
                self.zstd.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
                self.zstd.ZSTD_decompress.restype = ctypes.c_size_t
                self.zstd.ZSTD_isError.argtypes = [ctypes.c_size_t]
                self.zstd.ZSTD_isError.restype = ctypes.c_uint
            if not blob or len(blob) > MAX_FRAME:
                raise ValueError("invalid_frame")
            size = self.zstd.ZSTD_getFrameContentSize(blob, len(blob))
            if not 0 < size <= MAX_FRAME:
                raise ValueError("invalid_frame_size")
            target = ctypes.create_string_buffer(size)
            written = self.zstd.ZSTD_decompress(target, size, blob, len(blob))
            if self.zstd.ZSTD_isError(written) or written != size:
                raise ValueError("invalid_frame_data")
            raw = target.raw[:written]
        if len(raw) > MAX_FRAME:
            raise ValueError("oversized_event")
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("invalid_event")
        return event


def readonly(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    db.execute("PRAGMA query_only=ON")
    db.execute("BEGIN")
    return db


def enum(value, choices):
    return value if isinstance(value, str) and value in choices else "unknown"


def invocation(command, script):
    """Recognize ordinary CLI forms; never execute/evaluate shell expressions."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None, []
    for i, token in enumerate(tokens):
        if Path(token).name != script:
            continue
        args = tokens[i + 1:]
        j = 0
        while j < len(args):
            if args[j] == "--data-dir":
                j += 2
            elif args[j].startswith("--data-dir="):
                j += 1
            else:
                return args[j], args
    return None, []


def state_records(db, since, now):
    jobs, states = {}, {}
    for job, name, raw in db.execute("SELECT job_id,name,state_json FROM cron_jobs"):
        if name in JOBS:
            jobs[job] = JOBS[name]
            states[job] = json.loads(raw or "{}")
    receipts = []
    rows = db.execute("SELECT receipt_id,job_id,status,started_at_ms,finished_at_ms,delivery_attempt_state FROM cron_run_receipts WHERE started_at_ms>=? AND started_at_ms<=? ORDER BY started_at_ms LIMIT ?", (since, now, MAX_EVENTS + 1)).fetchall()
    if len(rows) > MAX_EVENTS:
        raise ValueError("receipt_limit")
    for rid, job, status, start, end, attempt in rows:
        if job not in jobs:
            continue
        state = states[job]
        latest = state.get("lastRunAtMs") == start
        delivered = enum(state.get("lastDeliveryStatus"), DELIVERY) if latest else "unknown"
        receipts.append({"receipt_id": identifier(rid), "job_key": identifier(job), "workflow": jobs[job],
                         "started_at_ms": start, "finished_at_ms": end,
                         "wall_ms": end - start if number(end) is not None and end >= start else None,
                         "generation_status": enum(status, STATUSES),
                         "delivery_status": delivered,
                         "delivery_source": "matching_latest_job_state" if latest else "unavailable",
                         "delivery_attempt_state": enum(attempt, {"unknown", "queued", "started", "completed", "failed"})})
    return jobs, receipts


def workflow(key, channel, jobs):
    for job, name in jobs.items():
        if re.search(r"(?:^|:)cron:" + re.escape(job) + r"(?::|$)", key):
            return name, identifier(job)
    return ("telegram" if channel == "telegram" or ":telegram:" in key else "other"), None


def new_run(sid, seq, stamp, group, job, partial):
    return {"run_id": identifier(f"{sid}:{seq}"), "workflow": group, "origin": group,
            "workflow_basis": "scheduled_session" if job else "session_channel", "job_key": job,
            "started_at_ms": stamp, "last_observed_at_ms": stamp, "partial_start": partial,
            "model_responses": 0, "models": Counter(), "tokens": Counter(),
            "usage_complete_responses": 0, "cost_positive_responses": 0,
            "reported_positive_cost_sum": 0, "cost_unknown_or_zero_responses": 0,
            "tools": Counter(), "operation_signals": Counter(), "tool_results": 0,
            "tool_errors": 0, "model_errors": 0, "truncation_signals": 0, "persisted_details_truncations": 0,
            "tool_result_chars": 0, "compactions": 0,
            "final_text_present": False, "last_assistant_terminal": False}


def observe(run, event, stamp):
    if "compact" in str(event.get("type", "")).lower() or "compact" in str(event.get("customType", "")).lower():
        run["compactions"] += 1
    msg = event.get("message", {})
    if not isinstance(msg, dict):
        return
    role = msg.get("role")
    if role == "assistant" and (msg.get("provider") == "openclaw" or msg.get("openclawDeliveryMirror")):
        return
    if role in ("user", "assistant", "toolResult"):
        run["last_observed_at_ms"] = max(stamp, run["last_observed_at_ms"])
    parts = msg.get("content", [])
    parts = parts if isinstance(parts, list) else []
    if role == "assistant" and msg.get("provider") != "openclaw" and not msg.get("openclawDeliveryMirror"):
        usage = msg.get("usage")
        # Includes zero-usage failed attempts; excludes synthetic/delivery messages.
        if msg.get("provider") and msg.get("model"):
            run["model_responses"] += 1
            run["models"][label(msg["provider"]) + "/" + label(msg["model"])] += 1
            usage = usage if isinstance(usage, dict) else {}
            fields = ("input", "output", "cacheRead", "cacheWrite", "totalTokens")
            for field in fields:
                value = number(usage.get(field))
                if value is not None:
                    run["tokens"][field] += value
                    run["tokens"][field + "_observed_responses"] += 1
            run["usage_complete_responses"] += int(all(number(usage.get(k)) is not None for k in fields[:4]))
            cost = usage.get("cost", {})
            total = number(cost.get("total")) if isinstance(cost, dict) else None
            if total is not None and total > 0:
                run["reported_positive_cost_sum"] += total
                run["cost_positive_responses"] += 1
            else:
                run["cost_unknown_or_zero_responses"] += 1
        failed = msg.get("stopReason") in ("error", "aborted")
        run["model_errors"] += int(failed)
        calls = [p for p in parts if isinstance(p, dict) and p.get("type") in ("toolCall", "tool_use")]
        terminal = not calls and (failed or any(p.get("type") == "text" and str(p.get("text", "")).strip() for p in parts if isinstance(p, dict)))
        run["last_assistant_terminal"] = terminal
        run["final_text_present"] = terminal and not failed
        for call in calls:
            name = call.get("name")
            run["tools"][name if name in TOOLS else "other"] += 1
            args = call.get("arguments", call.get("input", {}))
            # Invocation hints only; never a success claim. No arguments persisted.
            command = args.get("command", "") if isinstance(args, dict) else ""
            if isinstance(command, str):
                action, argv = invocation(command, "push.py")
                if action in ("push", "move", "delete", "annotate", "set-threshold"):
                    run["operation_signals"]["calendar_write_attempt" if "--confirm" in argv else "calendar_preview_command"] += 1
                action, _ = invocation(command, "coaching_plan.py")
                if action in ("propose", "review"):
                    run["operation_signals"]["plan_tool_attempt"] += 1
                if invocation(command, "pull.py")[0] is not None or "workout-review-streams" in command:
                    run["operation_signals"]["workout_analysis_tool"] += 1
    elif role == "toolResult":
        run["tool_results"] += 1
        text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))
        if isinstance(msg.get("content"), str):
            text = msg["content"]
        run["tool_result_chars"] += len(text)
        details = msg.get("details", {})
        details = details if isinstance(details, dict) else {}
        exit_code = details.get("exitCode")
        run["tool_errors"] += int(msg.get("isError") is True or (type(exit_code) is int and exit_code != 0) or details.get("status") in ("error", "failed"))
        run["persisted_details_truncations"] += int(bool(details.get("persistedDetailsTruncated")))
        truncation = details.get("truncation", {})
        structured_truncation = isinstance(truncation, dict) and truncation.get("truncated") is True
        run["truncation_signals"] += int(structured_truncation or bool(re.search(r"output truncated|content truncated|truncated to|showing lines \d|exceeds .{0,30}(?:limit|maximum)", text, re.I)))


def finish(run):
    if run["workflow"] in ("telegram", "other"):
        if run["operation_signals"].get("plan_tool_attempt"):
            run.update(workflow="training_plan_attempt", workflow_basis="tool_invocation")
        elif run["operation_signals"].get("calendar_write_attempt") or run["operation_signals"].get("calendar_preview_command"):
            run.update(workflow="calendar_change_attempt", workflow_basis="tool_invocation")
    run["observed_wall_ms"] = run["last_observed_at_ms"] - run["started_at_ms"]
    run["wall_complete"] = run.pop("last_assistant_terminal") and not run["partial_start"]
    run["delivery_status"] = "unknown"
    run["generation_status"] = "unknown"
    run["receipt_link"] = "unmatched"
    run["reported_cost_total"] = run["reported_positive_cost_sum"] if run["model_responses"] and run["cost_unknown_or_zero_responses"] == 0 else None
    run["input_including_cache_tokens"] = sum(run["tokens"].get(k, 0) for k in ("input", "cacheRead", "cacheWrite")) if run["model_responses"] and run["usage_complete_responses"] == run["model_responses"] else None
    run["quality_assessment"] = "not_graded"
    for key in ("models", "tokens", "tools", "operation_signals"):
        run[key] = dict(run[key])
    return run


def link_receipts(runs, receipts):
    # Conservative one-to-one time association, never job-name-only matching.
    candidates = {}
    for i, run in enumerate(runs):
        matches = [j for j, r in enumerate(receipts) if run["job_key"] == r["job_key"]
                   and not run["partial_start"] and r["finished_at_ms"] is not None
                   and r["started_at_ms"] - 5000 <= run["started_at_ms"] <= r["finished_at_ms"]
                   and run["last_observed_at_ms"] <= r["finished_at_ms"] + 5000]
        candidates[i] = matches
    use = Counter(j for matches in candidates.values() for j in matches)
    for i, matches in candidates.items():
        if len(matches) == 1 and use[matches[0]] == 1:
            receipt = receipts[matches[0]]
            runs[i].update(receipt_link="unique_time_match", receipt_id=receipt["receipt_id"],
                           generation_status=receipt["generation_status"], delivery_status=receipt["delivery_status"],
                           scheduler_wall_ms=receipt["wall_ms"])


def summarize(runs, receipts):
    groups = {}
    for group in sorted({r["workflow"] for r in runs} | {r["workflow"] for r in receipts}):
        rows = [r for r in runs if r["workflow"] == group]
        calls = sum(r["model_responses"] for r in rows)
        tokens = Counter()
        models = Counter()
        for r in rows:
            tokens.update(r["tokens"])
            models.update(r["models"])
        counts = [r["model_responses"] for r in rows if r["model_responses"]]
        latencies = [r["observed_wall_ms"] for r in rows if r["wall_complete"] and r["model_responses"]]
        costs = [r["reported_cost_total"] for r in rows if r["model_responses"]]
        prompts = [r["input_including_cache_tokens"] for r in rows if r["input_including_cache_tokens"] is not None]
        prompt_total = sum(tokens.get(k, 0) for k in ("input", "cacheRead", "cacheWrite"))
        complete_usage = sum(r["usage_complete_responses"] for r in rows)
        groups[group] = {"observed_turns": len(rows), "model_responses": calls, "models": dict(models),
                         "model_responses_per_model_turn_median": statistics.median(counts) if counts else None,
                         "observed_complete_wall_ms_median": statistics.median(latencies) if latencies else None,
                         "input_including_cache_tokens_per_complete_usage_turn_median": statistics.median(prompts) if prompts else None,
                         "cache_read_fraction": tokens.get("cacheRead", 0) / prompt_total if prompt_total and complete_usage == calls else None,
                         "tokens": dict(tokens), "usage_complete_responses": complete_usage,
                         "reported_cost_total": sum(costs) if costs and all(c is not None for c in costs) else None,
                         "cost_unknown_or_zero_responses": sum(r["cost_unknown_or_zero_responses"] for r in rows),
                         "tool_errors": sum(r["tool_errors"] for r in rows), "model_errors": sum(r["model_errors"] for r in rows),
                         "truncation_signals": sum(r["truncation_signals"] for r in rows),
                         "persisted_details_truncations": sum(r["persisted_details_truncations"] for r in rows),
                         "partial_turns": sum(r["partial_start"] for r in rows),
                         "receipt_delivery_statuses": dict(Counter(r["delivery_status"] for r in receipts if r["workflow"] == group))}
    return groups


def collect(root, days=14, now_ms=None):
    start = time.monotonic()
    now = int(time.time() * 1000) if now_ms is None else now_ms
    since = now - days * 86400000
    root = Path(root)
    state = readonly(root / "state/openclaw.sqlite")
    agent = readonly(root / "agents/main/agent/openclaw-agent.sqlite")
    try:
        jobs, receipts = state_records(state, since, now)
        windows = {sid: workflow(key or "", channel, jobs) for sid, key, channel in agent.execute("SELECT session_id,session_key,channel FROM session_windows")}
        rows = agent.execute("SELECT t.session_id,t.seq,t.event_json,t.event_zstd,t.created_at FROM transcript_events t JOIN session_transcript_active_events a ON a.session_id=t.session_id AND a.event_seq=t.seq WHERE t.created_at>=? AND t.created_at<=? ORDER BY t.session_id,t.seq LIMIT ?", (since, now, MAX_EVENTS + 1))
        decode, current, runs, scanned = Decoder(), {}, [], 0
        for sid, seq, raw, blob, created in rows:
            scanned += 1
            if scanned > MAX_EVENTS:
                raise ValueError("event_limit")
            event = decode(raw, blob)
            stamp = timestamp(event.get("timestamp")) or timestamp(created)
            if stamp is None:
                raise ValueError("invalid_timestamp")
            msg = event.get("message", {})
            role = msg.get("role") if isinstance(msg, dict) else None
            if role == "assistant" and (msg.get("provider") == "openclaw" or msg.get("openclawDeliveryMirror")):
                continue
            if role == "user" or sid not in current:
                if sid in current:
                    runs.append(finish(current.pop(sid)))
                group, job = windows.get(sid, ("other", None))
                current[sid] = new_run(sid, seq, stamp, group, job, role != "user")
                if role == "user" and not job:
                    parts = msg.get("content", [])
                    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)) if isinstance(parts, list) else ""
                    if "POST_WORKOUT_REPORT_TEMPLATE.md" in text:
                        current[sid].update(workflow="post_workout_review", workflow_basis="explicit_request_marker")
            observe(current[sid], event, stamp)
        runs.extend(finish(r) for r in current.values())
    finally:
        agent.close()
        state.close()
    runs = [r for r in runs if r["model_responses"] or r["tool_results"]]
    link_receipts(runs, receipts)
    return {"schema_version": 1, "truncation_policy_version":2, "collected_at_ms": now, "since_ms": since,
            "collector_elapsed_ms": round((time.monotonic() - start) * 1000),
            "scope": "active_transcript_projection_and_scheduler_receipts",
            "limits": {"not_billing": True, "omits_untranscribed_utility_calls": True,
                       "compacted_or_deleted_history_may_be_absent": True,
                       "zero_cost_is_unknown": True, "tool_success_is_not_delivery": True,
                       "quality_requires_evaluation": True, "separate_source_snapshots": True},
            "coverage": {"events_scanned": scanned, "observed_turns": len(runs), "scheduler_receipts": len(receipts)},
            "workflows": summarize(runs, receipts), "runs": runs, "receipts": receipts}


def private_output(path):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.parent.lstat()
    if path.parent.is_symlink() or not path.parent.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("private_directory_required")
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("private_output_required")
    return path


def supervised_reports(path,since):
    """Separate headless envelopes from main-agent transcripts; never read cache text."""
    result={"source":"report_supervisor_ledger","not_billing":True,"workflows":{}}
    with readonly(path) as db:
        rows=db.execute('SELECT task,state,model_attempts,send_attempts FROM reports WHERE created_ms>=?',(since,)).fetchall()
        for task,state,model_attempts,send_attempts in rows:
            if task not in ('morning','weekly','post_workout'):continue
            out=result['workflows'].setdefault(task,{'reports':0,'states':{},'generation_attempts':0,'delivery_attempts':0,'observed_assistant_turns':0,'assistant_turn_samples':0,'usage':{},'usage_samples':0,'reported_cost_usd':None,'positive_cost_samples':0,'reported_positive_cost_usd_sum':0})
            out['reports']+=1;key=enum(state,{'new','ready','failed','send_failed','delivered','unknown','generating','sending','legacy_seen','expired'})
            out['states'][key]=out['states'].get(key,0)+1
            out['generation_attempts']+=number(model_attempts) or 0;out['delivery_attempts']+=number(send_attempts) or 0
        times={}
        for task,raw in db.execute("SELECT r.task,a.metrics_json FROM attempts a JOIN reports r ON r.id=a.report_id WHERE a.kind='generation' AND a.at_ms>=?",(since,)):
            if task not in result['workflows']:continue
            m=json.loads(raw);out=result['workflows'][task]
            wall=number(m.get('wall_ms'))
            if wall is not None:times.setdefault(task,[]).append(wall)
            for field in ('model','provider'):
                value=m.get(field)
                if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}',value):
                    counts=out.setdefault(field+'_samples',{});counts[value]=counts.get(value,0)+1
            for field,allowed in [('route',{'baseline','reviewed_routine_candidate'}),('requested_thinking',{'off','minimal','low','medium','high','xhigh','max','ultra','adaptive'})]:
                value=m.get(field)
                if isinstance(value,str) and value in allowed:
                    counts=out.setdefault(field+'_samples',{});counts[value]=counts.get(value,0)+1
            calls=number(m.get('tool_calls'))
            if calls is not None:out['observed_tool_calls']=out.get('observed_tool_calls',0)+calls
            turns=number(m.get('assistant_turns'))
            if turns is not None:out['observed_assistant_turns']+=turns;out['assistant_turn_samples']+=1
            cost=number(m.get('reported_cost_usd'))
            if cost is not None and cost>0:out['positive_cost_samples']+=1;out['reported_positive_cost_usd_sum']+=cost
            usage=m.get('usage',{})
            if isinstance(usage,dict) and usage:
                out['usage_samples']+=1
                for k,v in usage.items():
                    if k in ('input','output','total','cacheRead','cacheWrite') and number(v) is not None:out['usage'][k]=out['usage'].get(k,0)+v
    for task,out in result['workflows'].items():
        samples=times.get(task,[])
        out['generation_wall_ms_samples']=len(samples)
        out['generation_wall_ms_median']=statistics.median(samples) if samples else None
        if out['generation_attempts'] and out['positive_cost_samples']==out['generation_attempts']:out['reported_cost_usd']=out['reported_positive_cost_usd_sum']
    return result


def save(path, value):
    path = private_output(path)
    fd, temporary = tempfile.mkstemp(prefix=".telemetry-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openclaw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--days", type=int, choices=range(1, 91), default=14)
    parser.add_argument("--report-state",type=Path,help="Optional private supervisor reports.sqlite; no response text is read")
    args = parser.parse_args()
    status_path = args.output.with_name(args.output.name + ".status.json")
    try:
        private_output(args.output)
        report = collect(args.openclaw_root, args.days)
        if args.report_state:
            report['report_supervisor']=supervised_reports(args.report_state,report['since_ms'])
        save(args.output, report)
        save(status_path, {"ok": True, "last_attempt_at_ms": report["collected_at_ms"], "last_success_at_ms": report["collected_at_ms"]})
        print(json.dumps({"ok": True, "coverage": report["coverage"]}))
        return 0
    except Exception:
        # Even SQLite/JSON exceptions can contain transcript content. Do not log.
        try:
            save(status_path, {"ok": False, "last_attempt_at_ms": int(time.time() * 1000),
                               "error_code": "collection_failed_previous_snapshot_preserved"})
        except Exception:
            pass
        print('{"ok":false,"error_code":"collection_failed_previous_snapshot_preserved"}')
        return 1


if __name__ == "__main__":
    sys.exit(main())
