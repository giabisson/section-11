"""Read-only retrieval must resolve one private account from any working directory."""
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from _harness import REPO_ROOT, load_module_by_path

p = load_module_by_path('s11_pull_credentials', REPO_ROOT/'examples/agentic/pull.py')


class PullCredentials(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root/'private'; self.directory.mkdir(mode=0o700)
        self.config = self.directory/'.sync_config.json'
        self.key = 'synthetic-private-key'
        self.write({'athlete_id': 'i123456', 'intervals_key': self.key})
        cwd = os.getcwd(); self.addCleanup(os.chdir, cwd)
        workspace = self.root/'workspace'; workspace.mkdir(); os.chdir(workspace)
        Path('.sync_config.json').write_text(json.dumps({'athlete_id':'i999', 'intervals_key':'wrong-cwd-key'}))
        patch = mock.patch.dict(os.environ, {'ATHLETE_ID':'i888', 'INTERVALS_KEY':'wrong-env-key'})
        patch.start(); self.addCleanup(patch.stop)

    def write(self, value):
        self.config.write_text(json.dumps(value)); self.config.chmod(0o600)

    def args(self, **extra):
        return SimpleNamespace(credentials_dir=str(self.directory), **extra)

    def reject(self, args=None):
        with self.assertRaises(ValueError) as caught:
            p._load_credentials(args or self.args())
        self.assertNotIn(self.key, str(caught.exception))
        self.assertIn('No fallback attempted', str(caught.exception))

    def test_explicit_account_ignores_conflicting_workspace_and_environment(self):
        self.assertEqual(p._load_credentials(self.args()), ('i123456', self.key))

    def test_missing_partial_invalid_or_nonobject_config_never_falls_back(self):
        for value in ({}, {'athlete_id':'i123456'}, {'intervals_key':self.key},
                      {'athlete_id':123,'intervals_key':self.key},
                      {'athlete_id':'i123456','intervals_key':' '}, [], None):
            with self.subTest(value=value):
                self.write(value); self.reject()
        self.config.write_text('invalid '+self.key); self.reject()
        self.config.unlink(); self.reject()

    def test_permissions_ownership_size_and_symlink_guards(self):
        self.config.chmod(0o644); self.reject(); self.config.chmod(0o600)
        self.reject(SimpleNamespace(credentials_dir='relative'))
        alias = self.root/'alias'; alias.symlink_to(self.directory)
        self.reject(SimpleNamespace(credentials_dir=str(alias)))
        self.config.write_text('x'*65537); self.reject()
        self.write({'athlete_id':'i123456','intervals_key':self.key})
        info = self.config.stat()
        with mock.patch.object(p.os, 'fstat', return_value=SimpleNamespace(
                st_mode=info.st_mode, st_uid=os.getuid()+1, st_size=info.st_size)):
            self.reject()
        target = self.directory/'original'; self.config.rename(target)
        self.config.symlink_to(target); self.reject()

    def test_explicit_account_cannot_mix_cli_values(self):
        self.reject(self.args(api_key='another-key'))
        self.reject(self.args(athlete_id='another-athlete'))

    def test_cli_trace_from_unrelated_workspace_uses_selected_account_without_echo(self):
        response = SimpleNamespace(status_code=200, json=lambda:[{'type':'watts','data':[180]}])
        fake = SimpleNamespace(get=mock.Mock(return_value=response))
        args = ['pull.py','--credentials-dir',str(self.directory),'trace',
                '--activity-id','i193686489','--types','time,watts,heartrate']
        with mock.patch.object(p.sys,'argv',args), mock.patch.object(p,'_requests',fake), contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as exit_: p.main()
        self.assertEqual(exit_.exception.code,0)
        body=json.loads(out.getvalue()); self.assertTrue(body['success'])
        self.assertNotIn(self.key,out.getvalue())
        self.assertEqual(fake.get.call_args.kwargs['auth'],('API_KEY',self.key))
        self.assertIn('/activity/i193686489/streams.json',fake.get.call_args.args[0])

    def test_cli_invalid_private_directory_returns_sanitized_json_without_network(self):
        self.config.unlink()
        args=['pull.py','--credentials-dir',str(self.directory),'units']
        with mock.patch.object(p.sys,'argv',args), mock.patch.object(p.IntervalsPull,'fetch_athlete') as network, contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as exit_: p.main()
        self.assertEqual(exit_.exception.code,1)
        self.assertFalse(json.loads(out.getvalue())['success'])
        self.assertNotIn('Traceback',out.getvalue()); network.assert_not_called()

    def test_legacy_discovery_still_works_without_explicit_directory(self):
        self.assertEqual(p._load_credentials(SimpleNamespace()),('i999','wrong-cwd-key'))
        Path('.sync_config.json').unlink()
        self.assertEqual(p._load_credentials(SimpleNamespace()),('i888','wrong-env-key'))
