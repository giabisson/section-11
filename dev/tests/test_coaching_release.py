"""Event-context, current race prompts and actual shipped-module install/update."""
import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _harness import REPO_ROOT, SYNC_PATH, load_module_by_path
import test_coaching_plan as fixtures
import test_init_update_distribution as distribution

plans = fixtures.plans
sync = load_module_by_path("s11_event_release_sync", SYNC_PATH)
doctor = load_module_by_path("s11_coaching_check_tests", REPO_ROOT / "examples/agentic/coaching_check.py")


class EventContext(unittest.TestCase):
    setUp = fixtures.CoachingPlan.setUp
    propose = fixtures.CoachingPlan.propose

    def event(self):
        self.source["goals"][0].update(priority="A", date="2026-11-02")
        self.source["block"]["event_preparation"] = {
            "goal_id": self.source["goals"][0]["goal_id"], "expected_duration_minutes": 60,
            "terrain": "flat", "decisive_demands": ["Sustained power"],
            "recent_training_reference": copy.deepcopy(self.source["revision"]["evidence"]),
            "taper": {"start_date": "2026-10-26", "end_date": "2026-11-01", "reference_minutes": 250,
                      "planned_minutes": 200, "rationale": "A modest reduction suited to recent completed training",
                      "familiar_intensity": True}}
        return self.source["block"]["event_preparation"]

    def durability(self):
        row = {"source": "Synthetic matched power windows", "date": "2026-10-20", "assessment": "Comparable sustained effort",
               "assessment_seconds": 300, "power_watts": 300, "prior_minutes": 15,
               "prior_work": {"value": 100, "unit": "kJ_mechanical"}, "prior_intensity": "easy",
               "environment": "indoor", "pacing": "steady", "fueling": "fed", "conditions": "cool with fan"}
        other = dict(copy.deepcopy(row), power_watts=270, prior_minutes=120, prior_work={"value": 1000, "unit": "kJ_mechanical"})
        context = {"fresh": row, "fatigued": other, "interpretation": "Descriptive comparison; not a causal fitness estimate"}
        self.source["block"]["durability_context"] = context
        return context

    def strength(self, arrangement="replace"):
        context = {"goal": "Optional goal-specific strength", "experience": "experienced", "equipment": "gym",
                   "technique": "reviewed", "soreness": "none reported", "arrangement": arrangement,
                   "displaced_sessions": ["easy-short"] if arrangement == "replace" else [],
                   "recovery_plan": "Monitor soreness and cycling quality; preserve recovery", "evidence_certainty": "low"}
        self.source["block"]["strength_context"] = context
        return context

    def test_feasible_taper_is_not_forced_to_a_meta_analysis_subgroup_percentage(self):
        self.event()
        self.propose()
        result = self.store.show()["context_assessment"]["event"]
        self.assertEqual(result["taper"]["reduction_pct"], 20)
        self.assertIsNone(result["fixed_TSB_target"])
        self.assertFalse(result["mandatory_overload"])

    def test_event_priority_does_not_supply_a_missing_duration(self):
        self.event()["expected_duration_minutes"] = None
        self.propose()
        result = self.store.show()["context_assessment"]
        self.assertIsNone(result["event"]["expected_duration_minutes"])
        self.assertIn("priority is not duration", result["questions"][0])

    def test_taper_must_match_exact_planned_dose_and_precede_the_event(self):
        event = self.event()
        for change in ({"planned_minutes": 150}, {"end_date": "2026-11-03"}, {"reference_minutes": 100}):
            original = copy.deepcopy(event["taper"])
            event["taper"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.propose()
            event["taper"] = original

    def test_matched_durability_preserves_prior_context_without_a_kj_cutoff(self):
        self.durability()
        self.propose()
        result = self.store.show()["context_assessment"]["durability"]
        self.assertEqual(result["status"], "descriptive_comparison")
        self.assertEqual(result["power_change_pct"], -10)
        self.assertIn("not decoupling", result["scope"])

    def test_unqualified_or_incompatible_durability_is_unavailable_not_zero(self):
        original = self.durability()
        for change in ("missing", "fueling", "conditions", "method"):
            context = copy.deepcopy(original)
            if change == "missing":
                context["fatigued"] = None
            elif change == "fueling":
                context["fatigued"]["fueling"] = "unknown"
            elif change == "conditions":
                context["fatigued"]["conditions"] = "hot"
            else:
                context["fatigued"]["assessment_seconds"] = 1200
            self.source["block"]["durability_context"] = context
            self.source["revision"]["request_id"] = "durability-" + change
            self.source["revision"]["parent_revision"] = self.store.latest_id()
            self.propose()
            result = self.store.show()["context_assessment"]["durability"]
            self.assertEqual(result["status"], "unavailable_or_not_comparable")
            self.assertIsNone(result["power_change_pct"])

    def test_dietary_calories_cannot_become_mechanical_work(self):
        self.durability()["fatigued"]["prior_work"]["unit"] = "kcal"
        with self.assertRaisesRegex(ValueError, "mechanical kJ"):
            self.propose()

    def test_strength_replacement_counts_minutes_and_does_not_claim_guaranteed_transfer(self):
        self.strength()
        self.source["sessions"][1]["workout"] = {"name": "Synthetic strength", "date": "2026-10-29", "type": "WeightTraining", "duration_minutes": 30}
        self.propose()
        result = self.store.show()["context_assessment"]["strength"]
        self.assertEqual(result["minutes_in_total_budget"], 30)
        self.assertFalse(result["performance_guarantee"])
        self.assertFalse(result["low_cadence_is_heavy_strength"])
        self.assertEqual(result["evidence_certainty"], "low")

    def test_added_strength_cannot_bypass_combined_availability(self):
        self.strength("add")
        s = copy.deepcopy(self.source["sessions"][1])
        s.update(session_id="strength", session_budget_minutes=60)
        s["workout"] = {"name": "Synthetic added strength", "date": "2026-10-28", "type": "WeightTraining", "duration_minutes": 60}
        self.source["sessions"].append(s)
        self.source["weeks"][0]["session_windows"].append({"date": "2026-10-28", "max_minutes": 60})
        with self.assertRaisesRegex(ValueError, "weekly availability"):
            self.propose()

    def test_unknown_strength_preparation_prompts_context_without_a_cycling_veto(self):
        self.strength()["technique"] = "unknown"
        self.propose()
        result = self.store.show()["context_assessment"]
        self.assertIn("cycling can continue", result["questions"][0])

    def test_race_week_does_not_manufacture_a_ctl_budget_or_priority_duration(self):
        instance = object.__new__(sync.IntervalsSync)
        for duration in (None, True, -1, float("nan"), "3600"):
            race = {"date": "2026-10-25", "days_until": 3, "category": "RACE_A", "name": "Synthetic race", "moving_time_seconds": duration}
            result = instance._build_race_week(race, 200, 220, -20, [], sync.datetime(2026, 10, 22).date())
            self.assertEqual(result["event_duration_class"], "unknown")
            self.assertIsNone(result["race_week_tss_budget"])
            self.assertIsNone(result["race_week_tss_remaining"])
            self.assertIsNone(result["normal_weekly_tss"])
            self.assertIsNone(result["carb_loading"]["applicable"])
            self.assertIsNone(result["today"]["load_target_tss"])

    def test_known_short_and_long_priority_events_still_have_individualized_dose(self):
        instance = object.__new__(sync.IntervalsSync)
        for duration, klass in ((3600, "short_intense"), (18000, "long_endurance")):
            race = {"date": "2026-10-24", "days_until": 2, "category": "RACE_A", "name": "Synthetic race", "moving_time_seconds": duration}
            result = instance._build_race_week(race, 0, 0, 0, [], sync.datetime(2026, 10, 22).date())
            self.assertEqual(result["event_duration_class"], klass)
            self.assertIsNone(result["tsb_target_range"])
            self.assertEqual(result["opener"]["intensity"], "individualize_familiar_efforts")
            alerts = instance._generate_race_alerts({"race_week": result})
            self.assertFalse(any(a["metric"] == "race_week_tsb" for a in alerts))
            self.assertFalse(any("0-0 TSS" in a["context"] for a in alerts))


class CoachingDistribution(unittest.TestCase):
    def bundle(self):
        names = ["examples/agentic/" + n for n in doctor.REQUIRED] + ["examples/training_history.py", "examples/workout-library/WORKOUT_REFERENCE.md", "examples/workout-library/workout_constraints.json"]
        return {n: (REPO_ROOT / n).read_bytes() for n in names}

    def test_generator_never_reads_publisher_copies_or_lists_private_records(self):
        tree = self.bundle()
        tree.update({"literature/cycling-training/sources/one/paper.pdf": b"private publisher copy",
                     "literature/cycling-training/papers/one/takeaways.md": b"our summary",
                     "private/coaching_plan.sqlite3": b"private athlete state", "coaching_decisions.jsonl": b"private decisions",
                     "private/facts.sqlite3": b"private history", "private/athlete_intake.sqlite3": b"private intake", "training-history-primary/summary.json": b"private summary"})
        raw = distribution.run_generator(tree)
        names = json.loads(raw)["files"]
        self.assertFalse(any("/sources/" in n or "sqlite3" in n or n.endswith("coaching_decisions.jsonl") for n in names))
        self.assertIn("literature/cycling-training/papers/one/takeaways.md", names)
        self.assertNotIn("training-history-primary/summary.json", names)

    def test_actual_coaching_modules_survive_fresh_init_and_work_from_installed_paths(self):
        tree = self.bundle()
        manifest = distribution.manifest_for(tree)
        result = distribution.run_init(distribution.repo_archive(manifest=manifest, files=tree))
        for name, value in tree.items():
            self.assertEqual(result.installed[name], value)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "section11"
            distribution.write_tree(root, result.installed)
            module = load_module_by_path("s11_installed_coaching_plan", root / "examples/agentic/coaching_plan.py")
            local_push = module.push_module()
            local_validator = local_push._load_workout_validator()
            with mock.patch.object(module, "datetime", fixtures.Clock), mock.patch.object(local_push, "datetime", fixtures.Clock), mock.patch.object(local_validator, "datetime", fixtures.Clock):
                store = module.PlanStore(Path(folder) / "private", create=True)
                try:
                    store.propose(json.loads(fixtures.FIXTURE.read_text()))
                    self.assertEqual(len(store.summary()["prescription_summaries"]), 3)
                    self.assertEqual(local_validator.catalog()["library_version"], "0.9.0")
                    review = json.loads((REPO_ROOT / "examples/json-examples/coaching_review.example.json").read_text())
                    review.update(review_id="installed-review", parent_revision=store.latest_id(), assessed_date="2026-10-22",
                                  period={"start": "2026-10-22", "end": "2026-10-22"}, observations=[], candidate_plan=None)
                    review["snapshot"].update(as_of="2026-10-22", activities=[], events=[])
                    review["snapshot"]["readiness"]["date"] = "2026-10-22"
                    review["current_feedback"]["date"] = "2026-10-22"
                    review["decisions"] = [{"action": "maintain", "session_ids": [], "observation_ids": [],
                                             "reason": "Retain the prepared plan", "next_observation": "Review completed training"}]
                    self.assertEqual(store.review(review)["calendar_writes"], 0)
                finally:
                    store.close()
            checked = doctor.check(root, Path(folder) / "private")
            self.assertTrue(checked["bundle_ready"])
            self.assertFalse(checked["live_runtime_verified"])

    def test_actual_bundle_update_adds_dependencies_and_preserves_private_siblings(self):
        tree = self.bundle()
        manifest = distribution.manifest_for(tree)
        files = {"section11/examples/agentic/push.py": b"old copied push", "athlete-private/coaching_plan.sqlite3": b"do not touch"}
        def get(url, **kwargs):
            name = url[len(distribution.sync_mod.SECTION11_REPO_RAW) + 1:]
            return distribution.FakeResponse(tree[name])
        patch = mock.patch.object(distribution.requests, "get", side_effect=get)
        result = distribution.run_update(files, ["y"], manifest=manifest, patches=(patch,), interactive=False)
        for name, value in tree.items():
            self.assertEqual(result.files["section11/" + name], value)
        self.assertEqual(result.files["athlete-private/coaching_plan.sqlite3"], b"do not touch")

    def test_private_or_publisher_records_in_an_explicit_archive_manifest_are_rejected(self):
        for name in ("coaching_plan.sqlite3", "athlete_intake.sqlite3", "literature/cycling-training/sources/one/paper.pdf"):
            tree = {"README.md": b"safe", name: b"excluded"}
            result = distribution.run_init(distribution.repo_archive(manifest=distribution.manifest_for(tree), files=tree))
            self.assertEqual(result.installed, {})

    def test_doctor_does_not_infer_live_runtime_from_files_or_fictional_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tree = self.bundle()
            distribution.write_tree(root, tree)
            (root / "manifest.json").write_text(json.dumps(distribution.manifest_for(tree)))
            (root / "HEARTBEAT.md").write_text("Illustrative instructions only")
            report = doctor.check(root, workspace=root)
            self.assertTrue(report["bundle_ready"])
            self.assertFalse(report["live_runtime_verified"])
            self.assertEqual(report["calendar_writes"], 0)
            self.assertEqual(report["messages_sent"], 0)
            report = doctor.check(root, latest_json=REPO_ROOT / "examples/json-examples/latest.example.json")
            self.assertFalse(report["bundle_ready"])

    def test_doctor_detects_incomplete_dependencies_hash_drift_and_missing_data_without_setup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tree = self.bundle()
            distribution.write_tree(root, tree)
            (root / "manifest.json").write_text(json.dumps(distribution.manifest_for(tree)))
            (root / "examples/agentic/coaching_review.py").unlink()
            absent = root / "not-created"
            report = doctor.check(root, data_dir=absent)
            self.assertFalse(report["bundle_ready"])
            self.assertFalse(absent.exists())


if __name__ == "__main__":
    unittest.main()
