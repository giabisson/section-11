"""Checked dose, denominator provenance, budgets and the pre-write boundary."""
import copy
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from _harness import (PUSH_PATH, REPO_ROOT, SYNC_PATH, RefuseEverything, load_module_by_path)

validator = load_module_by_path("s11_workout_validation_tests", PUSH_PATH.with_name("workout_validation.py"))
push = load_module_by_path("s11_push_validation_tests", PUSH_PATH)
sync_mod = load_module_by_path("s11_ftp_provenance_tests", SYNC_PATH)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 22, 12, tzinfo=tz)


def reference():
    return {"metric": "ftp", "value_watts": 250, "date": "2026-10-01",
            "method": "synthetic_test", "equipment": "synthetic_trainer", "environment": "indoor",
            "source": "synthetic fixture", "status": "current",
            "zone_bounds_watts": {"1": [0, 150], "2": [150, 200], "3": [200, 230],
                                  "4": [230, 265], "5": [265, 315], "6": [315, 400], "7": [400, 1000]}}


def step(role, seconds, zone=1, watts=125):
    return {"role": role, "seconds": seconds,
            "target": {"basis": "watts", "low": watts, "zones": [zone]}}


def workout(template="VO2-2", reps=10, sets=2, final_recovery=True):
    pair = [step("work", 30, 5, 300), step("recovery", 15)]
    group = [{"repeat": reps, "steps": pair}] if final_recovery else [
        {"repeat": reps - 1, "steps": pair}, step("work", 30, 5, 300)]
    main = []
    for i in range(sets):
        if i:
            main.append(step("set_recovery", 300))
        main.extend(copy.deepcopy(group))
    cooldown = 1800 if template == "VO2-5" else 600
    return {"name": "Synthetic checked workout", "date": "2026-10-27", "indoor": True,
            "coaching_prescription": {"schema_version": 1, "session_template": template,
                "template_version": "0.9.0", "available_minutes": 100,
                "fitness_reference": reference(),
                "steps": [step("warmup", 1140), step("warmup", 60, 4, 250)]
                         + main + [step("cooldown", cooldown)]}}


