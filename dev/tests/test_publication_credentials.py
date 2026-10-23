"""Explicit account credential loading from an unrelated working directory."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from _harness import REPO_ROOT,load_module_by_path
p=load_module_by_path('s11_explicit_credentials',REPO_ROOT/'examples/agentic/push.py')

class CredentialDirectory(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.directory=self.root/'data';self.directory.mkdir(mode=0o700)
        self.file=self.directory/'.sync_config.json';self.write({'athlete_id':'i123456','intervals_key':'synthetic-private-key'})
        self.cwd=os.getcwd();self.addCleanup(os.chdir,self.cwd)
        workspace=self.root/'workspace';workspace.mkdir();os.chdir(workspace)
        Path('.sync_config.json').write_text(json.dumps({'athlete_id':'i999','intervals_key':'wrong-cwd-key'}))
    def write(self,value):
        self.file.write_text(json.dumps(value));self.file.chmod(0o600)
    def args(self,**extra):return SimpleNamespace(credentials_dir=str(self.directory),**extra)
    def test_complete_pair_ignores_other_cwd_and_environment_accounts(self):
        with mock.patch.dict(os.environ,{'ATHLETE_ID':'i888','INTERVALS_KEY':'wrong-env-key'}):
            self.assertEqual(p._load_credentials(self.args()),('i123456','synthetic-private-key'))
    def test_explicit_failure_never_falls_back_or_echoes_values(self):
        for value in [{},{'athlete_id':'i123456'},{'intervals_key':'synthetic-private-key'},{'athlete_id':123,'intervals_key':'synthetic-private-key'}]:
            self.write(value)
            with self.assertRaises(ValueError) as error:p._load_credentials(self.args())
            self.assertNotIn('synthetic-private-key',str(error.exception))
        self.file.unlink()
        with self.assertRaises(ValueError):p._load_credentials(self.args())
    def test_private_regular_owned_file_and_absolute_directory_required(self):
        self.file.chmod(0o644)
        with self.assertRaises(ValueError):p._load_credentials(self.args())
        self.file.chmod(0o600)
        with self.assertRaises(ValueError):p._load_credentials(SimpleNamespace(credentials_dir='relative'))
        with self.assertRaises(ValueError):p._load_credentials(self.args(api_key='do-not-mix'))
        target=self.directory/'alias';self.file.rename(target);self.file.symlink_to(target)
        with self.assertRaises(ValueError):p._load_credentials(self.args())
    def test_push_parser_supports_explicit_directory_and_defaults_to_preview(self):
        args=['push.py','--credentials-dir',str(self.directory),'--name','Synthetic','--date','2099-01-01','--duration','30']
        with mock.patch.object(sys,'argv',args),mock.patch.object(p.IntervalsPush,'preview_push',return_value={'success':True,'mode':'preview'}) as preview,mock.patch.object(p.IntervalsPush,'push_workouts') as write,contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit):p.main()
        self.assertEqual(json.loads(out.getvalue())['mode'],'preview');preview.assert_called_once();write.assert_not_called()
