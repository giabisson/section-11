#!/usr/bin/env python3
"""Offline synthetic coaching evaluation packets and constrained response checks.

No model judge or model invocation. Mechanical checks cannot certify prose;
independent human review of each original answer is required for a quality pass.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

CASES = Path(__file__).with_name("evals") / "cases.json"
RUBRIC = ("evidence_fidelity", "safety_and_uncertainty", "individualization", "clarity_and_followup")
UNCERTAINTY_VOCABULARY = {
    'current_state':'Current readiness/health evidence is missing or stale.',
    'completion_unknown':'Session completion or execution has not been established.',
    'publication_unknown':'The outcome of a calendar write has not been confirmed.',
    'durability_confounded':'Durability observations have unresolved confounding factors.'
}
CONTRACT = {
    "case_id": "Copy the case ID",
    "answer": "Your full athlete-facing explanation, consistent with every structured field",
    "decision": {"action": "maintain|progress|reduce|rest|request_context|reschedule",
                 "requires_hrv": False, "requires_rhr": False, "ftp_change_pct": 0,
                 "catchup_sessions": 0, "completion": "verified|reported|unknown",
                 "calendar_state": "unchanged|confirmed|unknown",
                 "evidence_ids": ["IDs from input facts used to justify the decision"],
                 "uncertainty_ids": ["Unresolved issues"],
                 "next_observation": "What to observe and when before the next adjustment"},
    "sessions": [{"day": "mon|tue|wed|thu|fri|sat|sun", "minutes": 45,
                  "intensity": "easy|hard", "sport": "cycling|strength"}],
    "facts": [{"id": "An input fact ID", "value": "Copy its actual value", "source": "Copy its source"}]
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_cases(path=CASES):
    cases = json.loads(Path(path).read_text())
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_case")
    return cases


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def get(value, path):
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise ValueError("missing_field")
        value = value[key]
    return value


def check_rule(response, rule):
    try:
        value = get(response, rule["path"])
        expected = rule["value"]
        op = rule["op"]
        if op == "eq":
            return type(value) is type(expected) and value == expected
        if op == "in":
            return value in expected
        if op == "contains":
            return isinstance(value, list) and all(x in value for x in expected)
        if op == "lte":
            return finite(value) and value <= expected
        if op == "gte":
            return finite(value) and value >= expected
    except (ValueError, TypeError, KeyError):
        pass
    return False


def grade(case, response, review=None):
    failed = []
    try:
        if response.get("case_id") != case["case_id"] or not isinstance(response["answer"], str) or not response["answer"].strip():
            failed.append("answer_required")
        decision = response["decision"]
        if (set(decision) != set(CONTRACT["decision"]) or decision["action"] not in ("maintain", "progress", "reduce", "rest", "request_context", "reschedule")
                or type(decision["requires_hrv"]) is not bool or type(decision["requires_rhr"]) is not bool
                or not finite(decision["ftp_change_pct"]) or type(decision["catchup_sessions"]) is not int or decision["catchup_sessions"] < 0
                or decision["completion"] not in ("verified", "reported", "unknown")
                or decision["calendar_state"] not in ("unchanged", "confirmed", "unknown")
                or not isinstance(decision["uncertainty_ids"], list) or not all(isinstance(x, str) for x in decision["uncertainty_ids"])
                or not isinstance(decision["next_observation"], str) or not decision["next_observation"].strip()):
            failed.append("decision_contract")
        facts = {f["id"]: f for f in case["input"]["facts"]}
        supplied = response["facts"]
        if not isinstance(supplied, list) or any(not isinstance(f, dict) or f != facts.get(f.get("id")) for f in supplied):
            failed.append("invented_or_altered_fact")
        supplied_ids = [f["id"] for f in supplied]
        if len(set(supplied_ids)) != len(supplied_ids):
            failed.append("duplicate_fact")
        if (not isinstance(decision["evidence_ids"], list) or not decision["evidence_ids"]
                or not set(decision["evidence_ids"]) <= set(supplied_ids)):
            failed.append("decision_evidence_required")
        sessions = response["sessions"]
        total, hard = 0, 0
        if not isinstance(sessions, list) or len(sessions) > 14:
            raise ValueError("sessions_contract")
        for row in sessions:
            if (set(row) != {"day", "minutes", "intensity", "sport"} or row["day"] not in case["input"]["available_minutes_by_day"]
                    or not finite(row["minutes"]) or row["minutes"] <= 0 or row["intensity"] not in ("easy", "hard")
                    or row["sport"] not in ("cycling", "strength")):
                raise ValueError("sessions_contract")
            total += row["minutes"]
            hard += row["intensity"] == "hard"
        for day, minutes in case["input"]["available_minutes_by_day"].items():
            if sum(r["minutes"] for r in sessions if r["day"] == day) > minutes:
                failed.append("daily_availability")
        if total > case["input"]["weekly_budget_minutes"]:
            failed.append("weekly_availability")
        checked = {**response, "derived": {"minutes": total, "hard_sessions": hard}}
        for rule in case["checks"]:
            if not check_rule(checked, rule):
                failed.append(rule["id"])
    except (KeyError, TypeError, ValueError, AttributeError):
        failed.append("response_contract")
    human = "unreviewed"
    if review is not None:
        scores = review.get("scores", {}) if isinstance(review, dict) else {}
        if (isinstance(review, dict) and review.get("case_id") == case["case_id"]
                and review.get("response_sha256") == fingerprint(response)
                and isinstance(review.get("reviewer"), str) and review["reviewer"].strip()
                and set(scores) == set(RUBRIC) and all(type(v) is int and 0 <= v <= 2 for v in scores.values())):
            human = "pass" if all(v >= 1 for v in scores.values()) else "fail"
        else:
            human = "invalid_review"
    try:
        response_hash = fingerprint(response)
    except (ValueError, TypeError):
        response_hash = None
    return {"case_id": case["case_id"], "response_sha256": response_hash, "automated_pass": not failed,
            "failed_checks": sorted(set(failed)), "human_review": human,
            "quality_gate_pass": not failed and human == "pass"}


def grade_batch(cases, responses, reviews=()):
    known = {c["case_id"] for c in cases}
    for rows in (responses, reviews):
        ids = [r["case_id"] for r in rows]
        if len(ids) != len(set(ids)) or not set(ids) <= known:
            raise ValueError("duplicate_or_unknown_case")
    by_id = {r["case_id"]: r for r in responses}
    reviewed = {r["case_id"]: r for r in reviews}
    results = [grade(c, by_id.get(c["case_id"], {}), reviewed.get(c["case_id"])) for c in cases]
    return {"schema_version": 1, "case_count": len(cases), "cases_sha256": fingerprint(cases),
            "automated_passes": sum(r["automated_pass"] for r in results),
            "quality_gate_passes": sum(r["quality_gate_pass"] for r in results),
            "complete_quality_pass": bool(results) and all(r["quality_gate_pass"] for r in results),
            "scope": "synthetic_coaching_contract_plus_independent_human_review_not_clinical_validation",
            "results": results}


def packets(cases):
    return [{"case_id": c["case_id"], "input_sha256": fingerprint({"scenario":c["scenario"], "input":c["input"], "response_contract":CONTRACT,"uncertainty_vocabulary":UNCERTAINTY_VOCABULARY}), "prompt": "Act as an evidence-informed cycling coach. Use only the supplied facts. Return one JSON object following the response contract. Explain your actual recommendation in answer; structured fields must agree with it. Use the supplied standard uncertainty IDs where applicable; additional descriptive IDs are allowed. Do not call tools, publish training or send messages.",
             "scenario": c["scenario"], "input": c["input"], "response_contract": CONTRACT,"uncertainty_vocabulary":UNCERTAINTY_VOCABULARY} for c in cases]


def self_test(cases):
    return [{"case_id": c["case_id"], "reference_pass": grade(c, c["reference_response"])["automated_pass"],
             "negative_control_rejected": not grade(c, c["negative_control"])["automated_pass"]} for c in cases]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=CASES)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    export = sub.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    grading = sub.add_parser("grade")
    grading.add_argument("--responses", type=Path, required=True, help="JSON array of original structured answers")
    grading.add_argument("--reviews", type=Path, help="JSON array of independent human scores")
    args = parser.parse_args()
    try:
        cases = load_cases(args.cases)
        if args.command == "self-test":
            result = self_test(cases)
            print(json.dumps({"checks": result, "live_model_quality_measured": False}, indent=2))
            return 0 if result and all(r["reference_pass"] and r["negative_control_rejected"] for r in result) else 1
        if args.command == "export":
            # Exclusive creation avoids accidentally overwriting a saved benchmark.
            with args.output.open("x") as f:
                for packet in packets(cases):
                    f.write(json.dumps(packet) + "\n")
            print(json.dumps({"packets_exported": len(cases), "model_calls": 0}))
            return 0
        responses = json.loads(args.responses.read_text())
        reviews = json.loads(args.reviews.read_text()) if args.reviews else []
        result = grade_batch(cases, responses, reviews)
        print(json.dumps(result, indent=2))
        return 0 if result["complete_quality_pass"] else 1
    except Exception:
        print('{"ok":false,"error_code":"invalid_evaluation_input"}')
        return 2


if __name__ == "__main__":
    sys.exit(main())
