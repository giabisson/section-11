"""Dated readiness inputs, calendar persistence and non-operative signal audit."""
import copy
import unittest
from datetime import datetime
from unittest import mock

from _harness import (SYNC_PATH, install_verb_guard, load_module_by_path,
                      restore_verb_guard)

mod = load_module_by_path("s11_readiness_quality", SYNC_PATH)
originals = None


def setUpModule():
    global originals
    originals = install_verb_guard(mod.requests)


def tearDownModule():
    restore_verb_guard(mod.requests, originals)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 22, 12, tzinfo=tz)


def row(day, hrv=None, rhr=None, sleep=None):
    return {"id": "2026-10-" + str(day).zfill(2),
            "hrv": hrv, "restingHR": rhr, "sleepSecs": sleep}


class ReadinessQuality(unittest.TestCase):
    def setUp(self):
        self.sync = object.__new__(mod.IntervalsSync)
        patch = mock.patch.object(mod, "datetime", Clock)
        patch.start()
        self.addCleanup(patch.stop)

    def metrics(self, rows):
        result = self.sync._readiness_wellness_metrics(rows)
        result["acwr_start_of_day"] = {"value": 1.0, "as_of_date": "2026-10-22"}
        return result

    def decide(self, metrics, wellness=None, health=None, alerts=None):
        return self.sync._compute_readiness_decision(
            metrics, alerts or [], wellness or {}, [], {}, 0, health_context=health)

    def test_prior_days_exclude_today_and_duplicates_do_not_inflate_coverage(self):
        rows = [row(22, 120, 60), row(20, 60, 50), row(18, 80, 52), row(20, 60, 50)]
        before = copy.deepcopy(rows)
        values = self.metrics(rows)
        baseline = values["readiness_observations"]["hrv"]["baseline_7d"]
        self.assertEqual((baseline["mean"], baseline["sample_days"]), (70, 2))
        self.assertEqual(baseline["coverage"], .286)
        self.assertEqual((baseline["window_start"], baseline["window_end"]),
                         ("2026-10-15", "2026-10-21"))
        self.assertEqual(values["latest_hrv"], 120)
        self.assertEqual(rows, before)

    def test_current_reading_cannot_supply_its_own_baseline(self):
        values = self.metrics([row(22, 60, 50)])
        self.assertEqual(values["latest_hrv"], 60)
        self.assertIsNone(values["recovery_index"])
        observation = values["readiness_observations"]["hrv"]
        self.assertEqual(observation["value"], 60)
        self.assertEqual(observation["status"], "current")
        self.assertFalse(observation["readiness_eligible"])
        self.assertEqual(self.decide(values)["recommendation"], "go")

    def test_one_prior_hrv_does_not_require_more_measured_nights(self):
        values = self.metrics([row(16, 60, 50), row(22, 60, 50)])
        obs = values["readiness_observations"]["hrv"]
        self.assertEqual(obs["baseline_7d"]["status"], "single_observation")
        self.assertTrue(obs["readiness_eligible"])
        self.assertEqual(self.decide(values)["recommendation"], "go")
        self.assertIsNone(obs["device"])
        self.assertIsNone(obs["measurement_protocol"])

    def test_missing_current_night_does_not_reuse_an_older_low_hrv(self):
        values = self.metrics([row(20, 60, 50), row(21, 20, 50), row(22, rhr=50)])
        obs = values["readiness_observations"]["hrv"]
        self.assertEqual(obs["status"], "stale")
        self.assertEqual(obs["last_observation_date"], "2026-10-21")
        self.assertIsNone(values["latest_hrv"])
        self.assertIsNone(values["recovery_index"])
        self.assertEqual(self.decide(values)["recommendation"], "go")

    def test_stale_sleep_is_not_a_todays_fatigue_signal(self):
        rows = [row(20, rhr=50), row(21, rhr=50, sleep=3 * 3600), row(22, rhr=50)]
        result = self.decide(self.metrics(rows), wellness=rows[1])
        self.assertEqual(result["signals"]["sleep"]["status"], "unavailable")
        self.assertEqual(result["recommendation"], "go")

    def test_explicitly_stale_legacy_sleep_is_also_excluded(self):
        result = self.decide({}, wellness=row(21, sleep=3 * 3600))
        self.assertEqual(result["signals"]["sleep"]["status"], "unavailable")
        self.assertEqual(result["input_context"]["observation_quality"], "not_provided")

    def test_stale_sleep_quality_and_sdnn_are_not_described_as_current(self):
        values = self.metrics([row(22, rhr=50)])
        wellness = dict(row(21, sleep=3 * 3600), hrvSDNN=70, sleepQuality=4)
        result = self.decide(values, wellness=wellness)
        self.assertIsNone(result["signals"]["sleep"]["quality"])
        self.assertNotIn("reason", result["signals"]["hrv"])

    def test_current_sleep_still_modifies_without_hrv(self):
        values = self.metrics([row(22, sleep=3 * 3600)])
        result = self.decide(values)
        self.assertEqual(result["signals"]["sleep"]["status"], "red")
        self.assertEqual(result["recommendation"], "modify")

    def test_previous_ri_requires_yesterdays_date_not_previous_array_position(self):
        values = self.metrics([row(18, 100, 50), row(20, 65, 50), row(22, 50, 50)])
        self.assertIsNone(values["recovery_index_yesterday"])
        self.assertIsNotNone(values["recovery_index"])

    def test_yesterday_ri_uses_its_own_prior_baseline(self):
        values = self.metrics([row(19, 100, 50), row(21, 60, 50), row(22, 80, 50)])
        self.assertEqual(values["recovery_index_yesterday"], .6)
        self.assertEqual(values["recovery_index"], 1.0)

    def test_conflicting_dates_are_excluded_per_metric(self):
        values = self.metrics([row(20, 60, 50), row(20, 80, 50), row(21, 60, 50),
                               row(22, 60, 50), row(22, 30, 50)])
        obs = values["readiness_observations"]
        self.assertEqual(obs["hrv"]["status"], "conflicting")
        self.assertEqual(obs["hrv"]["baseline_7d"]["sample_days"], 1)
        self.assertEqual(obs["rhr"]["baseline_7d"]["sample_days"], 2)
        self.assertIsNone(values["recovery_index"])
        self.assertEqual(self.decide(values)["recommendation"], "go")

    def test_invalid_future_and_undated_values_cannot_trigger_decisions(self):
        rows = [row(20, 60, 50), row(23, 10, 100), {"hrv": 10, "restingHR": 100}]
        for invalid in (True, "45", float("inf"), float("nan"), -1):
            with self.subTest(value=invalid):
                values = self.metrics(rows + [row(22, invalid, invalid)])
                obs = values["readiness_observations"]
                self.assertEqual(obs["invalid_date_rows"], 1)
                self.assertEqual(obs["future_rows_excluded"], 1)
                self.assertEqual(obs["hrv"]["status"], "invalid")
                self.assertEqual(obs["rhr"]["status"], "invalid")
                self.assertIsNone(values["recovery_index"])
                self.assertEqual(self.decide(values)["recommendation"], "go")

    def test_baseline_window_does_not_expand_to_find_old_measurements(self):
        values = self.metrics([row(14, 60, 50), row(22, 60, 50)])
        obs = values["readiness_observations"]["hrv"]
        self.assertEqual(obs["baseline_7d"]["sample_days"], 0)
        self.assertEqual(obs["baseline_28d"]["sample_days"], 1)
        self.assertFalse(obs["readiness_eligible"])
        self.assertEqual(self.decide(values)["recommendation"], "go")

    def test_rounded_zero_baseline_does_not_cause_division_by_zero(self):
        values = self.metrics([row(21, 60, .001), row(22, 60, 50)])
        self.assertIsNone(values["recovery_index"])
        self.assertFalse(values["readiness_observations"]["rhr"]["readiness_eligible"])

    def test_alert_persistence_stops_at_missing_dates_and_rejects_duplicates(self):
        rows = [row(18, 30, 60), row(20, 30, 60), row(22, 30, 60), row(22, 30, 60)]
        self.assertEqual(self.sync._count_hrv_low_days(rows, 60), 1)
        self.assertEqual(self.sync._count_rhr_high_days(rows, 50), 1)
        self.assertEqual(self.sync._count_hrv_low_days(rows[:-2], 60), 0)

    def test_alert_persistence_accepts_unsorted_consecutive_calendar_days(self):
        rows = [row(21, 48, 55), row(22, 48, 55), row(20, 48, 55)]
        self.assertEqual(self.sync._count_hrv_low_days(rows, 60), 3)
        self.assertEqual(self.sync._count_rhr_high_days(rows, 50), 3)

    def test_alert_generation_does_not_turn_spaced_low_hrv_into_p0(self):
        rows = [row(22, 45), row(20, 45), row(18, 45)]
        values = {"latest_hrv": 45, "hrv_baseline_7d": 60}
        alerts = self.sync._generate_alerts(values, rows, 0, 0)
        hrv = next(a for a in alerts if a["metric"] == "hrv")
        self.assertEqual((hrv["severity"], hrv["persistence_days"]), ("warning", 1))
        self.assertNotEqual(self.decide(values, alerts=alerts)["priority"], 0)

    def test_grouped_audit_exposes_duplicate_votes_without_changing_active_policy(self):
        values = {"latest_hrv": 85, "hrv_baseline_7d": 100,
                  "latest_rhr": 53, "rhr_baseline_7d": 50,
                  "recovery_index": .68, "recovery_index_yesterday": .68}
        result = self.decide(values)
        self.assertEqual(result["recommendation"], "modify")
        audit = result["signal_count_review"]
        self.assertEqual(audit["mode"], "audit_only")
        self.assertEqual(audit["groups"]["autonomic"], "amber")
        self.assertEqual(audit["counts"]["amber"], 1)
        self.assertEqual(audit["p2_candidate"], "go")

    def test_grouped_audit_never_reinterprets_p0_p1(self):
        result = self.decide({"recovery_index": .5})
        self.assertEqual((result["recommendation"], result["priority"]), ("skip", 0))
        self.assertEqual(result["signal_count_review"]["p2_candidate"], "not_evaluated_p0_p1")

    def test_health_clarification_survives_favorable_physiology(self):
        values = self.metrics([row(21, 60, 50), row(22, 60, 50)])
        for health in ({"source_status": "ok", "clarification_required": True},
                       {"source_status": "partial", "clarification_required": True}):
            result = self.decide(values, health=health)
            self.assertEqual(result["recommendation"], "go")
            self.assertTrue(result["input_context"]["health_clarification_required"])
        self.assertIsNone(self.decide(values)["input_context"]["health_clarification_required"])

    def test_health_context_never_relaxes_existing_skip(self):
        result = self.decide({"recovery_index": .5}, health={"clarification_required": False})
        self.assertEqual(result["recommendation"], "skip")

    def test_real_health_builder_current_and_recent_markers_reach_readiness(self):
        for end, field in (("2026-10-23T00:00:00", "marker_active"),
                           ("2026-10-22T00:00:00", "recent_marker")):
            events = [{"id": 1, "category": "SICK", "name": "Synthetic marker",
                       "start_date_local": "2026-10-21T00:00:00", "end_date_local": end}]
            with mock.patch.object(self.sync, "_intervals_get", return_value=events):
                health = self.sync._build_health_context([], {}, "2026-10-22", "2026-10-15")
            result = self.decide({}, health=health)
            self.assertTrue(health[field])
            self.assertTrue(result["input_context"]["health_clarification_required"])
            self.assertEqual(result["recommendation"], "go")

    def test_failed_health_fetch_is_not_interpreted_as_no_illness(self):
        with mock.patch.object(self.sync, "_intervals_get",
                               side_effect=mod.requests.exceptions.RequestException("synthetic")):
            health = self.sync._build_health_context([], {}, "2026-10-22", "2026-10-15")
        self.assertEqual(health["source_status"], "partial")
        self.assertTrue(self.decide({}, health=health)["input_context"]["health_clarification_required"])

    def test_completed_activity_feel_is_not_current_athlete_feedback(self):
        result = self.sync._compute_readiness_decision(
            {}, [], {}, [{"feel": 5}], {}, 0)
        self.assertEqual(result["recommendation"], "go")
        self.assertNotIn("feel", result["signals"])
