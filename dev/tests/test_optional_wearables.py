"""Optional wearable inputs must remain distinct from adverse observations."""
import copy
import json
import unittest

from _harness import (REPO_ROOT, SYNC_PATH, install_verb_guard,
                      load_module_by_path, restore_verb_guard)

mod = load_module_by_path("s11_optional_wearables", SYNC_PATH)
originals = None


def setUpModule():
    global originals
    originals = install_verb_guard(mod.requests)


def tearDownModule():
    restore_verb_guard(mod.requests, originals)


class OptionalWearables(unittest.TestCase):
    def setUp(self):
        # These decision functions require no filesystem, credentials or network.
        self.sync = object.__new__(mod.IntervalsSync)
        self.metrics = {
            "latest_rhr": 50, "rhr_baseline_7d": 50,
            "acwr_start_of_day": {"value": 1.0, "as_of_date": "2026-10-22"},
        }

    def decide(self, metrics=None, wellness=None, alerts=None, tsb=0, race=None):
        return self.sync._compute_readiness_decision(
            self.metrics if metrics is None else metrics,
            alerts or [], wellness or {}, [], race or {}, tsb)

    def test_missing_overnight_hrv_ri_and_sleep_do_not_restrict(self):
        before = copy.deepcopy(self.metrics)
        result = self.decide()
        self.assertEqual((result["recommendation"], result["priority"]), ("go", 3))
        for signal in ("hrv", "ri", "sleep"):
            self.assertEqual(result["signals"][signal]["status"], "unavailable")
        self.assertEqual(result["input_context"]["available_signals"], ["acwr", "rhr", "tsb"])
        self.assertEqual(result["input_context"]["unavailable_signals"], ["hrv", "ri", "sleep"])
        self.assertFalse(result["input_context"]["wearables_required"])
        self.assertEqual(self.metrics, before)

    def test_optional_nights_can_alternate_without_recovery_wait(self):
        measured = dict(self.metrics, latest_hrv=60, hrv_baseline_7d=60, recovery_index=1.0)
        for metrics in (measured, self.metrics, self.metrics, measured):
            result = self.decide(metrics)
            self.assertEqual(result["recommendation"], "go")
            self.assertEqual(result["input_context"]["evidence_status"], "some_signals_available")

    def test_rhr_is_optional_too(self):
        result = self.decide(metrics={"acwr_start_of_day": {"value": 1.0}})
        self.assertEqual(result["recommendation"], "go")
        self.assertIn("rhr", result["input_context"]["unavailable_signals"])

    def test_no_signals_does_not_claim_physiological_green_light(self):
        result = self.decide(metrics={}, tsb=None)
        self.assertEqual(result["recommendation"], "go")  # Backward-compatible category.
        self.assertEqual(result["input_context"]["evidence_status"], "no_signals_available")
        self.assertEqual(result["input_context"]["available_signals"], [])
        self.assertEqual(len(result["input_context"]["unavailable_signals"]), 6)
        self.assertNotIn("green light", result["reason"].lower())

    def test_adverse_rhr_still_modifies_without_hrv(self):
        result = self.decide(dict(self.metrics, latest_rhr=56))
        self.assertEqual(result["signals"]["rhr"]["status"], "red")
        self.assertEqual((result["recommendation"], result["priority"]), ("modify", 2))

    def test_measured_short_sleep_still_modifies(self):
        result = self.decide(wellness={"sleepSecs": 4 * 3600})
        self.assertEqual(result["signals"]["sleep"]["status"], "red")
        self.assertEqual(result["recommendation"], "modify")

    def test_existing_p0_stops_are_preserved_and_annotated(self):
        cases = [
            (dict(self.metrics, recovery_index=0.5), []),
            (self.metrics, [{"tier": 1, "severity": "alarm", "metric": "rhr"}]),
        ]
        for metrics, alerts in cases:
            with self.subTest(alerts=alerts):
                result = self.decide(metrics, alerts=alerts)
                self.assertEqual((result["recommendation"], result["priority"]), ("skip", 0))
                self.assertEqual(result["input_context"]["policy_version"], "optional_wearables_v1")
                self.assertNotIn("tsb", result["input_context"]["available_signals"])
                self.assertNotIn("tsb", result["input_context"]["unavailable_signals"])

    def test_existing_p1_stop_is_preserved(self):
        metrics = dict(self.metrics, latest_rhr=54,
                       acwr_start_of_day={"value": 1.6, "as_of_date": "2026-10-22"})
        result = self.decide(metrics)
        self.assertEqual((result["recommendation"], result["priority"]), ("skip", 1))
        self.assertIn("input_context", result)

    def test_sdnn_is_not_substituted_for_rmssd(self):
        result = self.decide(wellness={"hrvSDNN": 60})
        self.assertEqual(result["signals"]["hrv"]["reason"], "rmssd_missing_sdnn_available")
        self.assertIn("hrv", result["input_context"]["unavailable_signals"])
        self.assertEqual(result["recommendation"], "go")

    def test_synthetic_export_illustrates_additive_contract(self):
        path = REPO_ROOT / "examples/json-examples/latest.example.json"
        decision = json.loads(path.read_text())["readiness_decision"]
        context = decision["input_context"]
        self.assertEqual(context["policy_version"], "optional_wearables_v1")
        self.assertFalse(context["wearables_required"])
        self.assertEqual(context["available_signals"], sorted(decision["signals"]))
        self.assertEqual(context["unavailable_signals"], [])
