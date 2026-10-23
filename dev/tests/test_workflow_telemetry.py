"""SQLite projection, cost/coverage semantics and privacy, using synthetic data."""
import contextlib
import ctypes
import ctypes.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from _harness import REPO_ROOT, load_module_by_path

t = load_module_by_path("s11_telemetry_tests", REPO_ROOT / "examples/agentic/openclaw/workflow_telemetry.py")
NOW = 1792670400000
START = NOW - 60000


class Telemetry(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state/openclaw.sqlite"
        self.agent = self.root / "agents/main/agent/openclaw-agent.sqlite"
        self.state.parent.mkdir(parents=True)
        self.agent.parent.mkdir(parents=True)
        with sqlite3.connect(self.state) as db:
            db.execute("CREATE TABLE cron_jobs (job_id TEXT,name TEXT,state_json TEXT)")
            db.execute("CREATE TABLE cron_run_receipts (receipt_id TEXT,job_id TEXT,status TEXT,started_at_ms INTEGER,finished_at_ms INTEGER,delivery_attempt_state TEXT)")
            db.execute("INSERT INTO cron_jobs VALUES (?,?,?)", ("job-private-id", "morning-readiness", json.dumps({"lastRunAtMs": START, "lastDeliveryStatus": "delivered"})))
            db.execute("INSERT INTO cron_run_receipts VALUES (?,?,?,?,?,?)", ("receipt-private-id", "job-private-id", "ok", START, START+10000, "unknown"))
        with sqlite3.connect(self.agent) as db:
            db.execute("CREATE TABLE session_windows (session_id TEXT,session_key TEXT,channel TEXT)")
            db.execute("CREATE TABLE transcript_events (session_id TEXT,seq INTEGER,event_json TEXT,event_zstd BLOB,created_at INTEGER)")
            db.execute("CREATE TABLE session_transcript_active_events (session_id TEXT,event_seq INTEGER)")
            db.execute("INSERT INTO session_windows VALUES (?,?,?)", ("session-private-id", "agent:main:cron:job-private-id", None))
        self.seq = 0
        self.event("user", content=[{"type":"text", "text":"private athlete symptoms and SECRET123"}], stamp=START+100)

    def event(self, role, stamp=None, active=True, **fields):
        self.seq += 1
        stamp = START + self.seq*1000 if stamp is None else stamp
        event = {"type":"message", "timestamp": stamp, "message":{"role":role, **fields}}
        with sqlite3.connect(self.agent) as db:
            db.execute("INSERT INTO transcript_events VALUES (?,?,?,?,?)", ("session-private-id", self.seq, json.dumps(event), None, stamp))
            if active:
                db.execute("INSERT INTO session_transcript_active_events VALUES (?,?)", ("session-private-id", self.seq))

    def model(self, **fields):
        msg = {"provider":"openai", "model":"synthetic-model", "api":"openai-responses", "stopReason":"stop",
               "usage":{"input":100, "output":20, "cacheRead":50, "cacheWrite":0, "totalTokens":170,"cost":{"total":0}},
               "content":[{"type":"text","text":"Private answer SECRET123"}]}
        msg.update(fields)
        self.event("assistant", **msg)

    def collect(self):
        return t.collect(self.root, now_ms=NOW)

    def test_usage_cost_delivery_and_no_sensitive_content(self):
        self.model()
        result = self.collect()
        run = result["runs"][0]
        self.assertEqual(run["tokens"]["input"], 100)
        self.assertEqual(run["tokens"]["cacheRead"], 50)
        self.assertEqual(run["usage_complete_responses"], 1)
        self.assertIsNone(run["reported_cost_total"])
        self.assertEqual(run["delivery_status"], "delivered")
        self.assertEqual(run["generation_status"], "ok")
        self.assertEqual(run["quality_assessment"], "not_graded")
        encoded = json.dumps(result)
        for private in ("SECRET123", "private athlete", "session-private-id", "job-private-id", "receipt-private-id"):
            self.assertNotIn(private, encoded)

    def test_zero_usage_error_attempt_is_counted_and_mirror_is_excluded(self):
        self.model(usage={}, stopReason="error", content=[])
        self.model(provider="openclaw")
        self.model(openclawDeliveryMirror=True)
        r = self.collect()["runs"][0]
        self.assertEqual(r["model_responses"], 1)
        self.assertEqual(r["model_errors"], 1)
        self.assertEqual(r["usage_complete_responses"], 0)
        self.assertFalse(r["final_text_present"])

    def test_cost_only_available_when_every_observed_response_has_positive_cost(self):
        self.model(usage={"cost":{"total":0.04}})
        r = self.collect()["runs"][0]
        self.assertAlmostEqual(r["reported_cost_total"], 0.04)
        self.model()
        r = self.collect()["runs"][0]
        self.assertIsNone(r["reported_cost_total"])
        self.assertAlmostEqual(r["reported_positive_cost_sum"], 0.04)

    def test_unknown_historical_delivery_is_not_inferred_from_generation(self):
        with sqlite3.connect(self.state) as db:
            db.execute("UPDATE cron_jobs SET state_json=?", (json.dumps({"lastRunAtMs":START+99999,"lastDeliveryStatus":"delivered"}),))
        self.model()
        r = self.collect()["runs"][0]
        self.assertEqual(r["generation_status"], "ok")
        self.assertEqual(r["delivery_status"], "unknown")

    def test_ambiguous_receipts_do_not_attribute_delivery(self):
        with sqlite3.connect(self.state) as db:
            db.execute("INSERT INTO cron_run_receipts VALUES (?,?,?,?,?,?)", ("another", "job-private-id", "error", START+1, START+10000, "unknown"))
        self.model()
        self.assertEqual(self.collect()["runs"][0]["receipt_link"], "unmatched")

    def test_tool_invocation_is_only_a_signal_and_errors_are_not_hidden(self):
        self.model(stopReason="toolUse", content=[{"type":"toolCall","name":"exec","arguments":{"command":"python3 /secret/push.py push --file private.json --confirm"}}])
        self.event("toolResult", isError=False, details={"exitCode":1,"persistedDetailsTruncated":True}, content=[{"type":"text","text":"private result"}])
        r = self.collect()["runs"][0]
        self.assertEqual(r["operation_signals"], {"calendar_write_attempt":1})
        self.assertEqual(r["tool_errors"], 1)
        self.assertEqual(r["truncation_signals"], 0)
        self.assertEqual(r["persisted_details_truncations"], 1)
        self.assertFalse(r["wall_complete"])
        self.assertNotIn("/secret/", json.dumps(r))

    def test_later_delivery_mirrors_do_not_inflate_telegram_response_latency(self):
        self.model()
        self.model(provider="openclaw", stamp=NOW-1000)
        r=self.collect()["runs"][0]
        self.assertEqual(r["observed_wall_ms"], 1900)

    def test_tool_text_truncation_is_separate_from_storage_details_truncation(self):
        self.model()
        self.event("toolResult", content=[{"type":"text","text":"[Showing lines 1 to 2000; output truncated]"}])
        r=self.collect()["runs"][0]
        self.assertEqual(r["truncation_signals"],1)
        self.assertEqual(r["persisted_details_truncations"],0)

    def test_structured_tool_truncation_counts_even_without_a_text_marker(self):
        self.model()
        self.event("toolResult",details={"truncation":{"truncated":True,"outputLines":2000}},content=[{"type":"text","text":"unmarked partial source"}])
        self.event("toolResult",details={"truncation":{"truncated":False}},content=[])
        result=self.collect();r=result["runs"][0]
        self.assertEqual(r["truncation_signals"],1)
        self.assertEqual(r["persisted_details_truncations"],0)
        self.assertEqual(result["truncation_policy_version"],2)

    def test_post_workout_marker_is_classified_without_persisting_prompt(self):
        with sqlite3.connect(self.agent) as db:
            db.execute("UPDATE session_windows SET session_key='agent:main:main'")
            db.execute("DELETE FROM transcript_events");db.execute("DELETE FROM session_transcript_active_events")
        self.event("user",content=[{"type":"text","text":"SECRET123 report according to POST_WORKOUT_REPORT_TEMPLATE.md"}])
        self.model()
        r=self.collect()["runs"][0]
        self.assertEqual(r["workflow"],"post_workout_review")
        self.assertEqual(r["workflow_basis"],"explicit_request_marker")
        self.assertNotIn("SECRET123",json.dumps(r))

    def test_plan_tool_workflow_remains_an_attempt_not_a_creation_claim(self):
        with sqlite3.connect(self.agent) as db:
            db.execute("UPDATE session_windows SET session_key='agent:main:telegram:private',channel='telegram'")
        self.model(content=[{"type":"toolCall","name":"exec","arguments":{"command":"python3 coaching_plan.py --data-dir '/private data' propose --json draft.json"}}])
        r=self.collect()["runs"][0]
        self.assertEqual(r["workflow"],"training_plan_attempt")
        self.assertEqual(r["origin"],"telegram")
        self.assertFalse(r["final_text_present"])

    def test_calendar_preview_is_not_counted_as_a_confirmed_write_attempt(self):
        self.model(content=[{"type":"toolCall","name":"exec","arguments":{"command":"python3 push.py push --json draft.json"}}])
        r=self.collect()["runs"][0]
        self.assertEqual(r["operation_signals"],{"calendar_preview_command":1})

    def test_compacted_inactive_event_is_not_double_counted(self):
        self.model(active=False)
        self.model()
        self.assertEqual(self.collect()["runs"][0]["model_responses"], 1)

    def test_leading_partial_turn_is_marked_and_not_given_a_delivery_match(self):
        with sqlite3.connect(self.agent) as db:
            db.execute("DELETE FROM session_transcript_active_events WHERE event_seq=1")
        self.model()
        r = self.collect()["runs"][0]
        self.assertTrue(r["partial_start"])
        self.assertEqual(r["delivery_status"], "unknown")
        self.assertFalse(r["wall_complete"])

    def test_snapshot_recollection_is_idempotent_and_sources_are_unchanged(self):
        self.model()
        before = {p:p.read_bytes() for p in (self.state,self.agent)}
        first, second = self.collect(), self.collect()
        first.pop("collector_elapsed_ms");second.pop("collector_elapsed_ms")
        self.assertEqual(first, second)
        self.assertEqual(before, {p:p.read_bytes() for p in before})

    def test_schema_failure_is_explicit_and_does_not_replace_previous_snapshot(self):
        out = self.root / "private/latest.json"
        t.save(out, {"previous":True})
        with sqlite3.connect(self.agent) as db:
            db.execute("DROP TABLE session_transcript_active_events")
        with mock.patch("sys.argv", ["telemetry", "--openclaw-root",str(self.root),"--output",str(out)]),contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(t.main(), 1)
        self.assertEqual(json.loads(out.read_text()), {"previous":True})
        self.assertFalse(json.loads(out.with_name("latest.json.status.json").read_text())["ok"])
        self.assertNotIn("SECRET123", stdout.getvalue())

    def test_event_limit_fails_instead_of_silently_reporting_partial_totals(self):
        self.model()
        with mock.patch.object(t, "MAX_EVENTS", 1), self.assertRaises(ValueError):
            self.collect()

    def test_private_output_and_symlink_checks(self):
        out = self.root / "private/latest.json"
        t.save(out, {"ok":True})
        self.assertEqual(out.stat().st_mode & 0o777, 0o600)
        out.chmod(0o644)
        with self.assertRaises(ValueError):t.save(out, {})
        out.unlink();out.symlink_to(self.state)
        with self.assertRaises(ValueError):t.save(out, {})

    def test_nonfinite_usage_is_missing_not_a_real_zero(self):
        self.model(usage={"input":float("nan"),"output":True,"cost":{"total":-1}})
        r = self.collect()["runs"][0]
        self.assertNotIn("input", r["tokens"])
        self.assertNotIn("output", r["tokens"])
        self.assertIsNone(r["reported_cost_total"])

    def test_compressed_frame_and_corrupt_frame(self):
        try:z = ctypes.CDLL(ctypes.util.find_library("zstd") or "libzstd.so.1")
        except OSError:self.skipTest("libzstd not installed")
        z.ZSTD_compressBound.argtypes=[ctypes.c_size_t];z.ZSTD_compressBound.restype=ctypes.c_size_t
        z.ZSTD_compress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];z.ZSTD_compress.restype=ctypes.c_size_t
        raw=b'{"type":"message","message":{"role":"user"}}';size=z.ZSTD_compressBound(len(raw));buffer=ctypes.create_string_buffer(size)
        length=z.ZSTD_compress(buffer,size,raw,len(raw),1)
        decode=t.Decoder()
        self.assertEqual(decode(None,buffer.raw[:length]), json.loads(raw))
        with self.assertRaises(ValueError):decode(None,b"invalid frame")

    def test_supervisor_envelopes_are_separate_and_never_read_cached_report_text(self):
        path=self.root/'reports.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE reports (id TEXT,task TEXT,state TEXT,model_attempts INTEGER,send_attempts INTEGER,created_ms INTEGER,response TEXT)')
            db.execute('CREATE TABLE attempts (report_id TEXT,kind TEXT,at_ms INTEGER,metrics_json TEXT)')
            db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?)',('private-id','morning','unknown',1,1,START,'PRIVATE_REPORT_CANARY'))
            db.execute('INSERT INTO attempts VALUES (?,?,?,?)',('private-id','generation',START,json.dumps({'assistant_turns':2,'usage':{'input':100},'reported_cost_usd':None,'route':'baseline','requested_thinking':'medium','private_text':'PRIVATE_REPORT_CANARY'})))
        result=t.supervised_reports(path,START-1)
        out=result['workflows']['morning']
        self.assertEqual(out['observed_assistant_turns'],2);self.assertEqual(out['states'],{'unknown':1})
        self.assertIsNone(out['reported_cost_usd']);self.assertNotIn('PRIVATE_REPORT_CANARY',json.dumps(result))
        self.assertEqual(out['route_samples'],{'baseline':1});self.assertEqual(out['requested_thinking_samples'],{'medium':1})


if __name__ == "__main__":
    unittest.main()
