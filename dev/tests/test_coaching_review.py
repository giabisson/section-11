"""Cause-aware multiweek review replay; no LLM, calendar or notification service."""
import copy
import json
import unittest
from unittest import mock

import test_coaching_plan as fixtures

plans = fixtures.plans


class CoachingReview(unittest.TestCase):
    setUp = fixtures.CoachingPlan.setUp
    propose = fixtures.CoachingPlan.propose
    preview = fixtures.CoachingPlan.preview
    publish = fixtures.CoachingPlan.publish
    revision = fixtures.CoachingPlan.revision
    replace_session = fixtures.CoachingPlan.replace_session

    def ready(self):
        self.propose()
        self.publish()
        patch = mock.patch.object(plans, "today", return_value="2026-10-29")
        patch.start()
        self.addCleanup(patch.stop)
        shown = self.store.show()
        rxid = next(s["prescription_id"] for s in shown["plan"]["sessions"] if s["session_id"] == "intervals")
        eid = self.store.bindings()["intervals"]["event_id"]
        return {"schema_version": 1, "review_id": "weekly-one", "parent_revision": shown["revision_id"],
                "trigger": "athlete", "schedule_opt_in": False, "assessed_date": "2026-10-29",
                "period": {"start": "2026-10-26", "end": "2026-10-28"},
                "snapshot": {"athlete_id": "i123456", "source": "Synthetic Intervals API read", "as_of": "2026-10-29", "coverage": "complete",
                    "activities": [{"id": "activity-one", "paired_event_id": eid, "start_date": "2026-10-27T18:00:00+00:00"}],
                    "events": [dict(self.remote.events[eid], paired_activity_id="activity-one")],
                    "readiness": {"date": "2026-10-29", "recommendation": "go", "priority": 3, "health_clarification_required": False}},
                "observations": [{"session_id": "intervals", "prescription_id": rxid, "activity_id": "activity-one", "status": "completed",
                    "cause": "none", "goal_attainment": "met", "response": "tolerated", "source": "Synthetic athlete feedback and paired activity",
                    "date": "2026-10-28", "note": "Tolerable familiar dose; no symptom report"}],
                "current_feedback": {"date": "2026-10-29", "state": "normal", "source": "Synthetic current athlete statement",
                                     "note": "Feeling healthy and rested; HRV not measured", "health_clarification": None},
                "decisions": [{"action": "maintain", "session_ids": [], "observation_ids": ["intervals"],
                    "reason": "Retain the tolerable objective and dose", "next_observation": "Review execution and response after the next comparable session"}],
                "candidate_plan": None}

    def candidate(self, review, action="progress", minutes=100):
        draft = self.revision("review-candidate")
        s = self.replace_session(draft, "endurance")
        spec = s["workout"]["coaching_prescription"]
        spec.update(session_template="AE-2" if minutes >= 90 else "AE-1", available_minutes=120)
        spec["steps"][0]["seconds"] = minutes * 60
        review["decisions"][0].update(action=action, session_ids=["endurance"], reason="Apply an explained future dose change after reviewing the athlete's response")
        review["candidate_plan"] = draft
        return draft

    def test_success_keeps_pairing_goal_and_response_separate_from_adherence(self):
        source = self.ready()
        result = self.store.review(source)
        row = result["report"]["observations"][0]
        self.assertEqual(row["completion_evidence"], "paired_activity")
        self.assertEqual(row["adherence"], "unknown_requires_formal_evaluator")
        self.assertEqual(row["goal_attainment"], "met")
        self.assertFalse(result["revision_created"])
        self.assertEqual(result["calendar_writes"], 0)

    def test_success_supports_a_concrete_progression_without_automatic_percentages(self):
        source = self.ready()
        original = source["parent_revision"]
        self.candidate(source)
        writes = len(self.remote.writes)
        result = self.store.review(source)
        self.assertTrue(result["revision_created"])
        new = self.store.show()
        rx = next(r for r in new["prescriptions"].values() if r["session_id"] == "endurance")
        self.assertEqual(rx["workout"]["duration_minutes"], 100)
        self.assertEqual(self.store.show(original)["plan"]["sessions"][0], new["plan"]["sessions"][0])
        self.assertEqual(len(self.remote.writes), writes)

    def test_repeated_review_including_scheduled_trigger_does_not_duplicate_revisions(self):
        source = self.ready()
        self.candidate(source)
        first = self.store.review(source)
        events = self.store.history()["total_events"]
        retry = copy.deepcopy(source)
        retry.update(review_id="scheduler-retry", parent_revision=first["revision_id"], trigger="scheduled", schedule_opt_in=True)
        result = self.store.review(retry)
        self.assertTrue(result["unchanged"])
        self.assertFalse(result["notify"])
        self.assertEqual(self.store.history()["total_events"], events)
        self.assertEqual(self.store.latest_id(), first["revision_id"])

    def test_same_review_id_cannot_mask_changed_feedback(self):
        source = self.ready()
        self.store.review(source)
        source["current_feedback"]["state"] = "fatigued"
        with self.assertRaisesRegex(ValueError, "different evidence"):
            self.store.review(source)

    def test_scheduled_review_requires_opt_in_and_stays_quiet_when_maintaining(self):
        source = self.ready()
        source["trigger"] = "scheduled"
        with self.assertRaisesRegex(ValueError, "opt-in"):
            self.store.review(source)
        source["schedule_opt_in"] = True
        result = self.store.review(source)
        self.assertFalse(result["notify"])

    def test_pairing_conflicts_missing_data_and_current_saved_versions_stay_unresolved(self):
        for change in ("reverse", "duplicate", "missing", "unpublished", "time", "no_pair"):
            source = self.ready() if self.store.latest_id() is None else copy.deepcopy(base)
            base = copy.deepcopy(source)
            if change == "reverse":
                source["snapshot"]["events"][0]["paired_activity_id"] = "another"
            elif change == "duplicate":
                source["snapshot"]["activities"] *= 2
            elif change == "missing":
                source["snapshot"]["events"] = []
            elif change == "unpublished":
                source["snapshot"]["activities"][0]["paired_event_id"] = 999
            elif change == "time":
                source["snapshot"]["activities"][0]["start_date"] = "2026-10-27T18:00:00"
            else:
                source["observations"][0]["activity_id"] = None
            source["review_id"] = "pair-" + change
            result = self.store.review(source)
            self.assertIsNotNone(result["report"]["observations"][0]["pairing_issue"])
            self.assertTrue(result["report"]["guard"]["progression_review_required"])

    def test_unmatched_reported_completion_cannot_support_progression(self):
        source = self.ready()
        source["observations"][0]["activity_id"] = None
        self.candidate(source)
        with self.assertRaisesRegex(ValueError, "progression"):
            self.store.review(source)

    def test_missed_work_session_creates_neither_catchup_nor_ftp_change(self):
        source = self.ready()
        row = source["observations"][0]
        row.update(status="missed", activity_id=None, cause="work", goal_attainment="unknown", response="unknown",
                   note="Work meeting prevented training")
        result = self.store.review(source)
        self.assertFalse(result["report"]["missed_session_debt"])
        self.assertFalse(result["revision_created"])
        self.assertEqual(result["report"]["unresolved_questions"], [])

    def test_unknown_missed_session_reason_requests_only_relevant_context(self):
        source = self.ready()
        source["observations"][0].update(status="missed", activity_id=None, cause="unknown", goal_attainment="unknown", response="unknown")
        source["decisions"][0]["action"] = "request_context"
        result = self.store.review(source)
        self.assertEqual(len(result["report"]["unresolved_questions"]), 1)
        self.assertNotIn("HRV", result["report"]["unresolved_questions"][0])

    def test_unexpected_difficulty_supports_reduction_not_diagnostic_overreach(self):
        source = self.ready()
        source["observations"][0]["response"] = "unexpectedly_hard"
        self.candidate(source, "reduce", 60)
        result = self.store.review(source)
        self.assertTrue(result["revision_created"])
        self.assertTrue(result["report"]["observations"][0]["cost_review_required"])
        self.assertNotIn("overreach", json.dumps(result).lower())

    def test_fatigue_does_not_allow_progression_or_an_increase_hidden_as_reduce(self):
        for action in ("progress", "reduce"):
            source = self.ready() if self.store.latest_id() is None else copy.deepcopy(base)
            base = copy.deepcopy(source)
            source["current_feedback"]["state"] = "fatigued"
            self.candidate(source, action, 100)
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "progression|increase"):
                self.store.review(source)

    def test_missing_wearables_or_current_feedback_does_not_force_a_training_change(self):
        source = self.ready()
        source["current_feedback"] = None
        self.candidate(source, "progress", 100)
        result = self.store.review(source)
        self.assertFalse(result["report"]["wearables_required"])
        self.assertTrue(result["revision_created"])
        self.assertEqual(result["report"]["unresolved_questions"], [])

    def test_stale_readiness_requires_refresh_not_false_normal_values(self):
        source = self.ready()
        source["snapshot"]["as_of"] = "2026-10-28"
        result = self.store.review(source)
        self.assertTrue(result["report"]["guard"]["same_day_clarification"])
        self.assertTrue(result["report"]["unresolved_questions"])
        draft = self.revision("same-day-after-stale-data")
        self.replace_session(draft, "easy-short", watts=180)
        self.propose(draft)
        with self.assertRaisesRegex(ValueError, "latest review"):
            self.preview()

    def test_p0_p1_and_current_weakness_cannot_be_erased_by_good_feedback(self):
        source = self.ready()
        source["snapshot"]["readiness"].update(recommendation="skip", priority=0)
        result = self.store.review(source)
        self.assertTrue(result["report"]["guard"]["same_day_stop"])
        draft = self.revision("same-day-after-stop")
        self.replace_session(draft, "easy-short", watts=180)
        self.propose(draft)
        with self.assertRaisesRegex(ValueError, "same-day stop"):
            self.preview()
        source = copy.deepcopy(source)
        source["review_id"] = "inconsistent-envelope"
        source["parent_revision"] = self.store.latest_id()
        source["snapshot"]["readiness"]["recommendation"] = "go"
        with self.assertRaisesRegex(ValueError, "P0/P1"):
            self.store.review(source)

    def test_health_marker_needs_context_and_compatibility_does_not_override_skip(self):
        source = self.ready()
        source["snapshot"]["readiness"]["health_clarification_required"] = True
        result = self.store.review(source)
        self.assertTrue(result["report"]["guard"]["same_day_clarification"])
        source["review_id"] = "health-clarified"
        source["current_feedback"]["health_clarification"] = {"compatible": True, "reason": "Synthetic minor resolved issue discussed"}
        result = self.store.review(source)
        self.assertFalse(result["report"]["guard"]["same_day_clarification"])

    def test_review_revision_cannot_change_the_past_or_unattributed_sessions(self):
        source = self.ready()
        draft = self.candidate(source)
        source["decisions"][0]["session_ids"] = []
        with self.assertRaisesRegex(ValueError, "attributable"):
            self.store.review(source)
        source["decisions"][0]["session_ids"] = ["intervals"]
        draft["sessions"] = [s for s in draft["sessions"] if s["session_id"] != "intervals"]
        source["decisions"][0]["session_ids"].append("endurance")
        with self.assertRaisesRegex(ValueError, "historical selections"):
            self.store.review(source)

    def test_concrete_revision_and_review_commit_atomically(self):
        source = self.ready()
        self.candidate(source)
        before = self.store.latest_id()
        real_log = self.store._log
        def fail(kind, *args):
            if kind == "reviewed":
                raise OSError("Synthetic journal failure")
            return real_log(kind, *args)
        with mock.patch.object(self.store, "_log", side_effect=fail):
            with self.assertRaises(OSError):
                self.store.review(source)
        self.assertEqual(self.store.latest_id(), before)

    def test_event_date_and_reduced_availability_create_explained_revisions(self):
        source = self.ready()
        draft = self.candidate(source, "reduce", 60)
        draft["weeks"][0]["session_windows"][2]["max_minutes"] = 60
        draft["goals"][0].update(priority="A", date="2026-11-15")
        self.store.review(source)
        self.assertEqual(self.store.show()["plan"]["goals"][0]["date"], "2026-11-15")
        self.assertEqual(self.store.show()["plan"]["weeks"][0]["session_windows"][2]["max_minutes"], 60)

    def test_wrong_athlete_and_stale_parent_cannot_enter_the_review(self):
        source = self.ready()
        source["snapshot"]["athlete_id"] = "i987654"
        with self.assertRaisesRegex(ValueError, "another athlete"):
            self.store.review(source)
        source["snapshot"]["athlete_id"] = "i123456"
        self.propose(self.revision())
        with self.assertRaisesRegex(ValueError, "not current"):
            self.store.review(source)

    def test_unrecorded_sessions_stay_unknown_instead_of_becoming_misses(self):
        source = self.ready()
        source["observations"] = []
        source["decisions"][0]["observation_ids"] = []
        result = self.store.review(source)
        self.assertEqual(result["report"]["observations"][0]["status"], "unknown")
        self.assertFalse(result["report"]["missed_session_debt"])

    def test_no_narrative_only_adjustments_or_maintain_with_hidden_changes(self):
        source = self.ready()
        source["decisions"][0]["action"] = "reduce"
        with self.assertRaisesRegex(ValueError, "concrete candidate"):
            self.store.review(source)
        self.candidate(source, "maintain", 100)
        with self.assertRaisesRegex(ValueError, "maintain cannot hide"):
            self.store.review(source)

    def test_repeated_difficulty_counts_distinct_occurrences_not_duplicate_reviews(self):
        self.source["sessions"][1]["workout"] = copy.deepcopy(self.source["sessions"][0]["workout"])
        self.source["sessions"][1]["workout"]["date"] = "2026-10-28"
        self.source["weeks"][0]["session_windows"][1]["date"] = "2026-10-28"
        source = self.ready()
        source["observations"][0]["response"] = "unexpectedly_hard"
        eid = self.store.bindings()["easy-short"]["event_id"]
        pid = self.store.bindings()["easy-short"]["prescription_id"]
        source["snapshot"]["activities"].append({"id": "second-hard", "paired_event_id": eid, "start_date": "2026-10-28T18:00:00+00:00"})
        source["snapshot"]["events"].append(dict(self.remote.events[eid], paired_activity_id="second-hard"))
        source["observations"].append(dict(source["observations"][0], session_id="easy-short", prescription_id=pid, activity_id="second-hard"))
        result = self.store.review(source)
        self.assertEqual(result["report"]["response_patterns"][0]["distinct_occurrences"], 2)
        self.assertIn("fueling", result["report"]["response_patterns"][0]["next_review"])
        source["review_id"] = "same-evidence-retry"
        self.assertTrue(self.store.review(source)["unchanged"])

    def test_multiweek_replay_progresses_then_reduces_and_preserves_missed_work_context(self):
        source = self.ready()
        draft = self.candidate(source)
        week = copy.deepcopy(draft["weeks"][0])
        week["start_date"] = "2026-11-02"
        for window in week["session_windows"]:
            window["date"] = {"2026-10-27": "2026-11-03", "2026-10-29": "2026-11-05", "2026-10-31": "2026-11-07"}[window["date"]]
        draft["weeks"].append(week)
        for old, new, day in (("intervals", "intervals-two", "2026-11-03"), ("easy-short", "easy-two", "2026-11-05"), ("endurance", "long-two", "2026-11-07")):
            session = copy.deepcopy(next(s for s in self.source["sessions"] if s["session_id"] == old))
            session["session_id"] = new
            session["workout"]["date"] = day
            draft["sessions"].append(session)
            source["decisions"][0]["session_ids"].append(new)
        first = self.store.review(source)
        self.publish()
        with mock.patch.object(plans, "today", return_value="2026-11-05"):
            second = copy.deepcopy(source)
            second.update(review_id="week-two-response", parent_revision=first["revision_id"], assessed_date="2026-11-05",
                          period={"start": "2026-11-02", "end": "2026-11-04"}, candidate_plan=None)
            eid = self.store.bindings()["intervals-two"]["event_id"]
            pid = self.store.bindings()["intervals-two"]["prescription_id"]
            second["snapshot"].update(as_of="2026-11-05", activities=[{"id": "week-two-ride", "paired_event_id": eid, "start_date": "2026-11-03T18:00:00+00:00"}],
                                      events=[dict(self.remote.events[eid], paired_activity_id="week-two-ride")])
            second["snapshot"]["readiness"]["date"] = "2026-11-05"
            second["current_feedback"].update(date="2026-11-05", state="fatigued")
            second["observations"] = [dict(source["observations"][0], session_id="intervals-two", prescription_id=pid,
                                           activity_id="week-two-ride", response="unexpectedly_hard", date="2026-11-04")]
            change = self.revision("week-two-adjustment")
            replacement = copy.deepcopy(self.source["sessions"][2])
            replacement.update(session_id="long-two", session_budget_minutes=60)
            replacement["workout"]["date"] = "2026-11-07"
            spec = replacement["workout"]["coaching_prescription"]
            spec.update(session_template="AE-1", available_minutes=60)
            spec["steps"][0]["seconds"] = 3600
            change["sessions"] = [replacement if s["session_id"] == "long-two" else s for s in change["sessions"]]
            change["weeks"][1]["session_windows"][2]["max_minutes"] = 60
            second["candidate_plan"] = change
            second["decisions"] = [{"action": "reduce", "session_ids": ["long-two"], "observation_ids": ["intervals-two"],
                                     "reason": "Unexpectedly costly intervals and reduced weekend availability", "next_observation": "Review recovery and the shorter easy ride"}]
            result = self.store.review(second)
            self.assertTrue(result["revision_created"])
            self.assertEqual(self.store.show()["plan"]["weeks"][1]["session_windows"][2]["max_minutes"], 60)
            second["parent_revision"] = result["revision_id"]
            self.assertTrue(self.store.review(second)["unchanged"])

    def test_feedback_date_cannot_make_old_training_a_current_repeated_difficulty_pattern(self):
        self.source["sessions"][1]["workout"] = copy.deepcopy(self.source["sessions"][0]["workout"])
        self.source["sessions"][1]["workout"]["date"] = "2026-10-28"
        self.source["weeks"][0]["session_windows"][1]["date"] = "2026-10-28"
        source = self.ready()
        source.update(assessed_date="2026-12-10")
        source["snapshot"].update(as_of="2026-12-10")
        source["snapshot"]["readiness"]["date"] = "2026-12-10"
        source["current_feedback"]["date"] = "2026-12-10"
        source["observations"][0].update(response="unexpectedly_hard", date="2026-12-10")
        eid = self.store.bindings()["easy-short"]["event_id"]
        pid = self.store.bindings()["easy-short"]["prescription_id"]
        source["snapshot"]["activities"].append({"id": "older-hard", "paired_event_id": eid, "start_date": "2026-10-28T18:00:00+00:00"})
        source["snapshot"]["events"].append(dict(self.remote.events[eid], paired_activity_id="older-hard"))
        source["observations"].append(dict(source["observations"][0], session_id="easy-short", prescription_id=pid, activity_id="older-hard"))
        with mock.patch.object(plans, "today", return_value="2026-12-10"):
            result = self.store.review(source)
        self.assertEqual(result["report"]["response_patterns"], [])
        self.assertEqual(result["report"]["observations"][0]["execution_date"], "2026-10-27")


if __name__ == "__main__":
    unittest.main()
