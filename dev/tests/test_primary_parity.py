"""Parity mapping must include deployment entry points and exclude private data."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from _harness import REPO_ROOT, load_module_by_path

p=load_module_by_path('s11_primary_parity',REPO_ROOT/'dev/check_primary_parity.py')


class PrimaryParity(unittest.TestCase):
    def test_runtime_skill_and_units_are_checked_alongside_source(self):
        expected=p.targets(REPO_ROOT,Path('/source'),Path('/runtime'),Path('/skill'),Path('/units'),include_runtime=True)
        for name in ['checkout/examples/agentic/coaching_plan.py','runtime/reporter_entry.py','runtime/context-tool/policy.mjs','runtime/credential-guard/register.mjs','runtime/training_history.py','skill/SKILL.md','unit/section11-history-primary.timer']:
            self.assertIn(name,expected)
        self.assertFalse(any(n.endswith('context-primary.json') or n.endswith('report-primary.json') for n in expected))

    def test_default_checks_checkout_only(self):
        expected=p.targets(REPO_ROOT,Path('/source'),Path('/runtime'),Path('/skill'),Path('/units'))
        self.assertTrue(all(name.startswith('checkout/') for name in expected))

    def test_remote_check_detects_drift_and_missing_files_without_printing_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'source.py';path.write_text('private-canary')
            expected={'code':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
            result=subprocess.run([sys.executable,'-c',p.remote_script(expected)],capture_output=True,text=True,check=True)
            self.assertTrue(json.loads(result.stdout)['matched'])
            path.write_text('changed-private-canary')
            result=subprocess.run([sys.executable,'-c',p.remote_script(expected)],capture_output=True,text=True,check=True)
            self.assertEqual(json.loads(result.stdout)['mismatches'],['code']);self.assertNotIn('canary',result.stdout)
            path.unlink()
            result=subprocess.run([sys.executable,'-c',p.remote_script(expected)],capture_output=True,text=True,check=True)
            self.assertFalse(json.loads(result.stdout)['matched'])

    def test_source_inventory_rejects_credentials_and_symlinks(self):
        for name in ['.sync_config.json','folder/.env','../outside.py','literature/cycling-training/sources/paper.pdf']:
            with mock.patch.object(p.subprocess,'run',return_value=mock.Mock(stdout=(name+'\0').encode())):
                with self.assertRaises(ValueError):p.source_files(REPO_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'target').write_text('data');(root/'link').symlink_to(root/'target')
            with mock.patch.object(p.subprocess,'run',return_value=mock.Mock(stdout=b'link\0')):
                with self.assertRaises(ValueError):p.source_files(root)
