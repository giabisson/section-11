"""Bounded, offline compilation of explicitly checked cycling prescriptions.

This checks dose/target contracts, not health clearance or research efficacy.
Only the adjacent reviewed catalog supplies template constraints. No caller can
replace those constraints or silently fall back to label-based certification.
"""
import copy
import hashlib
import json
import math
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def catalog_location(directory=None):
    """Support the source checkout and documented root-script installations."""
    here = directory or Path(__file__).resolve().parent
    choices = [here / "workout-library/workout_constraints.json",
               here / "section11/examples/workout-library/workout_constraints.json",
               here / "examples/workout-library/workout_constraints.json"]
    if here.name == "agentic" and here.parent.name == "examples":
        choices.insert(0, here.parent / "workout-library/workout_constraints.json")
    return next((p for p in choices if p.is_file() and p.with_name("WORKOUT_REFERENCE.md").is_file()), choices[0])


CATALOG_PATH = catalog_location()
MAX_STEPS = 2000
MAX_DEPTH = 4
ROLES = {"warmup", "work", "endurance", "recovery", "set_recovery", "cooldown"}
METRICS = {"ftp", "ramp_peak_power", "critical_power"}


def number(value, name, minimum=0, integer=False):
    try:
        finite = isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        finite = False
    if (isinstance(value, bool) or not finite or value < minimum
            or (integer and not isinstance(value, int))):
        raise ValueError(f"{name} must be a finite {'integer' if integer else 'number'} >= {minimum}")
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\n\r"):
        raise ValueError(f"{name} must be nonempty single-line text")
    return value.strip()


def date(value, name):
    text(value, name)
    try:
        result = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{name} must be YYYY-MM-DD") from None
    if result.isoformat() != value:
        raise ValueError(f"{name} must be YYYY-MM-DD")
    return result


def keys(value, allowed, name):
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError(f"{name} must be an object with only {sorted(allowed)}")


def catalog():
    try:
        raw = CATALOG_PATH.read_bytes()
        data = json.loads(raw)
        library = CATALOG_PATH.with_name("WORKOUT_REFERENCE.md").read_bytes()
        digest = hashlib.sha256(library).hexdigest()
    except (OSError, ValueError) as exc:
        raise ValueError(f"checked workout catalog/library unavailable: {exc}") from None
    version = re.search(rb"\*\*Version:\*\* ([^\s]+)", library)
    if (data.get("schema_version") != 1 or data.get("library_sha256") != digest
            or version is None or data.get("library_version") != version[1].decode()):
        raise ValueError("checked catalog does not match the installed workout library")
    data["constraints_sha256"] = hashlib.sha256(raw).hexdigest()
    return data


def flatten(nodes, depth=0, result=None):
    if result is None:
        result = []
    if depth > MAX_DEPTH or not isinstance(nodes, list) or not nodes:
        raise ValueError("steps must be a nonempty list within the nesting limit")
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("every step must be an object")
        if "repeat" in node:
            keys(node, {"repeat", "steps"}, "repeat block")
            count = number(node["repeat"], "repeat", 1, integer=True)
            if count > MAX_STEPS:
                raise ValueError("repeat exceeds expanded step limit")
            expanded = flatten(node.get("steps"), depth + 1)
            if len(result) + len(expanded) * count > MAX_STEPS:
                raise ValueError("expanded step limit exceeded")
            for _ in range(count):
                result.extend(copy.deepcopy(expanded))
        else:
            keys(node, {"role", "seconds", "target", "label", "cadence_rpm", "technique"}, "step")
            if node.get("role") not in ROLES:
                raise ValueError(f"step role must be one of {sorted(ROLES)}")
            number(node.get("seconds"), "step seconds", 1, integer=True)
            if "label" in node:
                text(node["label"], "step label")
                # Labels must not introduce another executable duration/target/flag.
                if re.search(r"\d|\b(?:ramp|freeride|maxeffort|press lap)\b", node["label"], re.I):
                    raise ValueError("step label contains reserved workout syntax")
            if "technique" in node and node["technique"] not in ("high_cadence", "single_leg"):
                raise ValueError("technique must be high_cadence/single_leg")
            if "cadence_rpm" in node:
                number(node["cadence_rpm"], "cadence_rpm", 1, integer=True)
            result.append(copy.deepcopy(node))
            if len(result) > MAX_STEPS:
                raise ValueError("expanded step limit exceeded")
    return result


