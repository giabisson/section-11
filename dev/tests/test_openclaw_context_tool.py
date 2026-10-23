"""Run the dependency-free Node tool-policy and transport checks."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ContextToolNode(unittest.TestCase):
    def test_context_tool_boundaries(self):
        if not shutil.which('node'):self.fail('Node is required for OpenClaw integration checks')
        result=subprocess.run(['node','--test',str(Path(__file__).with_name('openclaw_context_tool.test.mjs'))],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