class WorkoutValidation(unittest.TestCase):
    def setUp(self):
        for module in (validator, push, sync_mod):
            patch = mock.patch.object(module, "datetime", Clock)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(push, "_workout_validator", validator)
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch.object(push, "_requests", RefuseEverything())
        patch.start()
        self.addCleanup(patch.stop)
        self.pusher = push.IntervalsPush("123", "synthetic")

    def compile(self, value):
        return validator.compile_workout(value)

    def test_complete_30_15_duration_includes_all_recoveries(self):
        original = workout()
        before = copy.deepcopy(original)
        prepared, report = self.compile(original)
        self.assertEqual(report["total_seconds"], 3000)
        self.assertEqual(report["work_seconds"], 600)
        self.assertEqual(report["recovery_seconds"], 600)
        self.assertEqual(prepared["duration_minutes"], 50)
        self.assertEqual(original, before)

    def test_final_recovery_is_explicit_not_silently_omitted(self):
        _, report = self.compile(workout(final_recovery=False))
        self.assertEqual(report["total_seconds"], 2970)
        self.assertEqual(report["recovery_seconds"], 570)

    def test_high_volume_30_15_uses_library_rest_not_assumed_paper_rest(self):
        _, report = self.compile(workout("VO2-5", 13, 3))
        self.assertEqual(report["total_seconds"], 5355)
        self.assertEqual(report["work_seconds"], 1170)
        self.assertEqual(report["recovery_seconds"], 1185)
        self.assertFalse(report["evidence"][0]["protocol_match"])

    def test_budget_and_declared_duration_are_checked_against_full_steps(self):
        for field, value in (("budget", 49), ("declared", 45)):
            item = workout()
            if field == "budget":
                item["coaching_prescription"]["available_minutes"] = value
            else:
                item["duration_minutes"] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.compile(item)

    def test_reduced_tempo_fits_one_hour_without_fabricated_template(self):
        item = workout()
        spec = item["coaching_prescription"]
        spec["session_template"] = "SS-4"
        spec["available_minutes"] = 60
        spec["steps"] = [step("warmup", 900), step("work", 900, 3, 220),
                         step("recovery", 300), step("work", 900, 3, 220), step("cooldown", 600)]
        _, report = self.compile(item)
        self.assertEqual(report["total_seconds"], 3600)

    def test_recovery_and_repetition_constraints_are_not_just_labels(self):
        for kind in ("rest", "repetitions", "zones"):
            item = workout()
            repeat = item["coaching_prescription"]["steps"][2]
            if kind == "rest":
                repeat["steps"][1]["seconds"] = 10
            elif kind == "repetitions":
                repeat["repeat"] = 11
            else:
                repeat["steps"][0] = step("work", 30, 3, 220)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.compile(item)

    def test_warmup_primer_and_full_cooldown_are_guarded(self):
        for kind in ("primer", "cooldown"):
            item = workout()
            if kind == "primer":
                item["coaching_prescription"]["steps"][1] = step("warmup", 60)
            else:
                item["coaching_prescription"]["steps"][-1]["seconds"] = 60
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.compile(item)

    def test_unsupported_template_and_wrong_version_fail_explicitly(self):
        for field, value in (("session_template", "UNKNOWN"), ("template_version", "0.7.1")):
            item = workout()
            item["coaching_prescription"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.compile(item)

    def test_catalog_is_bound_to_the_installed_library(self):
        wrong = validator.catalog()
        wrong["library_sha256"] = "0" * 64
        with mock.patch.object(validator.json, "loads", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "does not match"):
                self.compile(workout())

    def test_root_script_installation_finds_the_section11_mirror(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "section11/examples/workout-library"
            folder.mkdir(parents=True)
            (folder / "workout_constraints.json").write_text("{}")
            (folder / "WORKOUT_REFERENCE.md").write_text("Synthetic path-discovery fixture")
            self.assertEqual(validator.catalog_location(root), folder / "workout_constraints.json")

    def test_root_installation_does_not_read_an_unrelated_parent_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "athlete"
            own = root / "workout-library"
            foreign = root.parent / "workout-library"
            for folder in (own, foreign):
                folder.mkdir(parents=True)
                (folder / "workout_constraints.json").write_text("{}")
                (folder / "WORKOUT_REFERENCE.md").write_text("Path fixture")
            self.assertEqual(validator.catalog_location(root), own / "workout_constraints.json")

    def test_peak_power_percentage_resolves_as_peak_power_not_ftp(self):
        item = workout()
        spec = item["coaching_prescription"]
        spec["fitness_reference"].update(metric="ramp_peak_power", value_watts=350)
        target = spec["steps"][2]["steps"][0]["target"]
        target.update(basis="ramp_peak_power", low=100, zones=[6])
        prepared, _ = self.compile(item)
        self.assertIn("work 30s 350w", prepared["description"])
        target["basis"] = "ftp"
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.compile(item)

    def test_absolute_saved_targets_are_not_rescaled(self):
        item = workout()
        item["coaching_prescription"]["fitness_reference"]["value_watts"] = 270
        prepared, _ = self.compile(item)
        self.assertIn("work 30s 300w", prepared["description"])

    def test_unknown_method_equipment_and_date_are_visible_not_invented(self):
        item = workout()
        ref = item["coaching_prescription"]["fitness_reference"]
        ref.update(date=None, method=None, equipment=None)
        _, report = self.compile(item)
        self.assertEqual(len(report["warnings"]), 3)
        self.assertIsNone(report["fitness_reference"]["date"])

    def test_stale_or_contradictory_reference_needs_explicit_current_review(self):
        for status in ("stale", "contradictory"):
            item = workout()
            ref = item["coaching_prescription"]["fitness_reference"]
            ref["status"] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.compile(item)
            ref["review"] = {"date": "2026-10-22", "decision": "use_provisionally",
                             "reason": "Synthetic coach reconciled the discrepancy with repeatable trainer efforts"}
            _, report = self.compile(item)
            self.assertTrue(any("provisional" in w for w in report["warnings"]))

    def test_future_dates_environment_mismatch_and_review_expiry_are_checked(self):
        for change in ({"date": "2026-10-23"}, {"environment": "outdoor"}, {"review_after": "2026-10-21"}):
            item = workout()
            item["coaching_prescription"]["fitness_reference"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_zone_bounds_are_required_not_inferred_from_ftp(self):
        item = workout()
        del item["coaching_prescription"]["fitness_reference"]["zone_bounds_watts"]
        with self.assertRaisesRegex(ValueError, "zone_bounds"):
            self.compile(item)

    def test_recovery_template_does_not_allow_z2_hidden_in_cooldown(self):
        item = workout()
        spec = item["coaching_prescription"]
        spec["session_template"] = "AE-4"
        spec["steps"] = [step("work", 1800), step("cooldown", 600, 2, 175)]
        with self.assertRaisesRegex(ValueError, "recovery target"):
            self.compile(item)

    def test_target_outside_declared_zone_is_rejected(self):
        item = workout()
        item["coaching_prescription"]["steps"][2]["steps"][0]["target"]["low"] = 500
        with self.assertRaisesRegex(ValueError, "outside"):
            self.compile(item)

    def test_downward_ramp_retains_direction(self):
        item = workout()
        item["coaching_prescription"]["steps"][-1]["target"].update(low=100, high=140, ramp="down")
        prepared, _ = self.compile(item)
        self.assertIn("ramp 140-100w", prepared["description"])

    def test_rendered_description_cannot_replace_checked_steps(self):
        item = workout()
        item["description"] = "- 1s 900w"
        with self.assertRaisesRegex(ValueError, "description differs"):
            self.compile(item)

    def test_recompile_canonical_preview_is_idempotent(self):
        first, report1 = self.compile(workout())
        second, report2 = self.compile(first)
        self.assertEqual(first, second)
        self.assertEqual(report1, report2)

    def test_repeat_and_depth_limits_prevent_unbounded_expansion(self):
        for repeat in (2001, True, -1):
            item = workout()
            item["coaching_prescription"]["steps"][2]["repeat"] = repeat
            with self.subTest(repeat=repeat), self.assertRaises(ValueError):
                self.compile(item)
        item = workout()
        nested = step("work", 30, 5, 300)
        for _ in range(6):
            nested = {"repeat": 1, "steps": [nested]}
        item["coaching_prescription"]["steps"] = [nested]
        with self.assertRaisesRegex(ValueError, "nesting"):
            self.compile(item)

    def test_nonfinite_and_boolean_numeric_inputs_fail_before_network(self):
        for field, value in (("duration_minutes", float("nan")), ("tss", float("inf")), ("duration_minutes", True)):
            item = {"name": "Legacy", "date": "2026-10-27", field: value}
            with self.subTest(field=field, value=value):
                self.assertFalse(self.pusher.preview_push([item])["success"])
                self.assertEqual(self.pusher.push_workouts([item])["outcome"], "not_applied")

    def test_preview_reports_checked_and_legacy_entries_without_http(self):
        result = self.pusher.preview_push([workout(), {"name": "Native", "date": "2026-10-27"}])
        self.assertTrue(result["success"])
        self.assertEqual([r["status"] for r in result["coaching_validation"]], ["checked", "not_checked"])
        self.assertEqual(result["summary"][0]["duration_minutes"], 50)

    def test_invalid_batch_is_rejected_before_any_read_or_write(self):
        invalid = workout()
        invalid["coaching_prescription"]["available_minutes"] = 40
        with mock.patch.object(self.pusher, "_read_event_window") as read:
            result = self.pusher.push_workouts([workout(), invalid])
        self.assertEqual(result["outcome"], "not_applied")
        read.assert_not_called()

    def test_confirmed_write_uses_exact_preview_payload_and_single_send(self):
        preview = self.pusher.preview_push([workout()])
        expected = self.pusher._build_event(preview["compiled_workouts"][0])
        with mock.patch.object(self.pusher, "_read_event_window", return_value={"success": True, "events": []}), \
             mock.patch.object(self.pusher, "_exception_types", return_value=(TimeoutError, ConnectionError, OSError, RuntimeError)), \
             mock.patch.object(self.pusher, "_post", return_value=[dict(expected, id=123)]) as send:
            result = self.pusher.push_workouts(preview["compiled_workouts"])
        self.assertEqual(result["outcome"], "applied")
        send.assert_called_once_with("events/bulk?upsert=true", [expected])
        self.assertEqual(expected["moving_time"], 3000)

    def test_every_checked_catalog_entry_has_an_executable_positive_case(self):
        powers = {1: 125, 2: 175, 3: 220, 4: 250, 5: 300, 6: 350, 7: 500}
        complex_cases = {w["coaching_prescription"]["session_template"]: w for w in json.loads(
            (REPO_ROOT / "examples/json-examples/checked_complex_workouts.example.json").read_text())}
        for template, rule in validator.catalog()["templates"].items():
            with self.subTest(template=template):
                if template in complex_cases:
                    prepared, report = self.compile(complex_cases[template])
                    self.assertEqual(report["status"], "checked")
                    self.assertEqual(prepared["duration_minutes"] * 60, report["total_seconds"])
                    continue
                item = workout()
                spec = item["coaching_prescription"]
                spec.update(session_template=template, available_minutes=800)
                warmup = rule["warmup_seconds"][0]
                cooldown = rule["cooldown_seconds"][0]
                primer = rule.get("warmup_primer")
                start = []
                if primer:
                    count, seconds = primer["count"], primer["minimum_seconds"]
                    zone = primer["zones"][0]
                    start = [step("warmup", warmup - count * seconds - (count - 1) * 120)]
                    for i in range(count):
                        if i:
                            start.append(step("warmup", 120))
                        start.append(step("warmup", seconds, zone, powers[zone]))
                elif warmup:
                    start = [step("warmup", warmup)]
                if rule["kind"] == "continuous":
                    zone = rule["work_zones"][0]
                    main = [step("work", rule["total_seconds"][0], zone, powers[zone])]
                else:
                    variant = rule["variants"][0]
                    main = []
                    for group in range(variant["sets"][0]):
                        if group:
                            main.append(step("set_recovery", variant["set_recovery_seconds"][0]))
                        sequence = variant.get("work_sequence") or [variant["work_seconds"][0]] * variant["repetitions"][0]
                        zone = variant["work_zones"][0]
                        for i, seconds in enumerate(sequence):
                            if i:
                                main.append(step("recovery", variant["recovery_seconds"][0]))
                            main.append(step("work", seconds, zone, powers[zone]))
                spec["steps"] = start + main + ([step("cooldown", cooldown)] if cooldown else [])
                prepared, report = self.compile(item)
                self.assertEqual(report["status"], "checked")
                self.assertEqual(prepared["duration_minutes"] * 60, report["total_seconds"])

    def test_checked_catalog_covers_every_library_id_without_exceptions(self):
        data = validator.catalog()
        ids = re.findall(r"^id: (\S+)$", validator.CATALOG_PATH.with_name("WORKOUT_REFERENCE.md").read_text(), re.M)
        self.assertEqual(len(ids), 26)
        self.assertEqual(set(ids), set(data["templates"]))
        self.assertEqual(data["not_yet_checked"], [])

    def complex_case(self, template):
        cases = json.loads((REPO_ROOT / "examples/json-examples/checked_complex_workouts.example.json").read_text())
        return next(w for w in cases if w["coaching_prescription"]["session_template"] == template)

    def flat_case(self, template):
        item = self.complex_case(template)
        item["coaching_prescription"]["steps"] = validator.flatten(item["coaching_prescription"]["steps"])
        return item

    def test_complex_examples_have_independently_counted_durations_and_components(self):
        expected = {"AE-5": 3600, "AE-6": 7800, "AE-7": 7200, "SS-3": 3720,
                    "VO2-3": 3240, "AN-2": 3600, "AN-3": 5430, "MIX-1": 5400,
                    "MIX-2": 2700, "SE-1": 4140, "SE-2": 3900}
        for template, seconds in expected.items():
            with self.subTest(template=template):
                item = self.complex_case(template)
                compiled, report = self.compile(item)
                self.assertEqual(report["total_seconds"], seconds)
                self.assertEqual(sum(report[f] for f in ("warmup_seconds", "work_seconds", "endurance_seconds",
                                                        "recovery_seconds", "cooldown_seconds")), seconds)
                spec = item["coaching_prescription"]
                spec["available_minutes"] = (seconds - 1) / 60
                with self.assertRaisesRegex(ValueError, "exceeds available time"):
                    self.compile(item)
                again, _ = self.compile(compiled)
                self.assertEqual(again, compiled)

    def test_cadence_drills_require_technique_and_preserve_easy_recoveries(self):
        for change in ("missing", "cadence", "power", "rest", "hidden_rest", "too_short"):
            item = self.flat_case("AE-5")
            steps = item["coaching_prescription"]["steps"]
            if change == "missing":
                del steps[1]["technique"]
            elif change == "cadence":
                steps[1]["cadence_rpm"] = 95
            elif change == "power":
                steps[1] = step("work", 300, 3, 220)
            elif change == "rest":
                steps[2]["seconds"] = 120
            elif change == "hidden_rest":
                steps[2]["role"] = "endurance"
            else:
                del steps[-2]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_single_leg_drill_variant_is_explicit_and_rendered(self):
        item = self.flat_case("AE-5")
        for s in item["coaching_prescription"]["steps"]:
            if s["role"] == "work":
                s["technique"] = "single_leg"
                del s["cadence_rpm"]
        compiled, _ = self.compile(item)
        self.assertIn("single leg 300s", compiled["description"])

    def test_fast_finish_checks_lead_duration_order_and_finish_dose(self):
        for change in ("lead", "finish", "order", "zone", "endurance_after"):
            item = self.flat_case("AE-6")
            steps = item["coaching_prescription"]["steps"]
            if change == "lead":
                steps[1]["seconds"] = 1200
            elif change == "finish":
                steps[2]["seconds"] = 1700
            elif change == "order":
                steps[1], steps[2] = steps[2], steps[1]
            elif change == "zone":
                steps[2] = step("work", 1800, 4, 250)
            else:
                steps.insert(-1, step("endurance", 60, 2, 175))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_progressive_ride_rejects_flat_decreasing_short_or_premature_tempo(self):
        for change in ("flat", "decreasing", "short", "tempo", "few", "ramp"):
            item = self.flat_case("AE-7")
            steps = item["coaching_prescription"]["steps"]
            if change == "flat":
                steps[1]["target"]["low"] = 170
            elif change == "decreasing":
                steps[1]["target"]["low"] = 160
            elif change == "short":
                steps[1]["seconds"] = 1799
            elif change == "tempo":
                steps[1] = step("work", 2400, 3, 220)
            elif change == "few":
                steps.pop()
            else:
                steps[1]["target"]["ramp"] = "up"
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_progressive_four_blocks_may_finish_in_tempo(self):
        item = self.flat_case("AE-7")
        item["coaching_prescription"]["steps"] = [step("work", 1800, 2, w) for w in [160, 175, 190]] + [step("work", 1800, 3, 210)]
        _, report = self.compile(item)
        self.assertEqual(report["total_seconds"], 7200)

    def test_over_under_sequence_block_length_and_between_block_rest_are_checked(self):
        for change in ("under", "over", "zone", "rest", "blocks"):
            item = self.flat_case("SS-3")
            steps = item["coaching_prescription"]["steps"]
            if change == "under":
                steps[1]["seconds"] = 90
            elif change == "over":
                steps[2]["seconds"] = 90
            elif change == "zone":
                steps[2] = step("work", 60, 4, 250)
            elif change == "rest":
                next(s for s in steps if s["role"] == "set_recovery")["seconds"] = 240
            else:
                del steps[1:8]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_over_under_eight_and_ten_minute_blocks_clip_only_the_last_segment(self):
        for seconds in (480, 600):
            item = self.flat_case("SS-3")
            block, remaining = [], seconds
            i = 0
            while remaining:
                duration = min(120 if i % 2 == 0 else 60, remaining)
                block.append(step("work", duration, 4 if i % 2 == 0 else 5, 250 if i % 2 == 0 else 280))
                remaining -= duration
                i += 1
            main = block + [step("set_recovery", 300)] + copy.deepcopy(block) + [step("set_recovery", 300)] + copy.deepcopy(block)
            item["coaching_prescription"]["steps"] = [step("warmup", 900)] + main + [step("cooldown", 600)]
            _, report = self.compile(item)
            self.assertEqual(report["work_seconds"], seconds * 3)
            self.assertEqual(report["recovery_seconds"], 600)

    def test_descending_rests_are_exact_and_have_no_extra_final_rest(self):
        for change in ("sequence", "extra", "missing", "work"):
            item = self.flat_case("VO2-3")
            steps = item["coaching_prescription"]["steps"]
            if change == "sequence":
                next(s for s in steps if s["role"] == "recovery")["seconds"] = 150
            elif change == "extra":
                steps.insert(-1, step("recovery", 90))
            elif change == "missing":
                del steps[-3:-1]
            else:
                next(s for s in steps if s["role"] == "work")["seconds"] = 181
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_sprints_are_free_effort_and_do_not_invent_an_ftp_target(self):
        for template, count in (("AN-2", 4), ("AN-3", 15)):
            compiled, report = self.compile(self.complex_case(template))
            lines = [line for line in compiled["description"].splitlines() if "freeride" in line]
            self.assertEqual(len(lines), count)
            self.assertTrue(all(line.endswith("10s freeride") for line in lines))
            self.assertEqual(report["rendered_target_basis"], "absolute_watts_and_free_effort")
            self.assertTrue(any("verify trainer/device" in w for w in report["warnings"]))
            self.assertTrue(all("%" not in line for line in lines))

    def test_embedded_sprints_reject_fixed_targets_late_placement_short_rest_and_bad_count(self):
        for change in ("fixed", "late", "rest", "count", "duration"):
            item = self.flat_case("AN-2")
            steps = item["coaching_prescription"]["steps"]
            first = next(i for i, s in enumerate(steps) if s["role"] == "work")
            if change == "fixed":
                steps[first] = step("work", 10, 7, 700)
            elif change == "late":
                steps.insert(first, step("endurance", 60, 2, 175))
            elif change == "rest":
                steps[first + 1]["seconds"] = 240
            elif change == "count":
                del steps[first:first + 2]
            else:
                steps[first]["seconds"] = 16
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_free_effort_cannot_bypass_other_workout_power_guards(self):
        for template, role in (("VO2-2", "work"), ("AE-5", "work"), ("AN-2", "warmup"), ("AN-3", "recovery")):
            item = workout() if template == "VO2-2" else self.flat_case(template)
            spec = item["coaching_prescription"]
            spec["steps"] = validator.flatten(spec["steps"])
            next(s for s in spec["steps"] if s["role"] == role)["target"] = {"basis": "max_effort", "zones": [7]}
            with self.subTest(template=template, role=role), self.assertRaises(ValueError):
                self.compile(item)

    def test_progressive_sprint_reference_is_comparable_and_targets_are_advisory(self):
        item = self.complex_case("AN-3")
        _, report = self.compile(item)
        self.assertEqual(report["work_seconds"], 150)
        self.assertEqual(report["recovery_seconds"], 2760)
        self.assertEqual(report["total_seconds"], 5430)
        self.assertEqual(report["sprint_reference"]["set_targets_watts"], [700, 721, 735])
        item["coaching_prescription"]["sprint_reference"]["set_targets_watts"] = [700] * 3
        self.compile(item)  # Explicit maintain-reference regression in the template.

    def test_progressive_sprint_rejects_incompatible_reference_or_unreviewed_target_progression(self):
        for change in ({"duration_seconds": 1}, {"source": ""}, {"date": "2026-10-23"},
                       {"set_targets_watts": [700, 735, 721]}, {"set_targets_watts": [700, 800, 900]},
                       {"set_targets_watts": [700, True, 735]}):
            item = self.complex_case("AN-3")
            item["coaching_prescription"]["sprint_reference"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)
        item = self.complex_case("AN-3")
        del item["coaching_prescription"]["sprint_reference"]
        with self.assertRaises(ValueError):
            self.compile(item)

    def test_progressive_sprint_checks_sets_reps_recovery_and_extended_cooldown(self):
        for change in ("rest", "double_rest", "count", "sets", "cooldown"):
            item = self.flat_case("AN-3")
            steps = item["coaching_prescription"]["steps"]
            if change == "rest":
                next(s for s in steps if s["role"] == "set_recovery")["seconds"] = 180
            elif change == "double_rest":
                i = next(i for i, s in enumerate(steps) if s["role"] == "set_recovery")
                steps.insert(i, step("recovery", 180))
            elif change == "count":
                i = next(i for i, s in enumerate(steps) if s["role"] == "work")
                del steps[i:i + 2]
            elif change == "sets":
                i = next(i for i, s in enumerate(steps) if s["role"] == "set_recovery")
                del steps[4:i + 1]
            else:
                steps[-1]["seconds"] = 900
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_mixed_surges_check_start_spacing_dose_and_z2_background(self):
        for change in ("zone", "spacing", "duration", "count", "background"):
            item = self.flat_case("MIX-1")
            steps = item["coaching_prescription"]["steps"]
            if change == "zone":
                next(s for s in steps if s["role"] == "recovery")["target"] = step("recovery", 1)["target"]
            elif change == "spacing":
                next(s for s in steps if s["role"] == "recovery")["seconds"] = 400
            elif change == "duration":
                next(s for s in steps if s["role"] == "work")["seconds"] = 181
            elif change == "count":
                del steps[-3:-1]
            else:
                steps[1] = step("endurance", 780, 3, 220)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_openers_require_both_effort_types_and_full_z2_recoveries(self):
        for change in ("short", "long", "zone", "order", "count"):
            item = self.flat_case("MIX-2")
            steps = item["coaching_prescription"]["steps"]
            if change in {"short", "long"}:
                steps[2]["seconds"] = 179 if change == "short" else 301
            elif change == "zone":
                steps[2] = step("recovery", 180)
            elif change == "order":
                steps[1], steps[7] = steps[7], steps[1]
            else:
                del steps[1:3]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.compile(item)

    def test_low_cadence_work_and_higher_cadence_recoveries_are_required(self):
        for template in ("SE-1", "SE-2"):
            for change in ("missing", "high", "rest_cadence", "rest_power", "rest_time"):
                item = self.flat_case(template)
                steps = item["coaching_prescription"]["steps"]
                if change == "missing":
                    del steps[1]["cadence_rpm"]
                elif change == "high":
                    steps[1]["cadence_rpm"] = 90
                elif change == "rest_cadence":
                    steps[2]["cadence_rpm"] = 55
                elif change == "rest_power":
                    steps[2]["target"] = step("recovery", 1, 2, 175)["target"]
                else:
                    steps[2]["seconds"] = 180
                with self.subTest(template=template, change=change), self.assertRaises(ValueError):
                    self.compile(item)

    def test_seated_climbing_cadence_variant_is_available(self):
        item = self.flat_case("SE-1")
        for s in item["coaching_prescription"]["steps"]:
            if s["role"] == "work":
                s["cadence_rpm"] = 75
        compiled, _ = self.compile(item)
        self.assertIn("75rpm", compiled["description"])

    def test_labels_cannot_smuggle_executable_power_duration_or_mode_overrides(self):
        for label in ("bonus 1000w", "freeride", "ramp", "press lap", "extra 1h"):
            item = workout()
            item["coaching_prescription"]["steps"][0]["label"] = label
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "reserved workout syntax"):
                self.compile(item)

    def test_invalid_complex_template_batch_is_rejected_before_network(self):
        valid = self.complex_case("AN-3")
        bad = self.flat_case("SE-2")
        del bad["coaching_prescription"]["steps"][1]["cadence_rpm"]
        with mock.patch.object(self.pusher, "_read_event_window") as read:
            result = self.pusher.push_workouts([valid, bad])
        self.assertEqual(result["outcome"], "not_applied")
        read.assert_not_called()

    def test_ftp_setting_history_does_not_invent_assessment_provenance(self):
        sync = object.__new__(sync_mod.IntervalsSync)
        history = {"outdoor": {"2026-09-01": 250}, "indoor": {}}
        with mock.patch.object(sync, "_load_ftp_history", return_value=history):
            rows = sync._build_ftp_timeline([], {})
        self.assertEqual(rows[0]["date"], "2026-09-01")
        self.assertEqual(rows[0]["date_kind"], "setting_recorded")
        self.assertEqual(rows[0]["ftp"], 250)
        for field in ("assessment_date", "assessment_method", "equipment"):
            self.assertIsNone(rows[0][field])

    def test_current_ftp_setting_observation_is_not_a_test_today(self):
        sync = object.__new__(sync_mod.IntervalsSync)
        athlete = {"sportSettings": [{"types": ["Ride"], "ftp": 260}]}
        with mock.patch.object(sync, "_load_ftp_history", return_value={}):
            rows = sync._build_ftp_timeline([], athlete)
        self.assertEqual(rows[0]["date"], "2026-10-22")
        self.assertEqual(rows[0]["date_kind"], "setting_observed")
        self.assertIsNone(rows[0]["assessment_date"])