def reference_info(ref, workout, today):
    keys(ref, {"metric", "value_watts", "date", "method", "equipment", "environment",
               "source", "status", "review_after", "review", "zone_bounds_watts"}, "fitness_reference")
    if not isinstance(ref.get("metric"), str) or ref["metric"] not in METRICS:
        raise ValueError(f"fitness_reference.metric must be one of {sorted(METRICS)}")
    number(ref.get("value_watts"), "reference watts", .001)
    text(ref.get("source"), "fitness reference source")
    warnings = []
    for field in ("method", "equipment"):
        if ref.get(field) in (None, "unknown"):
            warnings.append(f"fitness {field} unknown; not independently verified")
        else:
            text(ref[field], "fitness " + field)
    if ref.get("date") is None:
        warnings.append("fitness assessment date unknown; do not substitute a setting-change date")
    elif date(ref["date"], "fitness assessment date") > today:
        raise ValueError("fitness assessment date is in the future")
    environment = ref.get("environment") or "unknown"
    if not isinstance(environment, str) or environment not in {"indoor", "outdoor", "unknown"}:
        raise ValueError("fitness environment must be indoor/outdoor/unknown")
    if environment == "unknown":
        warnings.append("fitness measurement environment unknown")
    mismatch = (isinstance(workout.get("indoor"), bool) and environment != "unknown"
                and workout["indoor"] != (environment == "indoor"))
    status = ref.get("status")
    if not isinstance(status, str) or status not in {"current", "uncertain", "stale", "contradictory"}:
        raise ValueError("reference status must be current/uncertain/stale/contradictory")
    overdue = (ref.get("review_after") is not None
               and date(ref["review_after"], "reference review_after") < today)
    if status in {"stale", "contradictory"} or overdue or mismatch:
        review = ref.get("review")
        keys(review, {"date", "reason", "decision"}, "reference review")
        if (review.get("decision") != "use_provisionally"
                or date(review.get("date"), "reference review date") != today):
            raise ValueError("stale/contradictory/overdue or mismatched reference requires a current explicit review")
        warnings.append("provisional reference use: " + text(review.get("reason"), "review reason"))
    if status == "uncertain":
        warnings.append("fitness reference is explicitly uncertain")
    bounds = ref.get("zone_bounds_watts")
    if not isinstance(bounds, dict) or not bounds:
        raise ValueError("zone_bounds_watts from the configured athlete zones is required; never infer it")
    for zone, pair in bounds.items():
        if zone not in {str(i) for i in range(1, 8)} or not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("zone bounds require zone keys 1..7 and [low, high] watts")
        low, high = (number(v, "zone bound") for v in pair)
        if low >= high:
            raise ValueError("each zone low must be below high")
    return warnings


def target_watts(target, ref):
    if isinstance(target, dict) and target.get("basis") == "max_effort":
        keys(target, {"basis", "zones"}, "maximal effort target")
        if target.get("zones") != [7] or type(target["zones"][0]) is not int:
            raise ValueError("maximal effort must explicitly declare zone 7 intent")
        return None  # Effort instruction, never an invented FTP multiple or ERG setpoint.
    keys(target, {"basis", "low", "high", "zones", "ramp"}, "target")
    basis = target.get("basis")
    if not isinstance(basis, str) or basis not in METRICS | {"watts"}:
        raise ValueError("unsupported power target basis")
    if basis != "watts" and basis != ref["metric"]:
        raise ValueError("target denominator does not match fitness reference; peak power is not FTP")
    low = number(target.get("low"), "target low")
    high = number(target.get("high", low), "target high")
    if low > high:
        raise ValueError("target low must not exceed high")
    if "ramp" in target and target["ramp"] not in ("up", "down"):
        raise ValueError("ramp must be up/down")
    factor = 1 if basis == "watts" else ref["value_watts"] / 100
    low, high = low * factor, high * factor
    if not all(math.isfinite(v) for v in (low, high)):
        raise ValueError("resolved targets must be finite")
    zones = target.get("zones")
    if (not isinstance(zones, list) or not zones
            or any(type(z) is not int or str(z) not in ref["zone_bounds_watts"] for z in zones)
            or len(zones) != len(set(zones))):
        raise ValueError("target zones must name available configured zones")
    if sorted(zones) != list(range(min(zones), max(zones) + 1)):
        raise ValueError("target zones must be contiguous")
    lo = min(ref["zone_bounds_watts"][str(z)][0] for z in zones)
    hi = max(ref["zone_bounds_watts"][str(z)][1] for z in zones)
    if low < lo or high > hi:
        raise ValueError("resolved target is outside its declared configured zones")
    return low, high


