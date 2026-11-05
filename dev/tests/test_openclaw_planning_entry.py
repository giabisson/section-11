"""Optional actual installed read boundary; no provider/service calls."""
import os
from pathlib import Path
import subprocess
import unittest
from _harness import REPO_ROOT

class NativePlanningEntry(unittest.TestCase):
    def test_installed_whole_skill_read_and_broker_budget(self):
        package=os.environ.get('SECTION11_OPENCLAW_PACKAGE')
        if not package or not Path(package).is_dir():
            self.skipTest('installed OpenClaw package not configured')
        result=subprocess.run(['node',str(REPO_ROOT/'dev/openclaw_planning_entry_smoke.mjs'),package],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr[-2000:])
        self.assertIn('"native_read_verified":true',result.stdout)
