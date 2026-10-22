"""Cause-aware review guards; exact training choices remain explained judgment.

Input is a dated, explicitly sourced observation snapshot plus optional proposed
future revision. No network, publication, medical diagnosis or universal ramp.
"""
import copy
from datetime import datetime, timedelta


ACTIONS = {"maintain", "progress", "reduce", "substitute", "reschedule", "request_context"}
CAUSES = {"none", "work", "availability", "illness", "injury", "fatigue", "equipment", "preference", "unknown"}


def assess(store, source, api):
    """Validate evidence, retain uncertainty and bind adjustments to observations."""
    api.obj(source, {"schema_version", "review_id", "parent_revision", "trigger", "schedule_opt_in", "assessed_date",
                     "period", "snapshot", "observations", "current_feedback", "decisions", "candidate_plan"})
    if type(source["schema_version"]) is not int or source["schema_version"] != 1:
        raise ValueError("review schema_version must be 1")
    api.identifier(source["review_id"])
    if source["trigger"] not in ("athlete", "scheduled") or type(source["schedule_opt_in"]) is not bool:
        raise ValueError("review trigger must be athlete/scheduled with explicit schedule_opt_in")
    if source["trigger"] == "scheduled" and not source["schedule_opt_in"]:
        raise ValueError("scheduled reviews require explicit opt-in; no schedule was enabled")
    day = api.date(source["assessed_date"])
    if day.isoformat() != api.today():
        raise ValueError("assessed_date must be the local review day")
    period = source["period"]
    api.obj(period, {"start", "end"})
    if not api.date(period["start"]) <= api.date(period["end"]) <= day:
        raise ValueError("review period must be ordered and not in the future")
    snapshot = source["snapshot"]
    api.obj(snapshot, {"athlete_id", "source", "as_of", "coverage", "activities", "events", "readiness"})
    api.text(snapshot["source"])
    snapshot_day = api.date(snapshot["as_of"])
    if snapshot_day > day or snapshot["coverage"] not in ("complete", "partial", "unavailable"):
        raise ValueError("invalid observation date or coverage")
    if not all(isinstance(snapshot[k], list) and len(snapshot[k]) <= 2000 for k in ("activities", "events")):
        raise ValueError("activities/events must be bounded lists")
    readiness = snapshot["readiness"]
    api.obj(readiness, {"date", "recommendation", "priority", "health_clarification_required"})
    api.date(readiness["date"])
    if (readiness["recommendation"] not in ("go", "modify", "skip", "unknown")
            or type(readiness["priority"]) is not int or readiness["priority"] not in (0, 1, 2, 3)
            or type(readiness["health_clarification_required"]) is not bool):
        raise ValueError("invalid readiness envelope")
    if readiness["priority"] in (0, 1) and readiness["recommendation"] != "skip":
        raise ValueError("P0/P1 cannot be represented as permission to train")
    feedback = source["current_feedback"]
    current = None
    if feedback is not None:
        api.obj(feedback, {"date", "state", "source", "note", "health_clarification"})
        if api.date(feedback["date"]) > day or feedback["state"] not in ("rested", "normal", "fatigued", "weak", "symptoms", "unknown"):
            raise ValueError("invalid current feedback")
        api.text(feedback["source"])
        api.text(feedback["note"])
        health = feedback["health_clarification"]
        if health is not None:
            api.obj(health, {"compatible", "reason"})
            if type(health["compatible"]) is not bool:
                raise ValueError("health compatibility must be explicit")
            api.text(health["reason"])
        if feedback["date"] == day.isoformat():
            current = feedback
    current_data = snapshot_day == day and readiness["date"] == day.isoformat() and snapshot["coverage"] != "unavailable"
    needs_health = readiness["health_clarification_required"] or (current and current["state"] == "symptoms")
    health_answer = current and current["health_clarification"]
    unresolved_health = bool(needs_health and not health_answer)
    health_incompatible = bool(health_answer and not health_answer["compatible"])
    same_day_stop = (current_data and readiness["recommendation"] == "skip") or health_incompatible or bool(current and current["state"] == "weak")
    restrict_progress = (not current_data or readiness["recommendation"] in ("modify", "skip", "unknown")
                         or unresolved_health or health_incompatible or bool(current and current["state"] in ("fatigued", "weak", "symptoms")))
    body = store._read("revisions", source["parent_revision"])
    plan = body["plan"]
    if snapshot["athlete_id"] != plan["athlete_id"]:
        raise ValueError("review snapshot belongs to another athlete")
    sessions = {s["session_id"]: s["prescription_id"] for s in plan["sessions"]}
    if not isinstance(source["observations"], list) or len(source["observations"]) > 1000:
        raise ValueError("observations must be a bounded list")
    rows, questions, seen = [], [], set()
    if not current_data:
        questions.append("Refresh the current readiness/training snapshot before progression or new same-day training.")
    if unresolved_health:
        questions.append("Clarify the actual illness/injury context and compatibility before new same-day training.")
    adverse = False
    for observation in source["observations"]:
        api.obj(observation, {"session_id", "prescription_id", "activity_id", "status", "cause", "goal_attainment",
                              "response", "source", "date", "note"})
        sid = observation["session_id"]
        if sid in seen or sessions.get(sid) != observation["prescription_id"]:
            raise ValueError("observations must identify unique selected prescription snapshots")
        seen.add(sid)
        rx = store.prescription(observation["prescription_id"])
        if not period["start"] <= rx["workout"]["date"] <= period["end"]:
            raise ValueError("observed prescription is outside the review period")
        if observation["status"] not in ("completed", "modified", "missed", "unknown") or observation["cause"] not in CAUSES:
            raise ValueError("unknown completion status/cause")
        if observation["goal_attainment"] not in ("met", "partial", "not_met", "unknown") or observation["response"] not in ("tolerated", "unexpectedly_hard", "adverse", "unknown"):
            raise ValueError("invalid goal attainment/response assessment")
        api.text(observation["source"])
        api.text(observation["note"])
        if api.date(observation["date"]) > day:
            raise ValueError("observation feedback is in the future")
        aid = observation["activity_id"]
        pairing, problem, execution_date = "unresolved", None, None
        if aid is not None:
            activities = [a for a in snapshot["activities"] if isinstance(a, dict) and str(a.get("id")) == str(aid)]
            if len(activities) != 1:
                problem = "activity_missing_or_duplicated"
            else:
                activity = activities[0]
                eid = activity.get("paired_event_id")
                events = [e for e in snapshot["events"] if isinstance(e, dict) and eid is not None and str(e.get("id")) == str(eid)]
                if len(events) != 1 or events[0].get("paired_activity_id") is not None and str(events[0]["paired_activity_id"]) != str(aid):
                    problem = "event_pair_missing_or_conflicting"
                else:
                    try:
                        started = datetime.fromisoformat(activity["start_date"])
                        if started.tzinfo is None:
                            raise ValueError("activity start must include timezone")
                        activity_day = started.astimezone().date().isoformat()
                        if not period["start"] <= activity_day <= period["end"] or activity_day > snapshot["as_of"]:
                            raise ValueError("activity outside the observed period/snapshot")
                        history = [r for r in store.event_history(int(eid))["versions"]
                                   if datetime.fromisoformat(r["verified_at"]) <= started]
                        applicable = history[-1] if history else None
                        if not applicable or applicable["kind"] == "delete" or applicable["prescription_id"] != observation["prescription_id"]:
                            problem = "no_applicable_published_snapshot"
                        else:
                            pairing = "paired_activity"
                            execution_date = activity_day
                    except (ValueError, KeyError, TypeError, OverflowError):
                        problem = "execution_time_or_publication_history_unverified"
        elif observation["status"] in ("completed", "modified"):
            problem = "reported_completion_without_authoritative_pair"
        if observation["status"] == "missed" and aid is not None:
            problem, pairing = "missed_report_conflicts_with_activity", "unresolved"
        if problem:
            pairing = "unresolved"
        if observation["status"] in ("missed", "modified") and observation["cause"] == "unknown":
            questions.append(f"Clarify why {sid} changed before using it to adjust future training.")
        cost = observation["response"] in ("unexpectedly_hard", "adverse") or observation["cause"] in ("fatigue", "illness", "injury")
        adverse |= cost
        rows.append({**copy.deepcopy(observation), "completion_evidence": pairing if aid is not None else "athlete_report" if observation["status"] == "missed" else "unresolved",
                     "execution_date": execution_date if pairing == "paired_activity" else None,
                     "pairing_issue": problem, "adherence": "unknown_requires_formal_evaluator",
                     "assessment_basis": "caller_supplied_goal_response", "cost_review_required": cost})
    # Absence is unknown, including a complete calendar snapshot: no automatic debt.
    omitted = [sid for sid, pid in sessions.items() if period["start"] <= store.prescription(pid)["workout"]["date"] <= period["end"] and sid not in seen]
    if omitted:
        rows.extend({"session_id": sid, "prescription_id": sessions[sid], "status": "unknown", "completion_evidence": "unresolved",
                     "pairing_issue": "not_observed", "adherence": "unknown_requires_formal_evaluator"} for sid in omitted)
    if any(r.get("pairing_issue") or r["status"] == "unknown" for r in rows):
        restrict_progress = True
    if adverse:
        restrict_progress = True
    patterns = []
    prior_rows = [r for event in store._events() if event["kind"] == "reviewed"
                  for r in event["body"]["result"]["report"]["observations"]]
    by_template = {}
    for row in prior_rows + rows:
        if (row.get("response") not in ("unexpectedly_hard", "adverse") or row.get("activity_id") is None
                or row.get("completion_evidence") != "paired_activity"
                or not (day - timedelta(days=28)).isoformat() <= (row.get("execution_date") or "") <= day.isoformat()):
            continue
        template = store.prescription(row["prescription_id"])["validation"].get("session_template")
        if template:
            by_template.setdefault(template, set()).add((row["prescription_id"], str(row["activity_id"])))
    for template, occurrences in by_template.items():
        if len(occurrences) >= 2:
            patterns.append({"session_template": template, "distinct_occurrences": len(occurrences),
                             "basis": "operational_repeat_flag_not_diagnosis",
                             "next_review": "Review fitness reference, recovery, session placement and fueling before escalation."})
            if adverse:
                questions.append(f"Repeated difficulty in {template}: review reference power, recovery, placement and fueling.")
    if not isinstance(source["decisions"], list) or not source["decisions"]:
        raise ValueError("each review requires an explicit decision and next observation")
    decisions = copy.deepcopy(source["decisions"])
    referenced = set()
    for decision in decisions:
        api.obj(decision, {"action", "session_ids", "reason", "observation_ids", "next_observation"})
        if decision["action"] not in ACTIONS:
            raise ValueError("unknown review action")
        api.strings(decision["session_ids"])
        api.strings(decision["observation_ids"])
        if not set(decision["observation_ids"]) <= {r["session_id"] for r in rows}:
            raise ValueError("decision refers to an observation outside this review")
        api.text(decision["reason"])
        api.text(decision["next_observation"])
        if decision["action"] == "progress" and restrict_progress:
            raise ValueError("progression is not supported while current adverse/uncertain evidence needs review")
        if decision["action"] == "progress" and not any(r.get("completion_evidence") == "paired_activity" and r.get("response") == "tolerated" and r.get("goal_attainment") == "met" for r in rows):
            raise ValueError("progression needs applicable completed training and tolerability evidence")
        referenced.update(decision["session_ids"])
    candidate = source["candidate_plan"]
    if candidate is not None:
        if any(d["action"] == "request_context" for d in decisions):
            raise ValueError("resolve requested context before submitting a dependent revision")
        if candidate.get("revision", {}).get("parent_revision") != source["parent_revision"]:
            raise ValueError("candidate must revise the reviewed parent")
        selected = candidate.get("sessions")
        if not isinstance(selected, list):
            raise ValueError("candidate sessions must be explicit")
        candidate_ids = {s.get("session_id") for s in selected if isinstance(s, dict)}
        changed = {sid for sid in sessions if not any(s.get("session_id") == sid and s.get("prescription_id") == sessions[sid] for s in selected)} | (candidate_ids - sessions.keys())
        if not changed <= referenced:
            raise ValueError("every changed/removed/new future session needs an attributable decision")
        for sid in changed:
            if sid in sessions and store.prescription(sessions[sid])["workout"]["date"] < day.isoformat():
                raise ValueError("review revisions must preserve historical selections; add a new future occurrence instead")
        if changed and all(d["action"] == "maintain" for d in decisions):
            raise ValueError("maintain cannot hide a changed session dose")
        if restrict_progress and changed:
            # Do not claim a reduction while increasing training volume, work
            # dose or work targets. Purposeful substitutions remain possible.
            before_minutes = after_minutes = before_work = after_work = 0
            before_peak = after_peak = 0
            for s in plan["sessions"]:
                rx = store.prescription(s["prescription_id"])
                if rx["workout"]["date"] >= day.isoformat():
                    before_minutes += rx["workout"]["duration_minutes"]
                    before_work += _demanding_seconds(rx, api)
                    before_peak = max(before_peak, _work_peak(rx, api))
            for s in selected:
                rx = store.prescription(s["prescription_id"]) if "prescription_id" in s else _compile(s, store)
                if rx["workout"]["date"] >= day.isoformat():
                    after_minutes += rx["workout"]["duration_minutes"]
                    after_work += _demanding_seconds(rx, api)
                    after_peak = max(after_peak, _work_peak(rx, api))
            if after_minutes > before_minutes + 1e-9 or after_work > before_work or after_peak > before_peak:
                raise ValueError("adverse/uncertain evidence cannot be used to increase future dose under a reduction label")
    elif any(d["action"] not in ("maintain", "request_context") for d in decisions):
        raise ValueError("a training adjustment requires a concrete candidate_plan, not only a narrative")
    guard = {"date": day.isoformat(), "same_day_stop": bool(same_day_stop),
             "same_day_clarification": unresolved_health or not current_data,
             "readiness_modify": current_data and readiness["recommendation"] == "modify",
             "progression_review_required": bool(restrict_progress)}
    return {"assessed_date": day.isoformat(), "observations": rows, "decisions": decisions,
            "unresolved_questions": list(dict.fromkeys(questions)), "guard": guard,
            "response_patterns": patterns,
            "missed_session_debt": False, "wearables_required": False,
            "evidence_scope": "Pairing confirms a recorded activity, not formal adherence or medical clearance. Goal/response and reasons are sourced caller assessments."}


def _compile(session, store):
    prepared, reports, errors = store._local_pusher()._prepare_workouts([session["workout"]])
    if errors:
        raise ValueError("; ".join(errors))
    return {"workout": prepared[0], "validation": reports[0]}


def _work_peak(rx, api):
    spec = rx["workout"].get("coaching_prescription")
    if not spec:
        return 0
    validator = api.push_module()._load_workout_validator()
    high = 0
    for step in validator.flatten(spec["steps"]):
        if step["role"] == "work":
            target = validator.target_watts(step["target"], spec["fitness_reference"])
            if target is None:
                return float("inf")
            high = max(high, target[1])
    return high


def _demanding_seconds(rx, api):
    spec = rx["workout"].get("coaching_prescription")
    if not spec:
        return 0
    validator = api.push_module()._load_workout_validator()
    return sum(s["seconds"] for s in validator.flatten(spec["steps"])
               if s["role"] == "work" and any(z >= 3 for z in s["target"]["zones"]))