def in_range(value, limits):
    return limits[0] <= value <= limits[1]


def round_power(value):
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def check_pattern(main, rule):
    groups = [[]]
    for step in main:
        if step["role"] == "set_recovery":
            if not groups[-1] or not in_range(step["seconds"], rule["set_recovery_seconds"]):
                return False
            if not set(step["target"]["zones"]) <= {1}:
                return False
            groups.append([])
        else:
            groups[-1].append(step)
    if not in_range(len(groups), rule.get("sets", [1, 1])):
        return False
    for group in groups:
        if not group or group[0]["role"] != "work":
            return False
        for i, step in enumerate(group):
            role = "work" if i % 2 == 0 else "recovery"
            if step["role"] != role:
                return False
            allowed = rule["work_zones"] if role == "work" else [1]
            if not set(step["target"]["zones"]) <= set(allowed):
                return False
            if not in_range(step["seconds"], rule["work_seconds"] if role == "work" else rule["recovery_seconds"]):
                return False
            if role == "work":
                if (step["target"]["basis"] == "max_effort") != (rule.get("work_basis") == "max_effort"):
                    return False
                if "work_cadence" in rule and not in_range(step.get("cadence_rpm", 0), rule["work_cadence"]):
                    return False
            elif "recovery_cadence_min" in rule and step.get("cadence_rpm", 0) < rule["recovery_cadence_min"]:
                return False
        work = [s["seconds"] for s in group if s["role"] == "work"]
        if not in_range(len(work), rule["repetitions"]):
            return False
        if "work_sequence" in rule and work != rule["work_sequence"]:
            return False
        if "recovery_sequence" in rule and [s["seconds"] for s in group if s["role"] == "recovery"] != rule["recovery_sequence"]:
            return False
        if rule.get("final_recovery") is False and group[-1]["role"] != "work":
            return False
    return True


def steady(step, roles, zones):
    return (step["role"] in roles and set(step["target"]["zones"]) <= set(zones)
            and step["target"]["basis"] != "max_effort" and "ramp" not in step["target"])


def groups_with_rest(main, seconds):
    groups = [[]]
    for step in main:
        if step["role"] == "set_recovery":
            if not groups[-1] or not steady(step, {"set_recovery"}, {1}) or step["seconds"] != seconds:
                return []
            groups.append([])
        else:
            groups[-1].append(step)
    return groups if all(groups) else []


