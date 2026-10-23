"""Credential replacement and delivery audits with synthetic private fixtures."""
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

from _harness import REPO_ROOT, load_module_by_path

safety = load_module_by_path("s11_runtime_safety", REPO_ROOT / "examples/agentic/openclaw/runtime_safety.py")


class RuntimeSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / ".sync_config.json"
        self.old = "synthetic-old-credential-12345"
        self.new = "synthetic-new-credential-67890"
        self.write(self.config, {"athlete_id": "i123456", "intervals_key": self.old, "week_start": "mon"})

    def write(self, path, data):
        path.write_text(json.dumps(data))
        path.chmod(0o600)

    def test_rotation_verifies_before_updating_all_consumers_without_printing_keys(self):
        env = self.root / ".env"
        env.write_text("OTHER=preserved\nINTERVALS_KEY=" + self.old + "\n")
        env.chmod(0o600)
        with mock.patch.object(safety.getpass, "getpass", side_effect=[self.new, self.new]), mock.patch.object(safety, "verify_intervals_key") as verify:
            result = safety.replace_key(self.root, [env])
        verify.assert_called_once_with("i123456", self.new)
        self.assertEqual(json.loads(self.config.read_text())["intervals_key"], self.new)
        self.assertEqual(json.loads(self.config.read_text())["week_start"], "mon")
        self.assertIn("OTHER=preserved", env.read_text())
        self.assertIn(self.new, env.read_text())
        self.assertEqual(result["consumer_files_updated"], 2)
        self.assertNotIn(self.new, json.dumps(result))
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)

    def test_bad_or_unverified_input_changes_nothing(self):
        original = self.config.read_bytes()
        for values in ([self.new, "mismatch"], [self.old, self.old], [self.new, self.new]):
            with self.subTest(values=values), mock.patch.object(safety.getpass, "getpass", side_effect=values), mock.patch.object(safety, "verify_intervals_key", side_effect=ValueError("unavailable")):
                with self.assertRaises(ValueError):
                    safety.replace_key(self.root)
                self.assertEqual(self.config.read_bytes(), original)

    def test_partial_replacement_can_resume_with_already_updated_consumer(self):
        env = self.root / ".env"
        env.write_text("INTERVALS_KEY=" + self.new)
        env.chmod(0o600)
        with mock.patch.object(safety.getpass, "getpass", side_effect=[self.new, self.new]), mock.patch.object(safety, "verify_intervals_key"):
            result = safety.replace_key(self.root, [env])
        self.assertTrue(result["success"])
        self.assertEqual(json.loads(self.config.read_text())["intervals_key"], self.new)

    def test_public_and_symlink_consumers_are_rejected_before_prompting(self):
        for kind in ["public", "symlink"]:
            target = self.root / kind
            if kind == "public":
                target.write_text(self.old)
                target.chmod(0o644)
            else:
                target.symlink_to(self.config)
            with self.subTest(kind=kind), mock.patch.object(safety.getpass, "getpass") as prompt:
                with self.assertRaises(ValueError):
                    safety.replace_key(self.root, [target])
                prompt.assert_not_called()

    def test_audit_distinguishes_generation_from_delivery_and_never_exposes_targets(self):
        config = self.root / "openclaw.json"
        self.write(config, {"channels": {"telegram": {"botToken": self.old, "allowFrom": ["1234567"]}}})
        state = self.root / "state"
        state.mkdir()
        with sqlite3.connect(state / "openclaw.sqlite") as db:
            db.execute("CREATE TABLE cron_jobs (name TEXT, job_json TEXT, state_json TEXT)")
            db.execute("INSERT INTO cron_jobs VALUES (?,?,?)", ("morning-readiness", json.dumps({"enabled": True, "delivery": {"to": "1234567", "bestEffort": False}}), json.dumps({"lastStatus": "ok", "lastDeliveryStatus": "not-delivered", "lastDeliveryError": "chat not found"})))
        with mock.patch.object(safety, "telegram_get", side_effect=[{"ok": True}, {"ok": False}]):
            out = safety.audit(config, self.root)
        row = out["jobs"][0]
        self.assertEqual(row["generation_status"], "ok")
        self.assertEqual(row["delivery_status"], "not-delivered")
        self.assertFalse(row["bot_can_access_chat"])
        self.assertTrue(row["target_is_allowlisted"])
        self.assertNotIn("1234567", json.dumps(out))
        self.assertNotIn(self.old, json.dumps(out))
        self.assertEqual(out["messages_sent"], 0)

    def test_transport_errors_do_not_return_credential_urls(self):
        with mock.patch.object(safety.request, "urlopen", side_effect=OSError("https://api.telegram.org/bot" + self.old)):
            out = safety.telegram_get(self.old, "getMe")
        self.assertFalse(out["ok"])
        self.assertNotIn(self.old, json.dumps(out))

    def test_supervised_audit_checks_exact_command_and_separate_delivery_owner(self):
        config=self.root/'openclaw.json';profile=self.root/'report-primary.json'
        self.write(config,{'channels':{'telegram':{'botToken':self.old,'allowFrom':['1234567']}}})
        self.write(profile,{'openclaw_config':str(config),'target':'1234567','bot_id':'777'})
        (self.root/'state').mkdir()
        with sqlite3.connect(self.root/'state/openclaw.sqlite') as db:
            db.execute('CREATE TABLE cron_jobs (name TEXT,job_json TEXT,state_json TEXT)')
            for name,op in [('morning-readiness','morning'),('weekly-review','weekly')]:
                argv=['/usr/bin/python3',str(self.root/'report_runner.py'),'--profile',str(profile),op]
                job={'payload':{'kind':'command','argv':argv},'delivery':{'mode':'none'}}
                db.execute('INSERT INTO cron_jobs VALUES (?,?,?)',(name,json.dumps(job),json.dumps({'lastStatus':'ok','lastDeliveryStatus':'not-requested'})))
        with mock.patch.object(safety,'telegram_get',side_effect=[{'ok':True,'result':{'id':777}},{'ok':True},{'ok':True}]):
            out=safety.audit(config,self.root,profile)
        self.assertTrue(out['routing_ready'])
        self.assertTrue(all(j['delivery_owner']=='report_supervisor' and j['generation_status'] is None and j['delivery_status']=='see_supervisor_ledger' for j in out['jobs']))
        self.assertNotIn('1234567',json.dumps(out))

    def test_wrong_athlete_response_cannot_validate_a_replacement(self):
        for body in [{"id": "i654321"}, [], {}]:
            response = contextlib.nullcontext(io.StringIO(json.dumps(body)))
            with self.subTest(body=body), mock.patch.object(safety.request, "urlopen", return_value=response):
                with self.assertRaises(ValueError):
                    safety.verify_intervals_key("i123456", self.new)

    def test_verification_uses_an_explicit_application_user_agent(self):
        response = contextlib.nullcontext(io.StringIO('{"id":"i123456"}'))
        with mock.patch.object(safety.request, "urlopen", return_value=response) as fetch:
            safety.verify_intervals_key("i123456", self.new)
        req = fetch.call_args.args[0]
        self.assertEqual(req.get_header("User-agent"), "Section11/1.0")
        self.assertEqual(req.get_header("Accept"), "application/json")

    def test_cli_reports_http_status_without_provider_content_or_file_changes(self):
        original = self.config.read_bytes()
        provider_error = HTTPError("https://example.invalid/" + self.new, 401,
                                   self.new, {}, io.BytesIO(self.new.encode()))
        with mock.patch("sys.argv", ["runtime_safety.py", "replace-key", "--data-dir", str(self.root)]), mock.patch.object(safety.sys.stdin, "isatty", return_value=True), mock.patch.object(safety.getpass, "getpass", side_effect=[self.new, self.new]), mock.patch.object(safety.request, "urlopen", side_effect=provider_error), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(safety.main(), 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["error_code"], "intervals_http_error")
        self.assertEqual(result["http_status"], 401)
        self.assertNotIn(self.new, output.getvalue())
        self.assertEqual(self.config.read_bytes(), original)

    def test_hidden_input_diagnostics_are_distinct_and_do_not_echo_input(self):
        for entries, code in [([self.new, "different"], "key_input_mismatch"),
                              ([self.old, self.old], "unchanged_key"),
                              (["has space", "has space"], "invalid_key_input")]:
            with self.subTest(code=code), mock.patch.object(safety.getpass, "getpass", side_effect=entries), mock.patch.object(safety, "verify_intervals_key") as verify:
                with self.assertRaises(safety.CredentialError) as caught:
                    safety.replace_key(self.root)
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn(entries[0], str(caught.exception))
                verify.assert_not_called()

    def test_cli_requires_a_terminal_before_asking_for_a_key(self):
        with mock.patch("sys.argv", ["runtime_safety.py", "replace-key", "--data-dir", str(self.root)]), mock.patch.object(safety.sys.stdin, "isatty", return_value=False), mock.patch.object(safety.getpass, "getpass") as prompt, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(safety.main(), 1)
        prompt.assert_not_called()

    def test_cli_never_echoes_malformed_private_file(self):
        self.config.write_text('{"intervals_key": "' + self.old)
        with mock.patch("sys.argv", ["runtime_safety.py", "replace-key", "--data-dir", str(self.root)]), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(safety.main(), 1)
        self.assertNotIn(self.old, output.getvalue())


if __name__ == "__main__":
    unittest.main()
