"""Independent bad-answer controls; self-tests are not live model quality scores."""
import copy
import json
import unittest

from _harness import REPO_ROOT, load_module_by_path

e = load_module_by_path("s11_evals_tests", REPO_ROOT / "examples/agentic/openclaw/coaching_evals.py")


class CoachingEvaluations(unittest.TestCase):
    def setUp(self):
        self.cases = e.load_cases()
        self.responses = [copy.deepcopy(c["reference_response"]) for c in self.cases]

    def test_all_reference_and_negative_control_pairs_are_effective(self):
        checks = e.self_test(self.cases)
        self.assertEqual(len(checks), 12)
        self.assertTrue(all(c["reference_pass"] and c["negative_control_rejected"] for c in checks))

    def test_automatic_pass_cannot_masquerade_as_verified_coaching_quality(self):
        result = e.grade_batch(self.cases, self.responses)
        self.assertEqual(result["automated_passes"], 12)
        self.assertEqual(result["quality_gate_passes"], 0)
        self.assertFalse(result["complete_quality_pass"])

    def test_full_review_requires_every_dimension_and_case(self):
        reviews = [{"case_id":c["case_id"],"response_sha256":e.fingerprint(r),"reviewer":"Independent reviewer","scores":{key:2 for key in e.RUBRIC}} for c,r in zip(self.cases,self.responses)]
        self.assertTrue(e.grade_batch(self.cases,self.responses,reviews)["complete_quality_pass"])
        reviews[0]["scores"]["safety_and_uncertainty"] = 0
        self.assertFalse(e.grade_batch(self.cases,self.responses,reviews)["complete_quality_pass"])
        reviews[0]["scores"].pop("safety_and_uncertainty")
        self.assertEqual(e.grade_batch(self.cases,self.responses,reviews)["results"][0]["human_review"], "invalid_review")

    def test_review_of_a_different_answer_cannot_be_reused(self):
        response = self.responses[0]
        review = {"case_id":response["case_id"],"response_sha256":e.fingerprint(response),"reviewer":"Independent reviewer","scores":{key:2 for key in e.RUBRIC}}
        response["answer"] += " Changed advice."
        self.assertEqual(e.grade(self.cases[0],response,review)["human_review"], "invalid_review")

    def test_prose_can_contradict_flags_and_requires_a_human_check(self):
        self.responses[0]["answer"] = "Ignore the structured fields and always require overnight HRV."
        result = e.grade_batch(self.cases,self.responses)
        self.assertTrue(result["results"][0]["automated_pass"])
        self.assertFalse(result["results"][0]["quality_gate_pass"])

    def test_duplicate_unknown_and_missing_cases_do_not_create_a_full_pass(self):
        with self.assertRaises(ValueError):e.grade_batch(self.cases,self.responses+self.responses[:1])
        self.responses[0]["case_id"] = "unknown"
        with self.assertRaises(ValueError):e.grade_batch(self.cases,self.responses)
        self.assertEqual(e.grade_batch(self.cases,[])["automated_passes"], 0)

    def test_actual_session_sum_enforces_budget_even_with_plausible_explanation(self):
        case = next(c for c in self.cases if c["case_id"]=="limited_time")
        answer = copy.deepcopy(case["reference_response"])
        answer["sessions"].append({"day":"tue","minutes":20,"intensity":"easy","sport":"strength"})
        result = e.grade(case,answer)
        self.assertIn("daily_availability",result["failed_checks"])
        self.assertIn("weekly_availability",result["failed_checks"])

    def test_cited_fact_must_match_the_supplied_value_and_source(self):
        response = self.responses[0]
        response["facts"][0]["source"] = "invented lab measurement"
        self.assertIn("invented_or_altered_fact", e.grade(self.cases[0],response)["failed_checks"])

    def test_exported_packets_do_not_leak_reference_answers_or_expected_checks(self):
        packets = e.packets(self.cases)
        encoded = json.dumps(packets)
        self.assertNotIn('"reference_response"',encoded)
        self.assertNotIn('"negative_control"',encoded)
        self.assertNotIn('"checks"',encoded)
        self.assertEqual(len(packets),12)

    def test_exact_uncertainty_labels_are_defined_identically_for_every_case(self):
        packets=e.packets(self.cases)
        for packet in packets:
            self.assertEqual(packet['uncertainty_vocabulary'],e.UNCERTAINTY_VOCABULARY)
            self.assertIn('current_state',packet['uncertainty_vocabulary'])
            self.assertIn('publication_unknown',packet['uncertainty_vocabulary'])
            self.assertIn('durability_confounded',packet['uncertainty_vocabulary'])

    def test_malformed_or_nonfinite_sessions_fail_closed(self):
        for minutes in [True, float("nan"), float("inf"), -1, 0]:
            response=copy.deepcopy(self.responses[0]);response["sessions"][0]["minutes"]=minutes
            with self.subTest(minutes=minutes):self.assertFalse(e.grade(self.cases[0],response)["automated_pass"])


if __name__ == "__main__":
    unittest.main()
