from pathlib import Path
import shutil
import subprocess
import unittest


class CoachingToolNode(unittest.TestCase):
    def test_managed_coaching_contract_and_transport(self):
        self.assertTrue(shutil.which('node'),'Node required for integration tests')
        result=subprocess.run(['node','--test',str(Path(__file__).with_name('openclaw_coaching_tool.test.mjs'))],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
