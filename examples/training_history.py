#!/usr/bin/env python3
"""Deterministic training facts and monthly history. No LLM or write API calls.

Private SQLite is the durable source; summary.json is an atomic projection.
Failed refreshes retain the last good projection. Only dated source facts are
stored: neither plan intent nor adherence is inferred from activity patterns.
"""
import argparse
import base64
import calendar
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import urllib.request
from zoneinfo import ZoneInfo

CYCLING = {"Ride", "VirtualRide", "MountainBikeRide", "GravelRide", "TrackRide", "EBikeRide", "EMountainBikeRide", "Handcycle", "Velomobile"}
MAX_RESPONSE = 32_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_forbidden")


def dumps(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


def day(value):
    if not isinstance(value, str):
        raise ValueError("missing_date")
    return date.fromisoformat(value[:10]).isoformat()


def facts(activities, wellness):
    """Validate identities before reconciliation; unknown metrics remain null."""
    if not isinstance(activities, list) or not isinstance(wellness, list):
        raise ValueError("invalid_response_shape")
    rides, days = {}, {}
    for a in activities:
        identity = str(a.get("id", ""))
        if not identity or len(identity) > 128:
            raise ValueError("invalid_activity_identity")
        stamp = a.get("start_date_local")
        activity_day = day(stamp)
        kind = a.get("type")
        if not isinstance(kind, str) or len(kind) > 80:
            raise ValueError("invalid_activity_type")
        zones = {}
        power = a.get("icu_zone_times")
        if isinstance(power, list):
            zones["power"] = {str(z["id"]): number(z.get("secs")) for z in power if isinstance(z, dict) and re.fullmatch(r"Z(?:[1-9]|1[0-6])", str(z.get("id", "")))}
        hr = a.get("icu_hr_zone_times")
        if isinstance(hr, list) and len(hr) <= 16:
            zones["hr"] = {"Z"+str(i+1): number(v) for i, v in enumerate(hr)}
        row = {"id": identity, "date": activity_day, "type": kind,
               "sport": "cycling" if kind in CYCLING else "other",
               "indoor": True if kind == "VirtualRide" else a.get("trainer") if isinstance(a.get("trainer"), bool) else None,
               "seconds": number(a.get("moving_time")), "load": number(a.get("icu_training_load")),
               "load_basis": a.get("icu_training_load_data") if a.get("icu_training_load_data") in ("POWER", "HR", "RPE") else "unspecified",
               "zones_seconds": zones, "ftp_setting_watts": number(a.get("icu_ftp")),
               "feel": number(a.get("feel")), "rpe": number(a.get("icu_rpe", a.get("rpe")))}
        if identity in rides and rides[identity] != row:
            raise ValueError("conflicting_duplicate_activity")
        rides[identity] = row
    for w in wellness:
        key = day(w.get("id"))
        row = {"date": key, "hrv": number(w.get("hrv")), "rhr": number(w.get("restingHR")), "ctl": number(w.get("ctl"))}
        for measurement in ("hrv", "rhr"):
            if row[measurement] == 0:
                row[measurement] = None  # Zero is not a physiological observation.
        if key in days and days[key] != row:
            raise ValueError("conflicting_duplicate_wellness")
        days[key] = row
    return sorted(rides.values(), key=lambda r: (r["date"], r["id"])), sorted(days.values(), key=lambda r: r["date"])


def metric(rows, key, scale=1):
    values = [r[key] for r in rows if r.get(key) is not None]
    return {"value": round(sum(values)/scale, 3) if len(values) == len(rows) else None,
            "known_sum": round(sum(values)/scale, 3), "observed": len(values), "missing": len(rows)-len(values)}


def aggregate(rows):
    zone_totals = {}
    for basis in ("power", "hr"):
        observed = [r["zones_seconds"][basis] for r in rows if r["zones_seconds"].get(basis)]
        keys = sorted({key for z in observed for key in z}, key=lambda key: int(key[1:]))
        zone_totals[basis] = {"activity_count": len(observed), "seconds": {key: sum(z.get(key) or 0 for z in observed) for key in keys},
                              "missing_zone_values": sum(v is None for z in observed for v in z.values())}
    ftp = [r for r in rows if r.get("ftp_setting_watts") is not None]
    return {"activities": len(rows), "hours": metric(rows, "seconds", 3600), "load": metric(rows, "load"),
            "longest_hours": round(max((r["seconds"] for r in rows if r["seconds"] is not None), default=0)/3600, 3) if rows and all(r["seconds"] is not None for r in rows) else None,
            "indoor": sum(r["indoor"] is True for r in rows), "outdoor": sum(r["indoor"] is False for r in rows), "environment_unknown": sum(r["indoor"] is None for r in rows),
            "feedback": {key: sum(r.get(key) is not None for r in rows) for key in ("feel", "rpe")},
            "zones": zone_totals,
            "ftp_reference": {"latest_watts": ftp[-1]["ftp_setting_watts"], "date": ftp[-1]["date"], "kind": "activity_setting_not_verified_test", "comparable_test": False} if ftp else None}


def summarize(activities, wellness, start, end, generated_at, attestation=None, attestation_matches_source=True):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start > end:
        raise ValueError("invalid_coverage_range")
    attestation = attestation or None
    if attestation:
        if set(attestation) != {"source", "confirmed_at", "first_training_date", "complete_through"} or attestation["source"] != "athlete_statement":
            raise ValueError("invalid_attestation")
        first = date.fromisoformat(attestation["first_training_date"])
        confirmed = date.fromisoformat(attestation["complete_through"])
        datetime.fromisoformat(attestation["confirmed_at"])
        if first > confirmed or confirmed > end or any(date.fromisoformat(r["date"]) < first for r in activities):
            raise ValueError("attestation_source_conflict")
    first_seen = min((r["date"] for r in activities), default=None)
    # No padded pre-training zero months. Empty months BETWEEN observed months
    # and the current snapshot remain visible, with absence labelled explicitly.
    first_month = date.fromisoformat(first_seen).replace(day=1) if first_seen else end.replace(day=1)
    cursor = max(start.replace(day=1), first_month)
    months = []
    while cursor <= end:
        month_end = cursor.replace(day=calendar.monthrange(cursor.year, cursor.month)[1])
        left, right = max(start, cursor), min(end, month_end)
        rows = [r for r in activities if left.isoformat() <= r["date"] <= right.isoformat()]
        measurements = [w for w in wellness if left.isoformat() <= w["date"] <= right.isoformat()]
        confirmed_whole = bool(attestation and attestation_matches_source and right <= date.fromisoformat(attestation["complete_through"]) and left >= date.fromisoformat(attestation["first_training_date"]))
        coverage = {"start": left.isoformat(), "end": right.isoformat(), "calendar_closed": month_end < end,
                    "partial": left > cursor or month_end >= end or bool(first_seen and cursor.isoformat() < first_seen <= month_end.isoformat()),
                    "logging": "athlete_confirmed_all_training" if confirmed_whole else "api_records_only",
                    "empty_meaning": "confirmed_no_training" if not rows and confirmed_whole else "no_recorded_activity" if not rows else None}
        optional = {}
        for key in ("hrv", "rhr", "ctl"):
            values = [w[key] for w in measurements if w.get(key) is not None]
            optional[key] = {"observations": len(values), "mean": round(sum(values)/len(values), 2) if values else None}
        months.append({"month": cursor.strftime("%Y-%m"), "coverage": coverage,
                       "all_sports": aggregate(rows), "cycling": aggregate([r for r in rows if r["sport"] == "cycling"]),
                       "sport_counts": {s: sum(r["type"] == s for r in rows) for s in sorted({r["type"] for r in rows})}, "optional_measurements": optional})
        cursor = (month_end+timedelta(days=1))
    return {"schema_version": 1, "generated_at": generated_at, "source": "Intervals.icu API deterministic facts",
            "coverage": {"queried_start": start.isoformat(), "queried_end": end.isoformat(), "first_activity": first_seen,
                         "last_activity": max((r["date"] for r in activities), default=None), "activity_count": len(activities), "athlete_attestation": attestation,
                         "attestation_source_status": "matches_confirmed_activity_identities" if attestation and attestation_matches_source else "source_changed_reconfirm_completeness" if attestation else "no_attestation"},
            "monthly": months,
            "policy": "Missing measurements are unknown; known_sum is not a complete total when missing>0. Power and HR zones remain separate source zones, not a 3-zone physiological model. Settings are not fitness tests. Partial months are not comparable full months. HRV/RHR are optional; athlete feedback remains valid. No inferred adherence, block intent or causality."}


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".history-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(dumps(value)+"\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fetch(config, endpoint, start, end):
    athlete = str(config["athlete_id"])
    if not re.fullmatch(r"i?[0-9]+", athlete) or athlete in ("0", "i0"):
        raise ValueError("invalid_account")
    token = base64.b64encode(("API_KEY:"+config["intervals_key"]).encode()).decode()
    url = f"https://intervals.icu/api/v1/athlete/{athlete}/{endpoint}?oldest={start}&newest={end}"
    request = urllib.request.Request(url, headers={"Authorization": "Basic "+token, "User-Agent": "Section11/1.0"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=35) as response:
        # Redirects to another host must not receive Basic credentials.
        if response.geturl() != url:
            raise ValueError("unexpected_redirect")
        raw = response.read(MAX_RESPONSE+1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("response_size_limit")
    return json.loads(raw)


def refresh(profile, now=None, fetcher=fetch):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("aware_clock_required")
    root = Path(profile["state_dir"])
    if not root.is_absolute() or root.is_symlink():
        raise ValueError("private_absolute_state_required")
    root.mkdir(parents=True, exist_ok=True, mode=0o700); root.chmod(0o700)
    if any((root/name).is_symlink() for name in ("facts.sqlite3", "summary.json", "status.json", "refresh.lock")):
        raise ValueError("ordinary_private_state_files_required")
    today = now.astimezone(ZoneInfo(profile["timezone"])).date()
    stamp = now.isoformat()
    with (root/"refresh.lock").open("a") as lock:
        lock_path = root/"refresh.lock"; lock_path.chmod(0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"success": True, "status": "already_running"}
        db_path = root/"facts.sqlite3"
        db = sqlite3.connect(db_path); db_path.chmod(0o600)
        try:
            db.execute("CREATE TABLE IF NOT EXISTS facts (kind TEXT, id TEXT, date TEXT, body TEXT, PRIMARY KEY(kind,id))")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
            meta = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM metadata")}
            config = json.loads(Path(profile["credentials_file"]).read_text())
            account = hashlib.sha256(str(config["athlete_id"]).encode()).hexdigest()
            if meta.get("account") not in (None, account):
                raise ValueError("account_mismatch")
            last_full = datetime.fromisoformat(meta["last_full"]) if meta.get("last_full") else None
            attestation = profile.get("athlete_attestation")
            old_attestation = meta.get("attestation_binding", {})
            full = last_full is None or (now-last_full).total_seconds() >= 86400 or now < last_full or old_attestation.get("statement") != attestation
            start = meta.get("coverage_start", (today-timedelta(days=365*3)).isoformat()) if full else (today-timedelta(days=13)).isoformat()
            end = today.isoformat()
            raw_a = fetcher(config, "activities", start, end)
            raw_w = fetcher(config, "wellness", start, end)
            activities, wellness = facts(raw_a, raw_w)
            if any(not start <= r["date"] <= end for r in activities+wellness):
                raise ValueError("response_outside_requested_dates")
            # All validation/network completes before any replacement/deletion.
            with db:
                for kind, records, identity in (("activity", activities, "id"), ("wellness", wellness, "date")):
                    db.execute("DELETE FROM facts WHERE kind=? AND date>=? AND date<=?", (kind, start, end))
                    for r in records:
                        db.execute("INSERT OR REPLACE INTO facts VALUES(?,?,?,?)", (kind, r[identity], r["date"], dumps(r)))
                all_a = [json.loads(r[0]) for r in db.execute("SELECT body FROM facts WHERE kind=? ORDER BY date,id", ("activity",))]
                all_w = [json.loads(r[0]) for r in db.execute("SELECT body FROM facts WHERE kind=? ORDER BY date,id", ("wellness",))]
                binding = {}
                if attestation:
                    identities = [(r["id"], r["date"]) for r in all_a if r["date"] <= attestation["complete_through"]]
                    identity_digest = hashlib.sha256(dumps(identities).encode()).hexdigest()
                    binding = old_attestation if old_attestation.get("statement") == attestation else {"statement": attestation, "activity_identity_digest": identity_digest}
                matches = not binding or binding["activity_identity_digest"] == identity_digest
                snapshot = summarize(all_a, all_w, meta.get("coverage_start", start), end, stamp, attestation, matches)
                snapshot["reconciliation"] = {"mode": "full" if full else "recent_14_days", "last_full": stamp if full else meta["last_full"], "recent_start": start,
                                               "source_activity_rows": len(raw_a), "unique_activity_rows": len(activities), "old_edits_checked_daily": True}
                generation = hashlib.sha256(dumps(snapshot).encode()).hexdigest()
                snapshot["generation"] = generation
                updates = {"account": account, "coverage_start": meta.get("coverage_start", start), "last_full": stamp if full else meta["last_full"], "generation": generation, "snapshot": snapshot, "attestation_binding": binding}
                for key, value in updates.items():
                    db.execute("INSERT OR REPLACE INTO metadata VALUES(?,?)", (key, dumps(value)))
            atomic_json(root/"summary.json", snapshot)
            atomic_json(root/"status.json", {"success": True, "attempted_at": stamp, "generation": generation})
            return {"success": True, "mode": snapshot["reconciliation"]["mode"], "activities": len(all_a), "months": len(snapshot["monthly"]), "calendar_writes": 0, "messages_sent": 0, "llm_calls": 0}
        except Exception:
            atomic_json(root/"status.json", {"success": False, "attempted_at": stamp, "error": "refresh_failed_last_good_summary_retained", "retry": "next_hourly_run"})
            raise
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = refresh(json.loads(args.profile.read_text()))
        print(dumps(result)); return 0
    except Exception:
        print('{"success":false,"error":"history_refresh_failed_private_status_available"}'); return 1


if __name__ == "__main__":
    sys.exit(main())
