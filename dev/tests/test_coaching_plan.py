"""Private plan revisions, exact snapshots and crash-safe publication boundaries."""
import copy
import contextlib
import io
import fcntl
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from _harness import REPO_ROOT, RefuseEverything, load_module_by_path

PATH = REPO_ROOT / "examples/agentic/coaching_plan.py"
plans = load_module_by_path("s11_coaching_plan_tests", PATH)
push = plans.push_module()
validator = push._load_workout_validator()
FIXTURE = REPO_ROOT / "examples/json-examples/coaching_plan.example.json"


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 22, 12, tzinfo=tz)


class HttpError(OSError):
    def __init__(self, status):
        self.response = type("Response", (), {"status_code": status, "text": "synthetic"})()


class Calendar:
    """Only the HTTP verbs are simulated; real push outcome/retry code runs."""

    def __init__(self, pusher):
        self.events = {}
        self.calls = []
        self.next_id = 100
        self.fail_reads = False
        self.behavior = {}
        self.pusher = pusher

    @property
    def writes(self):
        return [c for c in self.calls if c[0] in {"post", "put", "delete"}]

    def get(self, endpoint, params=None):
        self.calls.append(("get", endpoint, copy.deepcopy(params)))
        if self.fail_reads:
            raise RuntimeError("synthetic read failure")
        if endpoint == "events":
            return [copy.deepcopy(e) for e in self.events.values()
                    if params["oldest"] <= e["start_date_local"][:10] <= params["newest"]]
        event_id = int(endpoint.split("/")[-1])
        if event_id not in self.events:
            raise HttpError(404)
        return copy.deepcopy(self.events[event_id])

    def _before(self, verb):
        behavior = self.behavior.pop(verb, "normal")
        if behavior == "refuse":
            raise push.WriteStatusError(400, "synthetic refusal")
        if behavior == "timeout_before":
            self.fail_reads = True
            raise TimeoutError("synthetic timeout")
        return behavior

    def _after(self, behavior):
        if behavior == "timeout_after":
            self.fail_reads = True
            raise TimeoutError("synthetic timeout after application")
        if behavior == "crash_after":
            raise KeyboardInterrupt("synthetic process interruption")

    def post(self, endpoint, payload):
        self.calls.append(("post", endpoint, copy.deepcopy(payload)))
        behavior = self._before("post")
        out = []
        for row in payload:
            event_id = self.next_id
            self.next_id += 1
            self.events[event_id] = dict(copy.deepcopy(row), id=event_id)
            out.append(self.events[event_id])
        self._after(behavior)
        return copy.deepcopy(out)

    def put(self, endpoint, payload):
        self.calls.append(("put", endpoint, copy.deepcopy(payload)))
        behavior = self._before("put")
        event_id = int(endpoint.split("/")[-1])
        self.events[event_id].update(copy.deepcopy(payload))
        self._after(behavior)
        return copy.deepcopy(self.events[event_id])

    def delete(self, endpoint):
        self.calls.append(("delete", endpoint))
        behavior = self._before("delete")
        self.events.pop(int(endpoint.split("/")[-1]), None)
        self._after(behavior)
        return True


class CoachingPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "private"
        for module in (plans, push, validator):
            patch = mock.patch.object(module, "datetime", Clock)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(push, "_requests", RefuseEverything())
        patch.start()
        self.addCleanup(patch.stop)
        self.store = plans.PlanStore(self.folder, create=True)
        self.addCleanup(lambda: self.store.close() if self.store else None)
        self.pusher = push.IntervalsPush("i123456", "synthetic-key-never-stored")
        self.remote = Calendar(self.pusher)
        methods = {"_get": self.remote.get, "_post": self.remote.post, "_put": self.remote.put,
                   "_delete": self.remote.delete,
                   "_exception_types": lambda: (TimeoutError, ConnectionError, HttpError, RuntimeError)}
        for name, method in methods.items():
            patch = mock.patch.object(self.pusher, name, side_effect=method)
            patch.start()
            self.addCleanup(patch.stop)
        self.source = json.loads(FIXTURE.read_text())

    def propose(self, value=None):
        return self.store.propose(value or self.source)["revision_id"]

    def revision(self, request="revision-two"):
        result = copy.deepcopy(self.store.show()["plan"])
        result["revision"].update(request_id=request, parent_revision=self.store.latest_id(), reason="Synthetic changed context")
        return result

    def preview(self, rid=None):
        return self.store.preview(rid or self.store.latest_id(), self.pusher)

    def publish(self, preview=None):
        preview = preview or self.preview()
        return self.store.publish(preview["preview_id"], "synthetic athlete approval", self.pusher, confirm=True)

    def replace_session(self, draft, sid, day=None, watts=None):
        session = copy.deepcopy(next(s for s in self.source["sessions"] if s["session_id"] == sid))
        if day:
            session["workout"]["date"] = day
        if watts:
            session["workout"]["coaching_prescription"]["steps"][0]["target"]["low"] = watts
        draft["sessions"] = [session if s["session_id"] == sid else s for s in draft["sessions"]]
        return session

    def test_fresh_session_recovers_current_plan_rationale_and_frozen_targets(self):
        original = copy.deepcopy(self.source)
        rid = self.propose()
        self.assertEqual(self.source, original)
        shown = self.store.show()
        self.store.close()
        self.store = plans.PlanStore(self.folder)
        with mock.patch.object(validator, "catalog", side_effect=AssertionError("historical reads must not recompile")):
            restored = self.store.show()
        self.assertEqual(shown, restored)
        self.assertEqual(restored["revision_id"], rid)
        self.assertEqual(restored["publication"]["state"], "proposed")
        self.assertEqual(restored["publication"]["completion"], "not_inferred")
        self.assertEqual(self.remote.writes, [])

    def test_no_wearable_data_is_required_or_manufactured(self):
        self.propose()
        raw = self.store.path.read_bytes()
        self.assertNotIn(b'"hrv":', raw)
        self.assertNotIn(b'"rhr":', raw)
        self.assertEqual(self.store.show()["plan"]["block"]["planned_phase"], "Base")

    def test_request_retry_is_idempotent_and_changed_reuse_is_rejected(self):
        rid = self.propose()
        count = self.store.history()["total_events"]
        self.assertEqual(self.store.propose(self.source), {"success": True, "revision_id": rid, "unchanged": True})
        self.assertEqual(self.store.history()["total_events"], count)
        self.source["block"]["objective"] = "Different content under the same request"
        with self.assertRaisesRegex(ValueError, "already used"):
            self.propose()

    def test_parent_compare_and_swap_prevents_lost_plan_revision(self):
        old = self.propose()
        first = self.revision()
        second = self.revision("concurrent-revision")
        current = self.propose(first)
        self.assertNotEqual(current, old)
        with self.assertRaisesRegex(ValueError, "parent_revision"):
            self.propose(second)
        self.assertEqual(self.store.latest_id(), current)

    def test_changed_event_date_is_an_attributable_revision_without_rewriting_prescriptions(self):
        first = self.propose()
        before = self.store.show()
        draft = self.revision()
        draft["goals"][0].update(priority="A", date="2027-06-20", description="Synthetic event preparation")
        second = self.propose(draft)
        self.assertEqual(self.store.show(first)["plan"]["goals"][0]["date"], None)
        self.assertEqual(self.store.show(second)["plan"]["goals"][0]["date"], "2027-06-20")
        self.assertEqual(before["prescriptions"], self.store.show()["prescriptions"])
        self.assertEqual(self.store.show()["affected_sessions"], [])
        self.assertEqual(self.store.show()["plan"]["revision"]["parent_revision"], first)

    def test_unknown_parent_fitness_or_saved_workout_edits_cannot_change_old_snapshot(self):
        self.propose()
        frozen = copy.deepcopy(self.store.show()["prescriptions"])
        self.source["sessions"][0]["workout"]["coaching_prescription"]["fitness_reference"]["value_watts"] = 350
        self.source["sessions"][1]["workout"]["coaching_prescription"]["steps"][0]["target"]["low"] = 190
        self.assertEqual(self.store.show()["prescriptions"], frozen)

    def test_changed_availability_requires_a_feasible_revision(self):
        first = self.propose()
        draft = self.revision()
        draft["weeks"][0]["session_windows"][1]["max_minutes"] = 45
        with self.assertRaisesRegex(ValueError, "time budget"):
            self.propose(draft)
        self.assertEqual(self.store.latest_id(), first)
        replacement = self.replace_session(draft, "easy-short")
        replacement["session_budget_minutes"] = 45
        spec = replacement["workout"]["coaching_prescription"]
        spec.update(session_template="AE-4", available_minutes=45)
        spec["steps"][0].update(seconds=2700, target={"basis": "watts", "low": 125, "zones": [1]})
        self.propose(draft)
        self.assertEqual(self.store.show()["affected_sessions"], ["easy-short"])

    def test_week_and_combined_day_budgets_are_checked_without_intensity_quotas(self):
        for change in ("week", "day", "session"):
            draft = copy.deepcopy(self.source)
            if change == "week":
                draft["weeks"][0]["weekly_minutes"] = 199
            elif change == "day":
                draft["sessions"][1]["workout"]["date"] = "2026-10-27"
            else:
                draft["sessions"][0]["session_budget_minutes"] = 49
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.propose(draft)
        draft = copy.deepcopy(self.source)
        draft["weeks"][0]["intensity_approach"]["intent"] = "Moderate emphasis, not polarized"
        self.propose(draft)

    def test_rest_week_and_flexible_later_horizon_are_valid(self):
        draft = copy.deepcopy(self.source)
        draft["sessions"] = []
        draft["weeks"][0].update(weekly_minutes=0, session_windows=[])
        self.propose(draft)
        preview = self.preview()
        self.assertEqual(preview["actions"], [])
        self.assertEqual(self.publish(preview)["publication"]["state"], "published")
        self.assertEqual(self.remote.calls, [])

    def test_other_sports_count_toward_capacity_and_remain_manually_dose_checked(self):
        draft = copy.deepcopy(self.source)
        s = draft["sessions"][0]
        s["workout"] = {"name": "Synthetic strength", "date": "2026-10-27", "type": "WeightTraining", "duration_minutes": 30}
        self.propose(draft)
        rx = next(r for r in self.store.show()["prescriptions"].values() if r["session_id"] == "intervals")
        self.assertEqual(rx["validation"]["status"], "not_checked")
        self.assertEqual(rx["workout"]["duration_minutes"], 30)

    def test_unchecked_cycling_cannot_enter_a_managed_plan(self):
        del self.source["sessions"][0]["workout"]["coaching_prescription"]
        self.source["sessions"][0]["workout"]["duration_minutes"] = 50
        with self.assertRaisesRegex(ValueError, "checked power schema"):
            self.propose()
        self.assertEqual(self.store.latest_id(), None)

    def test_incomplete_or_conflicting_context_is_rejected_atomically(self):
        for change in ("goal", "window", "duplicate", "event_date", "future_evidence", "policy", "zone_model"):
            draft = copy.deepcopy(self.source)
            if change == "goal":
                draft["goals"] = []
            elif change == "window":
                draft["weeks"][0]["session_windows"].pop()
            elif change == "duplicate":
                draft["sessions"].append(copy.deepcopy(draft["sessions"][0]))
            elif change == "event_date":
                draft["goals"][0]["priority"] = "A"
            elif change == "future_evidence":
                draft["revision"]["evidence"][0]["as_of"] = "2026-10-23"
            elif change == "policy":
                draft["planning_policy"] = "universal_80_20"
            else:
                del draft["weeks"][0]["intensity_approach"]["zone_model"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.propose(draft)
            self.assertEqual(self.store.latest_id(), None)
            self.assertEqual(self.store.db.execute("SELECT count(*) FROM prescriptions").fetchone()[0], 0)

    def test_explicit_times_cannot_overlap_or_cross_midnight(self):
        for cross_midnight in (False, True):
            draft = copy.deepcopy(self.source)
            if cross_midnight:
                draft["sessions"][0]["workout"]["time"] = "23:30"
            else:
                draft["sessions"][1]["workout"].update(date="2026-10-27", time="18:30")
                draft["weeks"][0]["session_windows"][0]["max_minutes"] = 120
            with self.subTest(cross_midnight=cross_midnight), self.assertRaisesRegex(ValueError, "overlap|midnight"):
                self.propose(draft)

    def test_prescription_reference_cannot_be_assigned_to_another_session(self):
        self.propose()
        draft = self.revision()
        draft["sessions"][1]["prescription_id"] = draft["sessions"][0]["prescription_id"]
        with self.assertRaisesRegex(ValueError, "another logical session"):
            self.propose(draft)

    def test_store_identity_and_alias_zero_are_rejected(self):
        self.source["athlete_id"] = "0"
        with self.assertRaisesRegex(ValueError, "explicit Intervals"):
            self.propose()
        self.source["athlete_id"] = "i123456"
        self.propose()
        draft = self.revision()
        draft["athlete_id"] = "i987654"
        with self.assertRaisesRegex(ValueError, "different athlete"):
            self.propose(draft)
        self.pusher.athlete_id = "i987654"
        with self.assertRaisesRegex(ValueError, "differs"):
            self.preview()
        self.assertEqual(self.remote.calls, [])

    def test_private_permissions_and_no_credentials_in_store(self):
        self.propose()
        self.assertEqual(self.folder.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(b"synthetic-key-never-stored", self.store.path.read_bytes())
        insecure = Path(self.tmp.name) / "public"
        insecure.mkdir(mode=0o755)
        with self.assertRaisesRegex(ValueError, "mode 0700"):
            plans.PlanStore(insecure, create=True)
        self.assertEqual(insecure.stat().st_mode & 0o777, 0o755)

    def test_source_checkout_and_symlink_store_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            plans.PlanStore(REPO_ROOT / "private-data", create=True)
        link = Path(self.tmp.name) / "link"
        link.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "dedicated"):
            plans.PlanStore(link, create=True)

    def test_revision_prescription_preview_and_journal_are_append_only(self):
        self.propose()
        self.preview()
        for table in ("revisions", "prescriptions", "previews", "journal"):
            for verb in ("UPDATE", "DELETE"):
                sql = f"UPDATE {table} SET body='{{}}'" if verb == "UPDATE" else f"DELETE FROM {table}"
                with self.subTest(table=table, verb=verb), self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    self.store.db.execute(sql)
                self.store.db.rollback()
        row = self.store.db.execute("SELECT * FROM prescriptions LIMIT 1").fetchone()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.store.db.execute("INSERT OR REPLACE INTO prescriptions VALUES (?,?)", tuple(row))
        self.store.db.rollback()

    def test_concurrent_mutator_is_rejected_without_changing_the_plan(self):
        second = plans.PlanStore(self.folder)
        self.addCleanup(second.close)
        with self.store.locked():
            with self.assertRaisesRegex(ValueError, "another plan operation"):
                second.propose(self.source)
        self.assertEqual(self.store.latest_id(), None)

    def test_preview_is_concrete_and_read_only_then_confirm_sends_exact_payloads(self):
        self.propose()
        preview = self.preview()
        self.assertEqual(self.remote.writes, [])
        self.assertEqual([a["kind"] for a in preview["actions"]], ["create"] * 3)
        result = self.publish(preview)
        self.assertTrue(result["success"])
        self.assertEqual(result["publication"]["state"], "published")
        self.assertEqual([c[2][0] for c in self.remote.writes], [a["after"] for a in preview["actions"]])
        self.assertEqual(len(set(e["external_id"] for e in self.remote.events.values())), 3)
        self.assertEqual(self.store.pending(), [])
        self.assertEqual(result["publication"]["completion"], "not_inferred")

    def test_confirmation_requires_approval_current_revision_and_unused_preview(self):
        self.propose()
        preview = self.preview()
        for confirm, approval in ((False, "message"), (True, "")):
            with self.assertRaises(ValueError):
                self.store.publish(preview["preview_id"], approval, self.pusher, confirm=confirm)
        self.assertEqual(self.remote.writes, [])
        self.publish(preview)
        count = len(self.remote.writes)
        with self.assertRaises(ValueError):
            self.publish(preview)
        self.assertEqual(len(self.remote.writes), count)

    def test_superseded_preview_is_not_publishable(self):
        self.propose()
        preview = self.preview()
        self.propose(self.revision())
        with self.assertRaisesRegex(ValueError, "current plan revision"):
            self.publish(preview)
        self.assertEqual(self.remote.writes, [])

    def test_same_plan_republication_has_no_duplicate_calendar_writes(self):
        self.propose()
        self.publish()
        count = len(self.remote.writes)
        preview = self.preview()
        self.assertEqual(preview["actions"], [])
        self.publish(preview)
        self.assertEqual(len(self.remote.writes), count)

    def test_move_updates_the_stable_event_id_and_preserves_old_prescription(self):
        first = self.propose()
        self.publish()
        old = copy.deepcopy(self.store.bindings()["easy-short"])
        old_rx = self.store.prescription(old["prescription_id"])
        draft = self.revision()
        self.replace_session(draft, "easy-short", day="2026-10-28")
        draft["weeks"][0]["session_windows"].append({"date": "2026-10-28", "max_minutes": 60})
        second = self.propose(draft)
        preview = self.preview()
        self.assertEqual([a["kind"] for a in preview["actions"]], ["update"])
        self.assertEqual(preview["actions"][0]["before"]["start_date_local"], "2026-10-29T10:00:00")
        self.assertEqual(preview["actions"][0]["after"]["start_date_local"], "2026-10-28T10:00:00")
        self.publish(preview)
        current = self.store.bindings()["easy-short"]
        self.assertEqual(current["event_id"], old["event_id"])
        self.assertNotEqual(current["prescription_id"], old["prescription_id"])
        self.assertEqual(self.store.prescription(old["prescription_id"]), old_rx)
        self.assertFalse(self.store.show(first)["is_current"])
        history = self.store.event_history(old["event_id"])["versions"]
        self.assertEqual([r["revision_id"] for r in history], [first, second])
        self.assertEqual([r["prescription"]["workout"]["date"] for r in history], ["2026-10-29", "2026-10-28"])

    def test_removed_future_session_requires_explicit_previewed_delete(self):
        self.propose()
        self.publish()
        old = self.store.bindings()["endurance"]
        draft = self.revision()
        draft["sessions"] = [s for s in draft["sessions"] if s["session_id"] != "endurance"]
        self.propose(draft)
        count = len(self.remote.writes)
        preview = self.preview()
        self.assertEqual(len(self.remote.writes), count)
        self.assertEqual([a["kind"] for a in preview["actions"]], ["delete"])
        self.assertEqual(preview["actions"][0]["before"]["name"], "Synthetic endurance ride")
        self.publish(preview)
        self.assertNotIn(old["event_id"], self.remote.events)
        self.assertNotIn("endurance", self.store.bindings())
        self.assertEqual(self.store.event_history(old["event_id"])["versions"][-1]["kind"], "delete")

    def test_conflicting_remote_edits_or_pairing_block_the_whole_batch(self):
        self.propose()
        self.publish()
        draft = self.revision()
        self.replace_session(draft, "easy-short", watts=180)
        self.propose(draft)
        preview = self.preview()
        event_id = self.store.bindings()["easy-short"]["event_id"]
        before = copy.deepcopy(self.remote.events[event_id])
        count = len(self.remote.writes)
        for change in ({"name": "Athlete edited it"}, {"external_id": "different"}, {"paired_activity_id": "completed-ride"}):
            self.remote.events[event_id] = dict(before, **change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "no overwrite/delete"):
                self.publish(preview)
            self.assertEqual(len(self.remote.writes), count)

    def test_existing_new_external_identity_or_failed_pre_read_closes_the_gate(self):
        self.propose()
        rx = next(iter(self.store.show()["prescriptions"].values()))
        self.remote.events[999] = dict(self.pusher._build_event(rx["workout"]), id=999)
        with self.assertRaisesRegex(ValueError, "already present"):
            self.preview()
        self.remote.events.clear()
        self.remote.fail_reads = True
        with self.assertRaises(ValueError):
            self.preview()
        self.assertEqual(self.remote.writes, [])

    def test_ambiguous_create_is_not_retried_and_reconciles_only_exact_identity(self):
        self.propose()
        preview = self.preview()
        self.remote.behavior["post"] = "timeout_after"
        result = self.publish(preview)
        self.assertEqual(result["outcome"], "unknown")
        self.assertEqual(len(self.remote.writes), 1)
        self.assertEqual(len(self.store.pending()), 1)
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.preview()
        self.remote.fail_reads = False
        self.assertTrue(self.store.reconcile(self.pusher)["success"])
        self.assertEqual(len(self.remote.writes), 1)
        new_preview = self.preview()
        self.assertEqual(len(new_preview["actions"]), 2)
        self.publish(new_preview)
        self.assertEqual(len(self.remote.writes), 3)

    def test_absence_or_payload_mismatch_never_proves_an_uncertain_create_failed(self):
        self.propose()
        preview = self.preview()
        self.remote.behavior["post"] = "timeout_before"
        self.publish(preview)
        self.remote.fail_reads = False
        self.assertFalse(self.store.reconcile(self.pusher)["success"])
        self.assertEqual(len(self.remote.writes), 1)
        op = self.store.pending()[0]
        payload = copy.deepcopy(op["action"]["after"])
        self.remote.events[999] = dict(payload, id=999, name="Wrong target")
        self.assertFalse(self.store.reconcile(self.pusher)["success"])
        self.remote.events[999] = dict(payload, id=999)
        self.remote.events[998] = dict(payload, id=998)
        self.assertFalse(self.store.reconcile(self.pusher)["success"])
        self.assertEqual(len(self.remote.writes), 1)

    def test_process_interruption_leaves_a_durable_reconciliation_gate_after_restart(self):
        self.propose()
        preview = self.preview()
        self.remote.behavior["post"] = "crash_after"
        with self.assertRaises(KeyboardInterrupt):
            self.publish(preview)
        self.store.close()
        self.store = plans.PlanStore(self.folder)
        self.assertEqual(len(self.store.pending()), 1)
        with self.assertRaises(ValueError):
            self.preview()
        self.assertTrue(self.store.reconcile(self.pusher)["success"])
        self.assertEqual(len(self.remote.writes), 1)

    def test_post_send_local_journal_failure_stays_uncertain_on_restart(self):
        self.propose()
        preview = self.preview()
        real_log = self.store._log
        def fail_result(kind, *args):
            if kind == "operation_applied":
                raise OSError("synthetic disk failure")
            return real_log(kind, *args)
        with mock.patch.object(self.store, "_log", side_effect=fail_result):
            with self.assertRaises(OSError):
                self.publish(preview)
        self.store.close()
        self.store = plans.PlanStore(self.folder)
        self.assertEqual(len(self.store.pending()), 1)
        self.assertTrue(self.store.reconcile(self.pusher)["success"])
        self.assertEqual(len(self.remote.writes), 1)

    def test_definitive_refusal_is_distinct_from_unknown_and_consumes_the_preview(self):
        self.propose()
        preview = self.preview()
        self.remote.behavior["post"] = "refuse"
        result = self.publish(preview)
        self.assertEqual(result["outcome"], "not_applied")
        self.assertEqual(self.store.pending(), [])
        with self.assertRaisesRegex(ValueError, "already used"):
            self.publish(preview)
        self.publish()
        self.assertEqual(len(self.remote.events), 3)

    def test_partial_application_is_never_reported_as_nothing_applied(self):
        self.propose()
        preview = self.preview()
        original = self.remote.post
        def refuse_second(endpoint, payload):
            if len(self.remote.events) == 1:
                self.remote.behavior["post"] = "refuse"
            return original(endpoint, payload)
        with mock.patch.object(self.pusher, "_post", side_effect=refuse_second):
            result = self.publish(preview)
        self.assertEqual(result["outcome"], "partially_applied")
        self.assertEqual(result["publication"]["state"], "partially_published")
        self.assertEqual(len(self.remote.events), 1)
        self.assertEqual(len(self.preview()["actions"]), 2)

    def test_uncertain_update_and_delete_reconcile_without_replaying_writes(self):
        self.propose()
        self.publish()
        for kind in ("update", "delete"):
            draft = self.revision("change-" + kind)
            if kind == "update":
                self.replace_session(draft, "easy-short", watts=180)
            else:
                draft["sessions"] = [s for s in draft["sessions"] if s["session_id"] != "easy-short"]
            self.propose(draft)
            preview = self.preview()
            self.remote.behavior["put" if kind == "update" else "delete"] = "timeout_after"
            result = self.publish(preview)
            self.assertEqual(result["outcome"], "unknown")
            count = len(self.remote.writes)
            self.remote.fail_reads = False
            self.assertTrue(self.store.reconcile(self.pusher)["success"])
            self.assertEqual(len(self.remote.writes), count)

    def test_manual_resolution_requires_external_evidence_and_explicit_confirmation(self):
        self.propose()
        preview = self.preview()
        self.remote.behavior["post"] = "timeout_before"
        self.publish(preview)
        op = self.store.pending()[0]["operation_id"]
        for evidence_ref, approval, confirm in (("", "approval", True), ("server determination", "", True), ("server determination", "approval", False)):
            with self.assertRaises(ValueError):
                self.store.resolve_not_applied(op, evidence_ref, approval, confirm)
        result = self.store.resolve_not_applied(op, "Synthetic external server-log determination", "Synthetic athlete approval", True)
        self.assertEqual(result["calendar_writes"], 0)
        self.assertEqual(self.store.pending(), [])
        last = self.store.history()["events"][-1]
        self.assertIn("not_independently_verified", last["body"]["source"])

    def test_new_plan_revision_may_be_drafted_but_not_published_during_uncertainty(self):
        self.propose()
        self.remote.behavior["post"] = "timeout_after"
        self.publish()
        draft = self.revision()
        self.propose(draft)
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            self.preview()
        self.remote.fail_reads = False
        self.store.reconcile(self.pusher)
        self.assertEqual(len(self.preview()["actions"]), 2)

    def test_past_publications_are_not_deleted_or_repurposed(self):
        self.propose()
        self.publish()
        with mock.patch.object(plans, "today", return_value="2026-11-02"):
            draft = self.revision()
            draft["sessions"] = []
            self.propose(draft)
            preview = self.preview()
            self.assertEqual(preview["actions"], [])
            self.publish(preview)
            self.assertEqual(len(self.remote.events), 3)
            draft = self.revision("reuse-historical-session")
            replacement = copy.deepcopy(self.source["sessions"][1])
            replacement["workout"]["date"] = "2026-11-03"
            draft["sessions"] = [replacement]
            with self.assertRaisesRegex(ValueError, "historical session"):
                self.propose(draft)

    def test_changed_catalog_cannot_silently_recertify_a_stored_prescription(self):
        self.propose()
        real_preview = self.pusher.preview_push
        def changed(workouts):
            result = real_preview(workouts)
            result["coaching_validation"][0]["constraints_sha256"] = "changed"
            return result
        with mock.patch.object(self.pusher, "preview_push", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "catalog changed"):
                self.preview()
        self.assertEqual(self.remote.writes, [])

    def test_changed_payload_builder_after_preview_cannot_change_approved_calendar_payload(self):
        self.propose()
        preview = self.preview()
        build = self.pusher._build_event
        with mock.patch.object(self.pusher, "_build_event", side_effect=lambda w: dict(build(w), color="red")):
            with self.assertRaisesRegex(ValueError, "payload builder changed"):
                self.publish(preview)
        self.assertEqual(self.remote.writes, [])

    def test_store_version_mismatch_is_not_auto_migrated(self):
        self.store.db.execute("PRAGMA user_version=99")
        with self.assertRaisesRegex(ValueError, "unsupported"):
            plans.PlanStore(self.folder)

    def test_managed_preview_loads_explicit_credentials_outside_cwd_without_writes(self):
        revision=self.propose();directory=Path(self.tmp.name)/'source-data';directory.mkdir(mode=0o700)
        credentials=directory/'.sync_config.json';credentials.write_text(json.dumps({'athlete_id':'i123456','intervals_key':'synthetic-private-key'}));credentials.chmod(0o600)
        argv=['coaching_plan.py','--data-dir',str(self.folder),'--credentials-dir',str(directory),'preview','--revision',revision]
        with mock.patch.object(sys,'argv',argv),mock.patch.object(push,'IntervalsPush',return_value=self.pusher) as constructor,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(plans.main(),0)
        constructor.assert_called_once_with('i123456','synthetic-private-key')
        result=json.loads(out.getvalue());self.assertEqual(result['revision_id'],revision);self.assertEqual(result['mode'],'preview')
        self.assertEqual(self.remote.writes,[]);self.assertTrue(result['preview_id'].startswith('preview-'))
        self.assertNotIn('synthetic-private-key',out.getvalue())

    def test_local_cli_propose_show_and_history_work_without_credentials(self):
        directory = Path(self.tmp.name) / "cli-private"
        # Subprocesses use the actual wall clock, unlike the in-process fixtures.
        # Shift the synthetic week so this CLI check remains useful after 2026.
        current = datetime.now().date()
        monday = current + timedelta(days=7 - current.weekday())
        delta = monday - datetime(2026, 10, 26).date()
        def shift(value):
            if isinstance(value, list):
                return [shift(v) for v in value]
            if isinstance(value, dict):
                return {k: current.isoformat() if k == "as_of" else shift(v) for k, v in value.items()}
            if isinstance(value, str):
                try:
                    parsed = datetime.strptime(value, "%Y-%m-%d")
                    if parsed.date().isoformat() == value:
                        return (parsed.date() + delta).isoformat()
                except ValueError:
                    pass
            return value
        cli_fixture = Path(self.tmp.name) / "cli-input.json"
        cli_fixture.write_text(json.dumps(shift(self.source)))
        env = dict(os.environ)
        env.pop("ATHLETE_ID", None)
        env.pop("INTERVALS_KEY", None)
        for args in (("propose", "--json", str(cli_fixture)), ("show",), ("history", "--limit", "1")):
            result = subprocess.run([sys.executable, str(PATH), "--data-dir", str(directory), *args],
                                    cwd=self.tmp.name, env=env, capture_output=True, text=True, check=True)
            self.assertTrue(json.loads(result.stdout)["success"])
        missing = subprocess.run([sys.executable, str(PATH), "--data-dir", str(Path(self.tmp.name) / "absent"), "show"],
                                 cwd=self.tmp.name, env=env, capture_output=True, text=True)
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse((Path(self.tmp.name) / "absent").exists())

    def test_bounded_history_and_one_prescription_retrieval_avoid_full_context_dump(self):
        self.propose()
        self.publish()
        result = self.store.history(limit=2)
        self.assertEqual(len(result["events"]), 2)
        self.assertGreater(result["total_events"], 2)
        pid = self.store.show()["plan"]["sessions"][0]["prescription_id"]
        self.assertEqual(self.store.prescription(pid)["session_id"], "intervals")
        for limit in (0, True, 1001):
            with self.assertRaises(ValueError):
                self.store.history(limit)

    def test_compact_view_keeps_intent_and_reference_ids_without_repeated_steps(self):
        self.propose()
        compact = self.store.summary()
        self.assertNotIn("prescriptions", compact)
        self.assertEqual(len(compact["prescription_summaries"]), 3)
        self.assertEqual(compact["plan"]["block"]["objective"], self.source["block"]["objective"])
        self.assertNotIn('"steps"', json.dumps(compact))

    def test_separate_store_namespace_does_not_upsert_another_stores_external_ids(self):
        self.propose()
        other = plans.PlanStore(Path(self.tmp.name) / "other-private", create=True)
        self.addCleanup(other.close)
        other.propose(self.source)
        first = {r["workout"]["external_id"] for r in self.store.show()["prescriptions"].values()}
        second = {r["workout"]["external_id"] for r in other.show()["prescriptions"].values()}
        self.assertTrue(first.isdisjoint(second))
        self.assertNotEqual(self.store.store_id, other.store_id)

    def test_delete_preview_cannot_delete_a_session_after_it_becomes_historical(self):
        self.propose()
        self.publish()
        draft = self.revision()
        draft["sessions"] = [s for s in draft["sessions"] if s["session_id"] != "endurance"]
        self.propose(draft)
        preview = self.preview()
        count = len(self.remote.writes)
        with mock.patch.object(plans, "today", return_value="2026-11-02"):
            with self.assertRaisesRegex(ValueError, "historical calendar"):
                self.publish(preview)
        self.assertEqual(len(self.remote.writes), count)

    def test_removing_a_managed_optional_field_is_visible_and_verified(self):
        self.source["sessions"][1]["workout"]["color"] = "blue"
        self.propose()
        self.publish()
        draft = self.revision()
        replacement = self.replace_session(draft, "easy-short")
        del replacement["workout"]["color"]
        self.propose(draft)
        preview = self.preview()
        self.assertEqual(preview["actions"][0]["before"]["color"], "blue")
        self.assertIsNone(preview["actions"][0]["after"]["color"])
        result = self.publish(preview)
        self.assertEqual(result["outcome"], "applied")
        self.assertIsNone(self.remote.events[self.store.bindings()["easy-short"]["event_id"]]["color"])

    def test_descriptive_phase_does_not_override_planned_intent(self):
        self.source["detected_phase"]["value"] = "Build"
        self.propose()
        self.assertEqual(self.store.show()["plan"]["block"]["planned_phase"], "Base")
        self.assertEqual(self.store.show()["plan"]["detected_phase"]["value"], "Build")

    def test_week_outside_block_is_not_an_unrelated_long_range_plan(self):
        self.source["sessions"] = []
        self.source["weeks"][0].update(start_date="2027-01-04", session_windows=[])
        with self.assertRaisesRegex(ValueError, "block horizon"):
            self.propose()

    def test_failed_remove_leaves_publication_incomplete_and_can_be_previewed_again(self):
        self.propose()
        self.publish()
        draft = self.revision()
        draft["sessions"] = [s for s in draft["sessions"] if s["session_id"] != "endurance"]
        self.propose(draft)
        self.remote.behavior["delete"] = "refuse"
        result = self.publish()
        self.assertFalse(result["success"])
        self.assertEqual(result["publication"]["state"], "partially_published")
        self.assertEqual(result["publication"]["removed_sessions_still_on_calendar"], ["endurance"])
        self.assertEqual([a["kind"] for a in self.preview()["actions"]], ["delete"])

    def test_expired_fitness_review_blocks_the_whole_batch_before_any_calendar_read(self):
        spec = self.source["sessions"][0]["workout"]["coaching_prescription"]
        spec["fitness_reference"].update(status="stale", review={"date": "2026-10-22", "decision": "use_provisionally", "reason": "Synthetic repeatable performance review"})
        self.propose()
        with mock.patch.object(validator, "datetime") as later:
            later.now.return_value = datetime(2026, 10, 23)
            later.strptime = datetime.strptime
            with self.assertRaisesRegex(ValueError, "current explicit review"):
                self.preview()
        self.assertEqual(self.remote.calls, [])

    def test_confirm_validates_later_prescriptions_before_reading_any_calendar_event(self):
        self.propose()
        preview = self.preview()
        self.remote.calls.clear()
        real_preview = self.pusher.preview_push
        def invalid_second(workouts):
            if workouts[0]["name"] == "Synthetic easy ride":
                return {"success": False, "error": "Synthetic later prescription now invalid"}
            return real_preview(workouts)
        with mock.patch.object(self.pusher, "preview_push", side_effect=invalid_second):
            with self.assertRaisesRegex(ValueError, "later prescription"):
                self.publish(preview)
        self.assertEqual(self.remote.calls, [])


if __name__ == "__main__":
    unittest.main()