def check_complex(main, rule, ref, total):
    """Explicit structures for continuous progressions and embedded work.

    Template prose ambiguities are resolved in the catalog/library, not guessed
    from labels or an LLM's description. Every second remains executable.
    """
    kind = rule["kind"]
    if "total_seconds" in rule and not in_range(total, rule["total_seconds"]):
        return False
    if kind == "fast_finish":
        # The easy lead-in includes the separately accounted ramp-in warm-up.
        lead = sum(s["seconds"] for s in main if s["role"] == "endurance")
        finish = [s for s in main if s["role"] == "work"]
        return (bool(finish) and all(steady(s, {"endurance"}, {1, 2}) for s in main[:-len(finish)])
                and all(steady(s, {"work"}, {3}) for s in main[-len(finish):])
                and in_range(sum(s["seconds"] for s in finish), rule["finish_seconds"])
                and in_range(lead + rule["actual_warmup"], rule["lead_seconds"]))
    if kind == "progressive":
        if not in_range(len(main), rule["blocks"]):
            return False
        previous = None
        for i, s in enumerate(main):
            allowed = {2, 3} if i == len(main) - 1 else {2}
            if not steady(s, {"work"}, allowed) or not in_range(s["seconds"], rule["block_seconds"]):
                return False
            low, high = (round_power(v) for v in target_watts(s["target"], ref))
            if previous is not None and low <= previous:
                return False
            previous = high
        return True
    if kind == "over_under":
        groups = groups_with_rest(main, rule["set_recovery_seconds"])
        if not in_range(len(groups), rule["sets"]):
            return False
        for group in groups:
            duration = sum(s["seconds"] for s in group)
            if not in_range(duration, rule["block_seconds"]):
                return False
            elapsed = 0
            for i, s in enumerate(group):
                zone, seconds = (4, 120) if i % 2 == 0 else (5, 60)
                if not steady(s, {"work"}, {zone}) or s["seconds"] != min(seconds, duration - elapsed):
                    return False
                elapsed += s["seconds"]
        return True
    if kind == "cadence_drills":
        # Optional Z2 lead/tail complete the easy ride; recovery cannot be hidden in them.
        first = next((i for i, s in enumerate(main) if s["role"] != "endurance"), len(main))
        last = len(main)
        while last > first and main[last - 1]["role"] == "endurance":
            last -= 1
        if not all(steady(s, {"endurance"}, {2}) for s in main[:first] + main[last:]):
            return False
        drills = main[first:last]
        if not check_pattern(drills, rule["pattern"]):
            return False
        for s in drills:
            if s["role"] == "work":
                if s.get("technique") == "single_leg":
                    continue
                if s.get("technique") != "high_cadence" or not in_range(s.get("cadence_rpm", 0), [100, 110]):
                    return False
        return True
    if kind == "embedded_sprints":
        last = len(main)
        while last and main[last - 1]["role"] == "endurance":
            last -= 1
        return (all(steady(s, {"endurance"}, {1, 2}) for s in main[last:])
                and check_pattern(main[:last], rule["pattern"]))
    if kind in {"mixed_surges", "openers"}:
        # Base segments and active recoveries are deliberately Z2, never Z1.
        efforts = []
        starts = []
        elapsed = 0
        for index, s in enumerate(main):
            if s["role"] == "work":
                if index and main[index - 1]["role"] == "work":
                    return False
                if not steady(s, {"work"}, rule["work_zones"]):
                    return False
                efforts.append(s)
                starts.append(elapsed)
            elif not steady(s, {"endurance", "recovery"}, {2}):
                return False
            elapsed += s["seconds"]
        if kind == "mixed_surges":
            return (in_range(len(efforts), rule["repetitions"])
                    and all(in_range(s["seconds"], rule["work_seconds"]) for s in efforts)
                    and all(in_range(b - a, rule["start_spacing_seconds"]) for a, b in zip(starts, starts[1:])))
        if [(s["seconds"], s["target"]["zones"]) for s in efforts] != [(60, [5])] * 3 + [(30, [6])] * 2:
            return False
        # Aggregate adjacent Z2 segments between efforts, regardless of their labels.
        return all(in_range(b - a - s["seconds"], rule["recovery_seconds"])
                   for a, b, s in zip(starts, starts[1:], efforts))
    return False


def sprint_reference_info(value, today):
    keys(value, {"value_watts", "duration_seconds", "date", "source", "set_targets_watts"}, "sprint_reference")
    watts = number(value.get("value_watts"), "sprint reference watts", .001)
    if type(value.get("duration_seconds")) is not int or value["duration_seconds"] != 10:
        raise ValueError("AN-3 reference must be comparable ten-second power, not FTP/instantaneous peak")
    if date(value.get("date"), "sprint reference date") > today:
        raise ValueError("sprint reference date is in the future")
    text(value.get("source"), "sprint reference source")
    targets = value.get("set_targets_watts")
    if not isinstance(targets, list) or len(targets) != 3:
        raise ValueError("AN-3 requires three advisory set targets")
    for target in targets:
        number(target, "advisory sprint watts", .001)
    if targets != [watts] * 3 and not (targets[0] == watts and targets[1] <= targets[2]
            and all(watts * 1.03 <= t <= watts * 1.05 for t in targets[1:])):
        raise ValueError("AN-3 targets must maintain the reference or increase sets two/three by 3–5 percent")
    return copy.deepcopy(value)


