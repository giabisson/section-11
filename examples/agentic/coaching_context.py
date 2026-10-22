"""Optional event, durability and strength context without universal doses."""


def assess(block, goals, sessions, prescriptions, api):
    result = {"policy_version": "event_specific_v1", "questions": [], "event": None, "durability": None, "strength": None}
    event = block.get("event_preparation")
    if event is not None:
        api.obj(event, {"goal_id", "expected_duration_minutes", "terrain", "decisive_demands", "recent_training_reference", "taper"})
        goal = next((g for g in goals if g["goal_id"] == event["goal_id"]), None)
        if goal is None or goal["date"] is None:
            raise ValueError("event preparation requires a dated goal")
        api.text(event["terrain"])
        api.strings(event["decisive_demands"], True)
        api.evidence(event["recent_training_reference"])
        duration = event["expected_duration_minutes"]
        if duration is None:
            result["questions"].append("Clarify expected event duration when it changes taper, pacing or fueling; priority is not duration.")
        else:
            api.number(duration, .001)
        taper = event["taper"]
        taper_result = None
        if taper is not None:
            api.obj(taper, {"start_date", "end_date", "reference_minutes", "planned_minutes", "rationale", "familiar_intensity"})
            if not api.date(taper["start_date"]) <= api.date(taper["end_date"]) < api.date(goal["date"]):
                raise ValueError("taper must be an explicit pre-event period")
            reference = api.number(taper["reference_minutes"], .001)
            planned = api.number(taper["planned_minutes"])
            if planned > reference:
                raise ValueError("a taper cannot manufacture overload above its stated completed-training reference")
            api.text(taper["rationale"])
            if type(taper["familiar_intensity"]) is not bool:
                raise ValueError("familiar_intensity must be explicit")
            actual = sum(prescriptions[s["prescription_id"]]["workout"]["duration_minutes"] for s in sessions
                         if taper["start_date"] <= prescriptions[s["prescription_id"]]["workout"]["date"] <= taper["end_date"])
            if abs(actual - planned) > 1e-8:
                raise ValueError("taper planned_minutes differs from the complete selected prescription durations")
            taper_result = {"reference_minutes": reference, "planned_minutes": planned,
                            "reduction_pct": round((1 - planned / reference) * 100, 1),
                            "basis": "caller_supplied_completed_training_reference_not_CTL", "rationale": taper["rationale"]}
        result["event"] = {"goal_id": goal["goal_id"], "expected_duration_minutes": duration, "taper": taper_result,
                           "mandatory_overload": False, "fixed_TSB_target": None,
                           "evidence": "Wang 2023: taper benefit; subgroup settings uncertain, not a universal optimum"}
    durability = block.get("durability_context")
    if durability is not None:
        api.obj(durability, {"fresh", "fatigued", "interpretation"})
        api.text(durability["interpretation"])
        usable = True
        for row in (durability["fresh"], durability["fatigued"]):
            if row is None:
                usable = False
                continue
            api.obj(row, {"source", "date", "assessment", "assessment_seconds", "power_watts", "prior_minutes", "prior_work",
                          "prior_intensity", "environment", "pacing", "fueling", "conditions"})
            api.text(row["source"])
            if api.date(row["date"]) > api.date(api.today()):
                raise ValueError("durability observation cannot be in the future")
            api.text(row["assessment"])
            api.number(row["assessment_seconds"], 1)
            api.number(row["power_watts"], .001)
            for field in ("prior_minutes",):
                if row[field] is None:
                    usable = False
                else:
                    api.number(row[field])
            work = row["prior_work"]
            if work is None:
                usable = False
            else:
                api.obj(work, {"value", "unit"})
                if work["unit"] != "kJ_mechanical":
                    raise ValueError("durability prior work must be mechanical kJ, never dietary kcal")
                api.number(work["value"])
            for field in ("prior_intensity", "environment", "pacing", "fueling", "conditions"):
                if row[field] in (None, "unknown"):
                    usable = False
                else:
                    api.text(row[field])
        fresh, tired = durability["fresh"], durability["fatigued"]
        comparable = usable and all(fresh[k] == tired[k] for k in ("assessment", "assessment_seconds", "environment", "pacing", "fueling", "conditions"))
        result["durability"] = {"status": "descriptive_comparison" if comparable else "unavailable_or_not_comparable",
                                "power_change_pct": round((tired["power_watts"] / fresh["power_watts"] - 1) * 100, 1) if comparable else None,
                                "scope": "Selected power-window context, not decoupling equivalence, causal fitness change or a universal fatigue-work threshold."}
    strength = block.get("strength_context")
    if strength is not None:
        api.obj(strength, {"goal", "experience", "equipment", "technique", "soreness", "arrangement", "displaced_sessions", "recovery_plan", "evidence_certainty"})
        for field in ("goal", "experience", "equipment", "technique", "soreness", "recovery_plan"):
            api.text(strength[field])
        api.strings(strength["displaced_sessions"])
        if strength["arrangement"] not in ("add", "replace") or strength["evidence_certainty"] != "low":
            raise ValueError("strength context must distinguish add/replace and retain low evidence certainty")
        if strength["arrangement"] == "replace" and not strength["displaced_sessions"]:
            raise ValueError("replacement strength must name displaced/reduced training")
        strength_minutes = sum(prescriptions[s["prescription_id"]]["workout"]["duration_minutes"] for s in sessions
                               if prescriptions[s["prescription_id"]]["workout"].get("type") == "WeightTraining")
        result["strength"] = {"minutes_in_total_budget": strength_minutes, "arrangement": strength["arrangement"],
                              "evidence_certainty": "low", "performance_guarantee": False,
                              "low_cadence_is_heavy_strength": False}
        if any(strength[f] == "unknown" for f in ("experience", "equipment", "technique")):
            result["questions"].append("Clarify lifting experience, equipment and technique before prescribing new heavy strength; cycling can continue independently.")
    return result
