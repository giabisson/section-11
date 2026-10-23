#!/usr/bin/env python3
"""Private, versioned coaching plans and journaled calendar publication.

Local propose/show/history require no credentials or HTTP. Publication is an
explicit preview/confirmation operation through the existing push transport.
SQLite is the transactional source of truth; no athlete files go in the repo.
"""
import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import re
import sqlite3
import stat
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


_push_module = None
_review_module = None
_context_module = None
MAX_INPUT_BYTES = 2_000_000


def push_module():
    global _push_module
    if _push_module is None:
        path = Path(__file__).with_name("push.py")
        spec = importlib.util.spec_from_file_location("s11_plan_push", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _push_module = module
    return _push_module


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def today():
    # Plan dates are athlete-local, as in push.py. Configure the process timezone.
    return datetime.now().date().isoformat()


def obj(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"expected fields {sorted(required)}; optional {sorted(optional)}")


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError("expected nonempty text (at most 4000 characters)")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise ValueError("IDs must contain 1–64 ASCII letters/digits/underscores/hyphens")
    return value


def date(value):
    text(value)
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    if parsed.isoformat() != value:
        raise ValueError("dates must use YYYY-MM-DD")
    return parsed


def number(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"expected a finite number >= {minimum}")
    return value


def strings(value, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError("expected a text list")
    for item in value:
        text(item)


def evidence(value):
    if not isinstance(value, list) or not value:
        raise ValueError("at least one explicit evidence reference is required")
    for row in value:
        obj(row, {"source", "as_of", "summary"})
        text(row["source"])
        text(row["summary"])
        if date(row["as_of"]) > date(today()):
            raise ValueError("evidence observation date is in the future")


class PlanStore:
    """One athlete and one continuing plan per explicitly private directory.

    Revisions, prescriptions, previews and journal rows are append-only through
    SQL triggers. A nonblocking process lock serializes mutations including HTTP;
    a committed operation_started row survives a process crash before/after send.
    """

    def __init__(self, directory, create=False):
        self.directory = Path(directory).expanduser().absolute()
        here = Path(__file__).resolve().parent
        if here.name == "agentic" and here.parent.name == "examples":
            if self.directory.resolve().is_relative_to(here.parent.parent):
                raise ValueError("private plan data must live outside the source/update checkout")
        if create:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.directory.is_dir() or self.directory.is_symlink():
            raise ValueError("choose a dedicated private data directory")
        if stat.S_IMODE(self.directory.stat().st_mode) & 0o077:
            raise ValueError("data directory must be private (mode 0700); choose a dedicated folder")
        self.path = self.directory / "coaching_plan.sqlite3"
        self.lock_path = self.directory / "coaching_plan.lock"
        if not create and not self.path.is_file():
            raise ValueError("no plan store exists in this directory")
        for path in (self.path, self.lock_path):
            if path.is_symlink():
                raise ValueError("plan database/lock must not be symlinks")
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise ValueError("plan database/lock must have private permissions")
        self.db = sqlite3.connect(self.path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA recursive_triggers=ON")
        try:
            with self.locked():
                version = self.db.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, 1):
                    raise ValueError("unsupported coaching-plan store version; no migration attempted")
                if version == 0:
                    if not create:
                        raise ValueError("plan store is not initialized")
                    self.db.executescript("""
                        BEGIN IMMEDIATE;
                        CREATE TABLE revisions (id TEXT PRIMARY KEY, body TEXT NOT NULL, request_id TEXT UNIQUE NOT NULL);
                        CREATE TABLE prescriptions (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                        CREATE TABLE previews (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                        CREATE TABLE identity (store_id TEXT PRIMARY KEY);
                        CREATE TABLE journal (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, revision TEXT NOT NULL,
                                              at TEXT NOT NULL, body TEXT NOT NULL);
                        PRAGMA user_version=1;
                    """)
                    self.db.execute("INSERT INTO identity VALUES (?)", (uuid.uuid4().hex,))
                    for table in ("revisions", "prescriptions", "previews", "journal", "identity"):
                        for verb in ("UPDATE", "DELETE"):
                            self.db.execute(f"CREATE TRIGGER immutable_{table}_{verb} BEFORE {verb} ON {table} "
                                            "BEGIN SELECT RAISE(ABORT, 'append-only coaching record'); END")
                    self.db.commit()
                identities = self.db.execute("SELECT store_id FROM identity").fetchall()
                if len(identities) != 1:
                    raise ValueError("store identity is missing or ambiguous; restore a verified backup")
                self.store_id = identities[0][0]
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @contextmanager
    def locked(self):
        with open(self.lock_path, "rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("another plan operation is running; nothing was changed") from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _log(self, kind, revision, body):
        self.db.execute("INSERT INTO journal(kind, revision, at, body) VALUES (?,?,?,?)",
                        (kind, revision, now(), canonical(body)))

    def _read(self, table, key):
        # table is selected only by internal callers, never from external input.
        row = self.db.execute(f"SELECT body FROM {table} WHERE id=?", (key,)).fetchone()
        if row is None:
            raise ValueError(f"unknown {table} identity")
        value = json.loads(row[0])
        prefix = {"revisions": "rev-", "prescriptions": "rx-", "previews": "preview-"}[table]
        if key != prefix + digest(value):
            raise ValueError("stored content hash mismatch; do not publish")
        return value

    def latest_id(self):
        row = self.db.execute("SELECT id FROM revisions ORDER BY rowid DESC LIMIT 1").fetchone()
        return row[0] if row else None

    def _events(self):
        return [dict(row, body=json.loads(row["body"])) for row in self.db.execute("SELECT * FROM journal ORDER BY seq")]

    def pending(self):
        active = {}
        for row in self._events():
            body = row["body"]
            if row["kind"] == "operation_started":
                active[body["operation_id"]] = body
            elif row["kind"] in {"operation_applied", "operation_not_applied"}:
                active.pop(body["operation_id"], None)
        return list(active.values())

    def bindings(self):
        result = {}
        for row in self._events():
            if row["kind"] == "operation_applied":
                body = row["body"]
                action = body["action"]
                sid = action["session_id"]
                if action["kind"] == "delete":
                    result.pop(sid, None)
                else:
                    result[sid] = {"prescription_id": action["prescription_id"], "event_id": body["event_id"],
                                   "verified_at": row["at"], "revision_id": row["revision"]}
        return result

    def prescription(self, prescription_id):
        return self._read("prescriptions", prescription_id)

    def _local_pusher(self):
        # No transport is invoked by local validation; no real key is loaded.
        return push_module().IntervalsPush("0", "offline-validation-only")

    def _validate_plan(self, plan, prescriptions):
        obj(plan, {"schema_version", "planning_policy", "athlete_id", "plan_id", "revision", "goals", "block", "weeks", "sessions"},
            {"detected_phase"})
        if type(plan["schema_version"]) is not int or plan["schema_version"] != 1 or plan["planning_policy"] != "athlete_specific_v1":
            raise ValueError("expected schema 1 and athlete_specific_v1 planning policy")
        identifier(plan["plan_id"])
        if not isinstance(plan["athlete_id"], str) or not re.fullmatch(r"i?[0-9]+", plan["athlete_id"]) or plan["athlete_id"] == "0":
            raise ValueError("use an explicit Intervals.icu athlete ID; alias 0 cannot bind a private store")
        rev = plan["revision"]
        obj(rev, {"request_id", "parent_revision", "reason", "evidence"})
        identifier(rev["request_id"])
        text(rev["reason"])
        evidence(rev["evidence"])
        goals = plan["goals"]
        if not isinstance(goals, list) or not goals:
            raise ValueError("a plan requires a goal; general fitness is valid")
        goal_ids = set()
        for goal in goals:
            obj(goal, {"goal_id", "description", "priority", "date", "demands", "success_measure", "constraints"})
            gid = identifier(goal["goal_id"])
            if gid in goal_ids:
                raise ValueError("duplicate goal_id")
            goal_ids.add(gid)
            text(goal["description"])
            text(goal["success_measure"])
            strings(goal["demands"], True)
            strings(goal["constraints"])
            if goal["priority"] not in ("general", "A", "B", "C"):
                raise ValueError("goal priority must be general/A/B/C")
            if goal["date"] is not None:
                date(goal["date"])
            elif goal["priority"] != "general":
                raise ValueError("event goals require an explicit date")
        block = plan["block"]
        obj(block, {"objective", "goal_ids", "planned_phase", "start_date", "end_date", "starting_evidence",
                    "progression", "recovery", "review_date", "change_conditions"},
            {"event_preparation", "durability_context", "strength_context"})
        for field in ("objective", "planned_phase", "progression", "recovery"):
            text(block[field])
        strings(block["goal_ids"], True)
        if not set(block["goal_ids"]) <= goal_ids:
            raise ValueError("block references an unknown goal")
        start, end = date(block["start_date"]), date(block["end_date"])
        if start > end or date(block["review_date"]) < start:
            raise ValueError("invalid block/review dates")
        evidence(block["starting_evidence"])
        strings(block["change_conditions"], True)
        if plan.get("detected_phase") is not None:
            obj(plan["detected_phase"], {"value", "as_of", "source"})
            text(plan["detected_phase"]["value"])
            evidence([dict(source=plan["detected_phase"]["source"], as_of=plan["detected_phase"]["as_of"], summary="Detected phase observation")])
        if not isinstance(plan["weeks"], list) or not 1 <= len(plan["weeks"]) <= 104:
            raise ValueError("provide 1–104 explicit planning weeks")
        windows, week_limits, date_weeks = {}, {}, {}
        for week in plan["weeks"]:
            obj(week, {"start_date", "weekly_minutes", "session_windows", "intensity_approach", "compromises"})
            monday = date(week["start_date"])
            if monday.weekday() != 0 or monday.isoformat() in week_limits:
                raise ValueError("weeks require unique Monday start dates")
            if monday > end or monday + timedelta(days=6) < start:
                raise ValueError("planning weeks must overlap the block horizon")
            week_limits[monday.isoformat()] = number(week["weekly_minutes"])
            obj(week["intensity_approach"], {"intent", "zone_model", "basis", "rationale"})
            for v in week["intensity_approach"].values():
                text(v)
            strings(week["compromises"])
            if not isinstance(week["session_windows"], list):
                raise ValueError("session_windows must be a list")
            for window in week["session_windows"]:
                obj(window, {"date", "max_minutes"})
                day = date(window["date"])
                if not monday <= day < monday + timedelta(days=7) or not start <= day <= end or window["date"] in windows:
                    raise ValueError("availability dates must be unique, within their week and the block")
                windows[window["date"]] = number(window["max_minutes"])
                date_weeks[window["date"]] = monday.isoformat()
        if not isinstance(plan["sessions"], list) or len(plan["sessions"]) > 1000:
            raise ValueError("sessions must be a list of at most 1000 entries")
        daily, weekly, timed, ids = {}, {}, {}, set()
        for session in plan["sessions"]:
            obj(session, {"session_id", "prescription_id"})
            sid = identifier(session["session_id"])
            if sid in ids:
                raise ValueError("duplicate session_id")
            ids.add(sid)
            rx = prescriptions[session["prescription_id"]]
            if rx["session_id"] != sid:
                raise ValueError("prescription identity belongs to another logical session")
            w = rx["workout"]
            day = w["date"]
            if day not in windows:
                raise ValueError(f"session {sid} has no dated availability window")
            seconds = number(w["duration_minutes"], .001) * 60
            if not math.isclose(seconds, round(seconds), abs_tol=.000001):
                raise ValueError("prescriptions must resolve to whole-second durations")
            minutes = seconds / 60
            if minutes > windows[day] or minutes > rx["session_budget_minutes"]:
                raise ValueError(f"session {sid} exceeds its dated/session time budget")
            daily[day] = daily.get(day, 0) + minutes
            week = date_weeks[day]
            weekly[week] = weekly.get(week, 0) + minutes
            if "time" in w:
                hour, minute = map(int, w["time"].split(":"))
                a, b = hour * 3600 + minute * 60, hour * 3600 + minute * 60 + seconds
                if b > 86400 or any(a < other_b and other_a < b for other_a, other_b in timed.get(day, [])):
                    raise ValueError("explicit session times overlap or cross midnight")
                timed.setdefault(day, []).append((a, b))
        if any(minutes > windows[day] + 1e-9 for day, minutes in daily.items()):
            raise ValueError("combined sessions exceed a dated availability budget")
        if any(minutes > week_limits[week] + 1e-9 for week, minutes in weekly.items()):
            raise ValueError("sessions exceed the weekly availability budget")
        self._context(plan, prescriptions)

    def _context(self, plan, prescriptions):
        global _context_module
        if _context_module is None:
            path = Path(__file__).with_name("coaching_context.py")
            spec = importlib.util.spec_from_file_location("s11_coaching_context", path)
            _context_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_context_module)
        return _context_module.assess(plan["block"], plan["goals"], plan["sessions"], prescriptions, sys.modules[__name__])

    def propose(self, source):
        with self.locked(), self.db:
            return self._propose_locked(source)

    def _propose_locked(self, source):
        # The original request hash makes retries idempotent even when stored
        # sessions have since been normalized to immutable prescription IDs.
        request_hash = digest(source)
        plan = copy.deepcopy(source)
        if len(canonical(plan).encode()) > MAX_INPUT_BYTES:
            raise ValueError("plan exceeds the 2 MB input limit")
        obj(plan, {"schema_version", "planning_policy", "athlete_id", "plan_id", "revision", "goals", "block", "weeks", "sessions"}, {"detected_phase"})
        obj(plan["revision"], {"request_id", "parent_revision", "reason", "evidence"})
        request_id = identifier(plan["revision"]["request_id"])
        prior = self.db.execute("SELECT id FROM revisions WHERE request_id=?", (request_id,)).fetchone()
        if prior:
            stored = self._read("revisions", prior[0])
            if stored["request_hash"] != request_hash:
                raise ValueError("request_id was already used for different content")
            return {"success": True, "revision_id": prior[0], "unchanged": True}
        latest = self.latest_id()
        if plan["revision"]["parent_revision"] != latest:
            raise ValueError("parent_revision is not current; reload before revising")
        old = self._read("revisions", latest)["plan"] if latest else None
        if old and (plan["athlete_id"], plan["plan_id"]) != (old["athlete_id"], old["plan_id"]):
            raise ValueError("this store is bound to a different athlete/plan")
        if not isinstance(plan["sessions"], list):
            raise ValueError("sessions must be a list")
        snapshots, normalized = {}, []
        local = self._local_pusher()
        bound = self.bindings()
        allowed_rx = {s["prescription_id"] for s in old["sessions"]} if old else set()
        # Historical references remain reusable across later revisions.
        for row in self.db.execute("SELECT body FROM revisions"):
            allowed_rx.update(s["prescription_id"] for s in json.loads(row[0])["plan"]["sessions"])
        for session in plan["sessions"]:
            if isinstance(session, dict) and "prescription_id" in session:
                obj(session, {"session_id", "prescription_id"})
                pid = session["prescription_id"]
                if pid not in allowed_rx:
                    raise ValueError("prescription is not part of this plan's history")
                rx = self.prescription(pid)
            else:
                obj(session, {"session_id", "purpose", "alternatives", "session_budget_minutes", "workout"})
                sid = identifier(session["session_id"])
                text(session["purpose"])
                strings(session["alternatives"])
                number(session["session_budget_minutes"], .001)
                w = copy.deepcopy(session["workout"])
                if not isinstance(w, dict) or "external_id" in w:
                    raise ValueError("workout must be an object; external_id is assigned by the plan store")
                obj(w, {"name", "date"}, {"time", "type", "description", "duration_minutes", "tss", "target",
                                        "category", "indoor", "color", "synthetic", "coaching_prescription"})
                if "indoor" in w and type(w["indoor"]) is not bool:
                    raise ValueError("indoor must be boolean")
                if "color" in w:
                    text(w["color"])
                w["external_id"] = "s11-" + digest([self.store_id, plan["athlete_id"], plan["plan_id"], sid])[:32]
                prepared, reports, errors = local._prepare_workouts([w])
                if errors:
                    raise ValueError("; ".join(errors))
                w, report = prepared[0], reports[0]
                if w.get("type", "Ride") in {"Ride", "VirtualRide", "MountainBikeRide", "GravelRide", "EBikeRide"} and report["status"] != "checked":
                    raise ValueError("plan cycling prescriptions require the checked power schema; native-only cycling is not certified")
                if "duration_minutes" not in w:
                    raise ValueError("every prescribed sport needs an explicit complete duration")
                if sid in bound:
                    previous = self.prescription(bound[sid]["prescription_id"])
                    if previous["workout"]["date"] < today():
                        raise ValueError("a published historical session cannot be rewritten; use a new session_id")
                rx = {"session_id": sid, "purpose": session["purpose"], "alternatives": session["alternatives"],
                      "session_budget_minutes": session["session_budget_minutes"], "workout": w, "validation": report}
                pid = "rx-" + digest(rx)
            snapshots[pid] = rx
            normalized.append({"session_id": session["session_id"], "prescription_id": pid})
        plan["sessions"] = normalized
        self._validate_plan(plan, snapshots)
        old_ids = {s["session_id"]: s["prescription_id"] for s in old["sessions"]} if old else {}
        new_ids = {s["session_id"]: s["prescription_id"] for s in normalized}
        affected = sorted(sid for sid in old_ids.keys() | new_ids.keys() if old_ids.get(sid) != new_ids.get(sid))
        body = {"plan": plan, "request_hash": request_hash, "affected_sessions": affected}
        rid = "rev-" + digest(body)
        for pid, rx in snapshots.items():
            self.db.execute("INSERT OR IGNORE INTO prescriptions VALUES (?,?)", (pid, canonical(rx)))
        self.db.execute("INSERT INTO revisions VALUES (?,?,?)", (rid, canonical(body), request_id))
        self._log("proposed", rid, {"parent_revision": latest, "reason": plan["revision"]["reason"], "affected_sessions": affected})
        return {"success": True, "revision_id": rid, "affected_sessions": affected, "state": "proposed"}

    def show(self, revision_id=None):
        rid = revision_id or self.latest_id()
        if rid is None:
            raise ValueError("no plan has been proposed")
        body = self._read("revisions", rid)
        bindings = self.bindings()
        pending = self.pending()
        prescriptions = {}
        statuses = []
        for session in body["plan"]["sessions"]:
            sid, pid = session["session_id"], session["prescription_id"]
            prescriptions[pid] = self.prescription(pid)
            binding = bindings.get(sid)
            uncertain = any(p["action"]["session_id"] == sid for p in pending)
            state = "uncertain" if uncertain else "published" if binding and binding["prescription_id"] == pid else "proposed"
            statuses.append({"session_id": sid, "prescription_id": pid, "state": state, "calendar": binding})
        events = self._events()
        for status in statuses:
            previous = [e for e in events if e["kind"] == "operation_applied"
                        and e["body"]["action"]["prescription_id"] == status["prescription_id"]]
            status["ever_published"] = bool(previous)
            if previous and status["state"] == "proposed":
                status["state"] = "previously_published"
        confirmed = any(e["kind"] == "confirmed" and e["revision"] == rid for e in events)
        selected = {s["session_id"] for s in body["plan"]["sessions"]}
        unwanted = [sid for sid, binding in bindings.items() if sid not in selected
                    and self.prescription(binding["prescription_id"])["workout"]["date"] >= today()]
        complete = all(s["state"] == "published" for s in statuses) and not unwanted
        partial = any(s["state"] == "published" for s in statuses) or bool(unwanted)
        state = ("uncertain" if pending else "published" if confirmed and complete else "partially_published" if confirmed and partial
                 else "confirmed" if confirmed else "proposed")
        return {"success": True, "revision_id": rid, **body, "prescriptions": prescriptions,
                "context_assessment": self._context(body["plan"], prescriptions),
                "is_current": rid == self.latest_id(),
                "publication": {"state": state, "sessions": statuses, "pending_operations": pending,
                                "removed_sessions_still_on_calendar": unwanted,
                                "completion": "not_inferred", "calendar_freshness": "last_verification_only"}}

    def event_history(self, event_id):
        if type(event_id) is not int or event_id <= 0:
            raise ValueError("event_id must be a positive integer")
        versions = []
        for event in self._events():
            if event["kind"] == "operation_applied" and event["body"]["event_id"] == event_id:
                action = event["body"]["action"]
                pid = action["prescription_id"]
                versions.append({"verified_at": event["at"], "revision_id": event["revision"], "kind": action["kind"],
                                 "prescription_id": pid, "prescription": self.prescription(pid) if pid else None})
        return {"success": True, "event_id": event_id, "versions": versions,
                "scope": "Verified publication history, not proof of completion or of intervening external edits. Select the applicable version using the authoritative activity pairing/execution time."}

    def summary(self, revision_id=None):
        result = self.show(revision_id)
        result["prescription_summaries"] = {
            pid: {"session_id": rx["session_id"], "name": rx["workout"]["name"], "date": rx["workout"]["date"],
                  "time": rx["workout"].get("time"), "duration_minutes": rx["workout"]["duration_minutes"],
                  "purpose": rx["purpose"], "session_template": rx["validation"].get("session_template"),
                  "validation_status": rx["validation"]["status"]}
            for pid, rx in result.pop("prescriptions").items()}
        return result

    def history(self, limit=20):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("history limit must be 1–1000")
        rows = self._events()
        return {"success": True, "total_events": len(rows), "events": rows[-limit:]}

    def review(self, source):
        """Atomically persist an observation review and its optional revision.

        Scheduled invocation is opt-in; this method neither schedules nor sends
        messages and never writes to the calendar. The LLM supplies exact choices,
        while local guards check their evidence, identity and concrete effect.
        """
        global _review_module
        if _review_module is None:
            path = Path(__file__).with_name("coaching_review.py")
            spec = importlib.util.spec_from_file_location("s11_coaching_review", path)
            _review_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_review_module)
        if not isinstance(source, dict) or len(canonical(source).encode()) > MAX_INPUT_BYTES:
            raise ValueError("review must be an object within the 2 MB input limit")
        if source.get("trigger") == "scheduled" and source.get("schedule_opt_in") is not True:
            raise ValueError("scheduled reviews require explicit opt-in")
        if source.get("assessed_date") != today():
            raise ValueError("assessed_date must be the local review day")
        semantic = copy.deepcopy(source)
        for field in ("review_id", "parent_revision", "trigger", "schedule_opt_in"):
            semantic.pop(field, None)
        if isinstance(semantic.get("candidate_plan"), dict):
            revision = semantic["candidate_plan"].get("revision", {})
            revision.pop("request_id", None)
            revision.pop("parent_revision", None)
        key = digest(semantic)
        with self.locked(), self.db:
            latest = self.latest_id()
            for event in reversed(self._events()):
                if event["kind"] != "reviewed":
                    continue
                previous = event["body"]
                if previous["review_id"] == source.get("review_id") and previous["semantic_hash"] != key:
                    raise ValueError("review_id already identifies different evidence/decisions")
                if previous["review_id"] == source.get("review_id") and latest not in (previous["parent_revision"], previous["result_revision"]):
                    raise ValueError("review_id was already used for another plan revision")
                if previous["semantic_hash"] == key and latest in (previous["parent_revision"], previous["result_revision"]):
                    return dict(previous["result"], unchanged=True, notify=False)
            if source.get("parent_revision") != latest:
                raise ValueError("review parent is not current; reload before reviewing")
            report = _review_module.assess(self, source, sys.modules[__name__])
            candidate = source["candidate_plan"]
            rid = latest
            if candidate is not None:
                rid = self._propose_locked(candidate)["revision_id"]
            new_plan = self._read("revisions", rid)["plan"]
            old_map = {s["session_id"]: s["prescription_id"] for s in self._read("revisions", latest)["plan"]["sessions"]}
            adjusted = [s["prescription_id"] for s in new_plan["sessions"] if old_map.get(s["session_id"]) != s["prescription_id"]]
            report["guard"]["adjusted_prescriptions"] = adjusted
            report["guard"]["adjustment_actions"] = sorted({d["action"] for d in report["decisions"]})
            actionable = bool(report["unresolved_questions"] or rid != latest or any(d["action"] != "maintain" for d in report["decisions"]))
            notification_key = digest({"questions": report["unresolved_questions"], "decisions": report["decisions"],
                                       "result_revision": rid})
            already_notified = any(e["kind"] == "reviewed" and e["body"].get("notification_key") == notification_key for e in self._events())
            result = {"success": True, "review_id": source["review_id"], "parent_revision": latest,
                      "revision_id": rid, "revision_created": rid != latest, "report": report,
                      "notify": bool(not already_notified and (source["trigger"] == "athlete" or actionable)),
                      "calendar_writes": 0}
            self._log("reviewed", rid, {"review_id": source["review_id"], "semantic_hash": key,
                      "parent_revision": latest, "result_revision": rid, "source": copy.deepcopy(source),
                      "notification_key": notification_key, "result": result})
            return result

    def _review_guard(self, actions):
        current = next((e["body"]["result"]["report"]["guard"] for e in reversed(self._events())
                        if e["kind"] == "reviewed" and e["body"]["result"]["report"]["guard"]["date"] == today()), None)
        if not current:
            return
        for action in actions:
            if action["kind"] == "delete" or action["after"]["start_date_local"][:10] != today():
                continue
            if current["same_day_stop"] or current["same_day_clarification"]:
                raise ValueError("latest review requires a same-day stop or current data/health clarification; deletion remains possible")
            if current["readiness_modify"] and (action["prescription_id"] not in current["adjusted_prescriptions"]
                    or not set(current["adjustment_actions"]) & {"reduce", "substitute"}):
                raise ValueError("morning modification requires an explicitly reviewed adjusted same-day prescription")

    def _bound_pusher(self, plan, pusher):
        if pusher.athlete_id != plan["athlete_id"]:
            raise ValueError("calendar client athlete ID differs from the private plan")

    def _assert_current(self, rid):
        if rid != self.latest_id():
            raise ValueError("only the current plan revision can be published")
        if self.pending():
            raise ValueError("an uncertain/interrupted publication requires reconciliation before another write")

    def _payload(self, action, pusher, old=False):
        return copy.deepcopy(action["before" if old else "after"])

    def _build_action(self, action, pusher):
        before = pusher._build_event(self.prescription(action["previous"]["prescription_id"])["workout"]) if action["previous"] else None
        after = pusher._build_event(self.prescription(action["prescription_id"])["workout"]) if action["prescription_id"] else None
        if before and after:
            for field in before:
                if field not in after:
                    after[field] = None
        return dict(action, before=before, after=after)

    def _check_frozen_action(self, action, pusher):
        built = self._build_action(action, pusher)
        if built["before"] != action["before"] or built["after"] != action["after"]:
            raise ValueError("calendar payload builder changed; obtain a new preview")

    def _check_prescription(self, pid, pusher):
        rx = self.prescription(pid)
        check = pusher.preview_push([rx["workout"]])
        if not check["success"]:
            raise ValueError(check["error"])
        if rx["validation"]["status"] == "checked":
            report = check["coaching_validation"][0]
            if (check["compiled_workouts"][0] != rx["workout"] or any(
                    report.get(k) != rx["validation"].get(k) for k in ("library_sha256", "constraints_sha256", "prescription_sha256"))):
                raise ValueError("checked prescription/catalog changed; propose a reviewed revision")

    def _baseline(self, action, pusher):
        if action["kind"] == "create":
            intended = self._payload(action, pusher)
            day = intended["start_date_local"][:10]
            window = pusher._read_event_window(day, day)
            if not window["success"] or any(str(e.get("external_id")) == intended["external_id"] for e in window.get("events", [])):
                raise ValueError("new event identity is already present or the calendar read failed; reconcile rather than upsert blindly")
            return
        previous = action["previous"]
        if action["before"]["start_date_local"][:10] < today():
            raise ValueError("a historical calendar session cannot be updated or deleted")
        presence = pusher._event_presence(previous["event_id"])
        remote = presence.get("event", {})
        expected = self._payload(action, pusher, old=True)
        if (presence["state"] != "present" or remote.get("id") != previous["event_id"]
                or remote.get("external_id") != expected["external_id"]
                or not pusher._event_matches_intent(remote, expected) or remote.get("paired_activity_id") is not None):
            raise ValueError("managed event changed, disappeared, became paired or could not be verified; no overwrite/delete")

    def preview(self, revision_id, pusher):
        with self.locked():
            self._assert_current(revision_id)
            plan = self._read("revisions", revision_id)["plan"]
            self._bound_pusher(plan, pusher)
            self._validate_plan(plan, {s["prescription_id"]: self.prescription(s["prescription_id"]) for s in plan["sessions"]})
            bindings, actions = self.bindings(), []
            selected = {s["session_id"]: s["prescription_id"] for s in plan["sessions"]}
            for sid, pid in selected.items():
                rx = self.prescription(pid)
                previous = bindings.get(sid)
                if previous and previous["prescription_id"] == pid:
                    continue
                if rx["workout"]["date"] < today():
                    continue  # An unpublished past session creates no catch-up debt.
                if previous and self.prescription(previous["prescription_id"])["workout"]["date"] < today():
                    raise ValueError("cannot repurpose a published historical session_id")
                self._check_prescription(pid, pusher)
                actions.append({"kind": "update" if previous else "create", "session_id": sid,
                                "prescription_id": pid, "previous": previous})
            for sid, previous in bindings.items():
                if sid not in selected and self.prescription(previous["prescription_id"])["workout"]["date"] >= today():
                    actions.append({"kind": "delete", "session_id": sid, "prescription_id": None, "previous": previous})
            actions = [self._build_action(a, pusher) for a in actions]
            self._review_guard(actions)
            for action in actions:
                self._baseline(action, pusher)
            body = {"revision_id": revision_id, "actions": actions, "bindings_hash": digest(bindings),
                    "created_at": now(), "nonce": uuid.uuid4().hex}
            pid = "preview-" + digest(body)
            with self.db:
                self.db.execute("INSERT INTO previews VALUES (?,?)", (pid, canonical(body)))
                self._log("previewed", revision_id, {"preview_id": pid, "actions": actions})
            # Full immutable prescriptions make the proposed changes reviewable.
            return {"success": True, "mode": "preview", "preview_id": pid, **body,
                    "prescriptions": {a["prescription_id"]: self.prescription(a["prescription_id"]) for a in actions if a["prescription_id"]},
                    "message": "No calendar write. Approve this exact preview before publish --confirm."}

    def _observe(self, action, pusher):
        if action["kind"] == "create":
            intended = self._payload(action, pusher)
            day = intended["start_date_local"][:10]
            window = pusher._read_event_window(day, day)
            if not window["success"]:
                return None
            matches = [e for e in window["events"] if str(e.get("external_id")) == intended["external_id"]]
            if len(matches) != 1:
                return None
            remote = matches[0]
        else:
            presence = pusher._event_presence(action["previous"]["event_id"])
            if action["kind"] == "delete":
                return {"event_id": action["previous"]["event_id"]} if presence["state"] == "absent" else None
            if presence["state"] != "present":
                return None
            remote = presence["event"]
            intended = self._payload(action, pusher)
            # Clear only optional fields previously controlled by this prescription.
            for field in self._payload(action, pusher, old=True):
                if field not in intended:
                    intended[field] = None
        event_id = remote.get("id")
        if (type(event_id) is not int or event_id <= 0 or remote.get("external_id") != intended["external_id"]
                or not pusher._event_matches_intent(remote, intended)):
            return None
        if action["kind"] == "update" and event_id != action["previous"]["event_id"]:
            return None
        return {"event_id": event_id}

    def publish(self, preview_id, approval_ref, pusher, confirm=False):
        if confirm is not True:
            raise ValueError("publication requires --confirm after athlete approval of the exact preview")
        text(approval_ref)
        with self.locked():
            preview = self._read("previews", preview_id)
            rid = preview["revision_id"]
            self._assert_current(rid)
            plan = self._read("revisions", rid)["plan"]
            self._bound_pusher(plan, pusher)
            if preview["bindings_hash"] != digest(self.bindings()):
                raise ValueError("publication state changed; request a new preview")
            if any(e["kind"] == "confirmed" and e["body"]["preview_id"] == preview_id for e in self._events()):
                raise ValueError("this preview was already used; do not replay a write")
            self._validate_plan(plan, {s["prescription_id"]: self.prescription(s["prescription_id"]) for s in plan["sessions"]})
            # Validate the full batch and every remote baseline before any write.
            self._review_guard(preview["actions"])
            for action in preview["actions"]:
                self._check_frozen_action(action, pusher)
                if action["kind"] != "delete":
                    self._check_prescription(action["prescription_id"], pusher)
            for action in preview["actions"]:
                self._baseline(action, pusher)
            with self.db:
                self._log("confirmed", rid, {"preview_id": preview_id, "approval_ref": approval_ref,
                                             "source": "caller_attests_athlete_approval"})
            results = []
            for action in preview["actions"]:
                op = {"operation_id": uuid.uuid4().hex, "preview_id": preview_id, "action": action}
                # Recheck immediately before each mutation, including after earlier
                # items changed. A failure here sends nothing for this operation.
                try:
                    self._baseline(action, pusher)
                except ValueError as exc:
                    with self.db:
                        self._log("publication_stopped", rid, {"preview_id": preview_id, "session_id": action["session_id"],
                                                               "state": "not_sent", "reason": str(exc)})
                    results.append({"session_id": action["session_id"], "state": "not_applied", "error": str(exc)})
                    break
                with self.db:
                    self._log("operation_started", rid, op)
                try:
                    if action["kind"] == "create":
                        outcome = pusher.push_workouts([self.prescription(action["prescription_id"])["workout"]])
                    elif action["kind"] == "update":
                        payload = self._payload(action, pusher)
                        for field in self._payload(action, pusher, old=True):
                            if field not in payload:
                                payload[field] = None
                        outcome = pusher._apply_event_update(action["previous"]["event_id"], payload)
                    else:
                        outcome = pusher.delete_event(action["previous"]["event_id"])
                    observed = self._observe(action, pusher) if outcome.get("outcome") != "not_applied" else None
                    state = "applied" if observed else "not_applied" if outcome.get("outcome") == "not_applied" else "unknown"
                except Exception:
                    # A transport/parse failure after the durable start may follow
                    # application. Never classify it as a safe retry.
                    state, observed = "unknown", None
                entry = dict(op, event_id=observed["event_id"] if observed else None)
                with self.db:
                    self._log("operation_" + state, rid, entry)
                results.append({"session_id": action["session_id"], "operation_id": op["operation_id"], "state": state})
                if state != "applied":
                    break  # Do not continue a partly applied/uncertain revision.
            success = len(results) == len(preview["actions"]) and all(r["state"] == "applied" for r in results)
            return {"success": success, "revision_id": rid, "results": results,
                    "outcome": ("applied" if success else "unknown" if self.pending() else "partially_applied"
                                if any(r["state"] == "applied" for r in results) else "not_applied"),
                    "publication": self.show(rid)["publication"]}

    def reconcile(self, pusher):
        with self.locked():
            rid = self.latest_id()
            self._bound_pusher(self._read("revisions", rid)["plan"], pusher)
            results = []
            for op in self.pending():
                observed = self._observe(op["action"], pusher)
                if observed:
                    with self.db:
                        self._log("operation_applied", self._read("previews", op["preview_id"])["revision_id"],
                                  dict(op, event_id=observed["event_id"], reconciled=True))
                results.append({"operation_id": op["operation_id"], "state": "applied" if observed else "unknown"})
            return {"success": not self.pending(), "mode": "read_only_calendar_reconciliation", "results": results,
                    "pending_operations": self.pending()}

    def resolve_not_applied(self, operation_id, evidence_ref, approval_ref, confirm=False):
        """Record an explicit external determination, never infer from absence."""
        if confirm is not True:
            raise ValueError("manual resolution requires --confirm and externally verified evidence")
        text(evidence_ref)
        text(approval_ref)
        with self.locked(), self.db:
            op = next((p for p in self.pending() if p["operation_id"] == operation_id), None)
            if op is None:
                raise ValueError("operation is not unresolved")
            rid = self._read("previews", op["preview_id"])["revision_id"]
            self._log("operation_not_applied", rid, dict(op, evidence_ref=evidence_ref, approval_ref=approval_ref,
                      source="caller_attests_external_determination_not_independently_verified"))
        return {"success": True, "operation_id": operation_id, "state": "not_applied", "calendar_writes": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, help="dedicated private directory outside the source checkout")
    parser.add_argument("--credentials-dir", help="Absolute private sync-data directory, separate from the managed-plan store")
    parser.add_argument("--athlete-id")
    parser.add_argument("--api-key")
    sub = parser.add_subparsers(dest="command", required=True)
    propose = sub.add_parser("propose")
    propose.add_argument("--json", required=True)
    show = sub.add_parser("show")
    show.add_argument("--revision")
    show.add_argument("--prescription-id")
    show.add_argument("--event-id", type=int)
    show.add_argument("--compact", action="store_true", help="current/revision intent plus session summaries, without full steps")
    history = sub.add_parser("history")
    history.add_argument("--limit", type=int, default=20)
    review = sub.add_parser("review")
    review.add_argument("--json", required=True, help="dated observation snapshot, decisions and optional concrete revision")
    preview = sub.add_parser("preview")
    preview.add_argument("--revision", required=True)
    publish = sub.add_parser("publish")
    publish.add_argument("--preview", required=True)
    publish.add_argument("--approval-ref", required=True)
    publish.add_argument("--confirm", action="store_true")
    sub.add_parser("reconcile")
    resolve = sub.add_parser("resolve-not-applied")
    resolve.add_argument("--operation-id", required=True)
    resolve.add_argument("--evidence-ref", required=True)
    resolve.add_argument("--approval-ref", required=True)
    resolve.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    store = None
    try:
        store = PlanStore(args.data_dir, create=args.command == "propose")
        if args.command in ("propose", "review"):
            path = Path(args.json)
            if path.stat().st_size > MAX_INPUT_BYTES:
                raise ValueError("plan exceeds the 2 MB input limit")
            source = json.loads(path.read_text())
            result = store.propose(source) if args.command == "propose" else store.review(source)
        elif args.command == "show":
            if sum(v is not None for v in (args.prescription_id, args.event_id, args.revision)) > 1:
                raise ValueError("select a revision, prescription or event history, not several")
            if args.compact and (args.event_id is not None or args.prescription_id is not None):
                raise ValueError("--compact applies to a plan/revision view")
            result = (store.event_history(args.event_id) if args.event_id is not None else store.prescription(args.prescription_id)
                      if args.prescription_id else store.summary(args.revision) if args.compact else store.show(args.revision))
        elif args.command == "history":
            result = store.history(args.limit)
        elif args.command == "resolve-not-applied":
            result = store.resolve_not_applied(args.operation_id, args.evidence_ref, args.approval_ref, args.confirm)
        else:
            module = push_module()
            athlete, key = module._load_credentials(args)
            pusher = module.IntervalsPush(athlete, key)
            if args.command == "preview":
                result = store.preview(args.revision, pusher)
            elif args.command == "publish":
                result = store.publish(args.preview, args.approval_ref, pusher, args.confirm)
            else:
                result = store.reconcile(pusher)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result.get("success", True) else 1
    except (ValueError, TypeError, KeyError, OverflowError, OSError, sqlite3.Error) as exc:
        # A started operation, if any, remains pending even on disk-write failure.
        result = {"success": False, "error": str(exc)}
        if store:
            try:
                if store.pending():
                    result.update(outcome="unknown", reconciliation_required=True)
            except sqlite3.Error:
                result.update(outcome="unknown", reconciliation_required=True)
        print(json.dumps(result))
        return 1
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