def compile_workout(workout):
    """Return a copied canonical workout and transparent validation report.

    Plain legacy descriptions remain possible but are explicitly not dose-checked.
    Native strings supplied with a checked prescription must match the compiler;
    they cannot replace its executable steps after validation.
    """
    if not isinstance(workout, dict):
        raise ValueError("workout must be an object")
    if "coaching_prescription" not in workout:
        return dict(workout), {"status": "not_checked", "reason": "no structured coaching_prescription"}
    spec = workout["coaching_prescription"]
    keys(spec, {"schema_version", "session_template", "template_version", "available_minutes",
                "fitness_reference", "sprint_reference", "steps"}, "coaching_prescription")
    if type(spec.get("schema_version")) is not int or spec["schema_version"] != 1:
        raise ValueError("coaching_prescription.schema_version must be 1")
    if workout.get("type", "Ride") not in {"Ride", "VirtualRide"}:
        raise ValueError("checked prescriptions currently support cycling power workouts only")
    if workout.get("target") not in (None, "POWER"):
        raise ValueError("checked power prescription cannot use an HR/PACE target")
    data = catalog()
    template = spec.get("session_template")
    if not isinstance(template, str) or template not in data["templates"]:
        raise ValueError("template has no checked constraint entry; obtain a reviewed addition rather than certify it")
    if spec.get("template_version") != data["library_version"]:
        raise ValueError("template_version does not match the installed checked library")
    ref = spec.get("fitness_reference")
    warnings = reference_info(ref, workout, datetime.now().date())
    steps = flatten(spec.get("steps"))
    total = sum(s["seconds"] for s in steps)
    if total > 43200:
        raise ValueError("checked workout exceeds the existing 12-hour limit")
    available = number(spec.get("available_minutes"), "available_minutes", .001)
    if total > available * 60:
        raise ValueError(f"full workout ({total} seconds) exceeds available time ({available} minutes)")
    for step in steps:
        target_watts(step.get("target"), ref)
    rule = data["templates"][template]
    maximal = [s for s in steps if s["target"]["basis"] == "max_effort"]
    if maximal:
        if rule["kind"] not in {"embedded_sprints", "sprint_sets"} or any(s["role"] != "work" for s in maximal):
            raise ValueError("maximal free effort is only checked for AN-2/AN-3 work steps")
        warnings.append("maximal sprints use freeride without an ERG power target; verify trainer/device mode before riding")
    if any("technique" in s and (rule["kind"] != "cadence_drills" or s["role"] != "work") for s in steps):
        raise ValueError("technique drills are only checked in AE-5 work steps")
    sprint_reference = None
    if rule["kind"] == "sprint_sets":
        sprint_reference = sprint_reference_info(spec.get("sprint_reference"), datetime.now().date())
        warnings.append("AN-3 sprint targets are advisory comparable-power goals, not ERG setpoints or a guarantee of increasing maximal power")
    elif "sprint_reference" in spec:
        raise ValueError("sprint_reference is only checked for AN-3")
    first = next((i for i, s in enumerate(steps) if s["role"] != "warmup"), len(steps))
    last = len(steps)
    while last > first and steps[last - 1]["role"] == "cooldown":
        last -= 1
    main = steps[first:last]
    if not main or any(s["role"] in {"warmup", "cooldown"} for s in main):
        raise ValueError("warm-up must precede the main set and cool-down must follow it")
    warmup = sum(s["seconds"] for s in steps[:first])
    cooldown = sum(s["seconds"] for s in steps[last:])
    if not in_range(warmup, rule["warmup_seconds"]) or not in_range(cooldown, rule["cooldown_seconds"]):
        raise ValueError("warm-up/cool-down duration is outside the checked template guard")
    primer = rule.get("warmup_primer")
    if primer:
        activations = [s for s in steps[:first]
                       if set(s["target"]["zones"]) <= set(primer["zones"])
                       and s["seconds"] >= primer["minimum_seconds"]]
        if len(activations) < primer["count"]:
            raise ValueError("warm-up lacks the checked intensity-specific primer")
    for step in steps[:first] + steps[last:]:
        allowed = rule["warmup_zones"] if step["role"] == "warmup" else rule.get("cooldown_zones", [1, 2])
        if not set(step["target"]["zones"]) <= set(allowed):
            raise ValueError("preparation/recovery target outside checked zones")
    if rule["kind"] == "continuous":
        if (not in_range(total, rule["total_seconds"])
                or any(s["role"] != "work" or not set(s["target"]["zones"]) <= set(rule["work_zones"]) for s in main)):
            raise ValueError("continuous workout violates checked duration/zone constraints")
    elif rule["kind"] in {"intervals", "sprint_sets"}:
        if not any(check_pattern(main, variant) for variant in rule["variants"]):
            raise ValueError("main-set structure, repetitions, recoveries, cadence or zones violate checked template constraints")
    elif not check_complex(main, dict(rule, actual_warmup=warmup), ref, total):
        raise ValueError("main-set structure, repetitions, recoveries, cadence or zones violate checked template constraints")
    if "duration_minutes" in workout:
        declared = number(workout["duration_minutes"], "duration_minutes", .001)
        if not math.isclose(declared * 60, total, abs_tol=.001, rel_tol=0):
            raise ValueError("declared duration_minutes differs from the complete executable steps")
    lines = []
    for step in steps:
        resolved = target_watts(step["target"], ref)
        if resolved is None:
            watts = "freeride"
        else:
            low, high = (round_power(v) for v in resolved)
            watts = f"{low}w" if low == high else f"{low}-{high}w"
            if step["target"].get("ramp"):
                if step["target"]["ramp"] == "down":
                    low, high = high, low
                watts = f"ramp {low}-{high}w"
        cadence = f" {step['cadence_rpm']}rpm" if "cadence_rpm" in step else ""
        cue = "Maximal sprint" if resolved is None else step.get("label", step["role"])
        technique = " " + step["technique"].replace("_", " ") if "technique" in step else ""
        lines.append(f"- {cue}{technique} {step['seconds']}s {watts}{cadence}")
    description = "\n".join(lines)
    if workout.get("description") not in (None, "", description):
        raise ValueError("description differs from compiled steps; preview the canonical description first")
    result = copy.deepcopy(workout)
    result.update(description=description, duration_minutes=total / 60, target="POWER")
    digest = hashlib.sha256(json.dumps(spec, sort_keys=True, allow_nan=False).encode()).hexdigest()
    report = {
        "status": "checked", "schema_version": 1, "session_template": template,
        "template_version": data["library_version"], "library_sha256": data["library_sha256"],
        "constraints_sha256": data["constraints_sha256"],
        "prescription_sha256": digest, "total_seconds": total,
        "available_minutes": available,
        "warmup_seconds": warmup, "cooldown_seconds": cooldown,
        "work_seconds": sum(s["seconds"] for s in main if s["role"] == "work"),
        "recovery_seconds": sum(s["seconds"] for s in main if s["role"] in {"recovery", "set_recovery"}),
        "endurance_seconds": sum(s["seconds"] for s in main if s["role"] == "endurance"),
        "expanded_steps": len(steps),
        "rendered_target_basis": "absolute_watts_and_free_effort" if maximal else "absolute_watts",
        "power_rounding": "nearest_watt_half_up",
        "fitness_reference": copy.deepcopy(ref), "warnings": warnings,
        "tss_basis": "caller_supplied_estimate" if "tss" in workout else "not_estimated",
        "evidence": rule.get("evidence", []),
        "scope": "Numeric dose and supplied session-budget/configured-zone guards; fitness provenance is caller-supplied. Week/day conflicts, suitability, exact technique and health require coaching review.",
    }
    if sprint_reference is not None:
        report["sprint_reference"] = sprint_reference
    return result, report


def main():
    """Compile a local JSON workout/list without credentials, HTTP or writes."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", help="workout object or list; source file is never changed")
    args = parser.parse_args()
    try:
        raw = json.loads(Path(args.json_file).read_text())
        values = raw if isinstance(raw, list) else [raw]
        if not values:
            raise ValueError("no workouts provided")
        compiled = [compile_workout(w) for w in values]
        result = {"success": True, "compiled_workouts": [x[0] for x in compiled],
                  "coaching_validation": [x[1] for x in compiled]}
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
