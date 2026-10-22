"""Intensity-distribution labels are context, not automatic training failures."""
import unittest

from _harness import (SYNC_PATH, install_verb_guard, load_module_by_path,
                      restore_verb_guard)

mod = load_module_by_path("s11_training_distribution", SYNC_PATH)
originals = None


def setUpModule():
    global originals
    originals = install_verb_guard(mod.requests)


def tearDownModule():
    restore_verb_guard(mod.requests, originals)


class TrainingDistribution(unittest.TestCase):
    def setUp(self):
        self.sync = object.__new__(mod.IntervalsSync)

    def metrics(self, drift):
        return {"capability": {"tid_comparison": {
            "drift": drift, "pi_7d": 1.8, "pi_28d": 2.5,
            "classification_7d": "Pyramidal", "classification_28d": "Polarized"}}}

    def decide(self, metrics, alerts):
        return self.sync._compute_readiness_decision(metrics, alerts, {}, [], {}, 0)

    def test_distribution_changes_are_informational_not_fatigue_warnings(self):
        for drift in ("shifting", "acute_depolarization"):
            with self.subTest(drift=drift):
                metrics = self.metrics(drift)
                alerts = self.sync._generate_alerts(metrics, [], 0, 0)
                notice = next(a for a in alerts if a["metric"] == "tid_distribution")
                self.assertEqual((notice["severity"], notice["tier"]), ("info", 3))
                self.assertEqual(self.decide(metrics, alerts)["recommendation"], "go")

    def test_moderate_time_does_not_raise_a_fatigue_alert_by_itself(self):
        metrics = {"grey_zone_percentage": 30, "quality_intensity_percentage": 5,
                   "easy_time_ratio": .65, "hard_days_this_week": 1}
        alerts = self.sync._generate_alerts(metrics, [], 0, 0)
        self.assertEqual(alerts, [])
        self.assertEqual(self.decide(metrics, alerts)["recommendation"], "go")

    def test_distribution_notice_does_not_relax_a_safety_stop(self):
        metrics = self.metrics("acute_depolarization")
        metrics["recovery_index"] = .5
        alerts = self.sync._generate_alerts(metrics, [], 0, 0)
        result = self.decide(metrics, alerts)
        self.assertEqual((result["recommendation"], result["priority"]), ("skip", 0))
        self.assertIn("recovery_index", result["alarm_refs"])

    def test_consistent_distribution_is_not_an_extra_notice(self):
        metrics = self.metrics("consistent")
        self.assertEqual(self.sync._generate_alerts(metrics, [], 0, 0), [])
