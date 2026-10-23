"""Read-only native runtime test; no provider calls or actual athlete fixtures."""
import json
import os
import subprocess
import tempfile
import unittest
from _harness import REPO_ROOT

class ContextPressureNative(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('SECTION11_OPENCLAW_PACKAGE'),'Installed OpenClaw SDK required')
    def test_native_projection_preserves_canonical_history_health_and_receipts(self):
        with tempfile.TemporaryDirectory(prefix='s11-native-telegram-') as scratch:
            env={**os.environ,'OPENCLAW_STATE_DIR':scratch}
            p=subprocess.run(['node',str(REPO_ROOT/'dev/openclaw_context_pressure_smoke.mjs'),os.environ['SECTION11_OPENCLAW_PACKAGE']],text=True,capture_output=True,timeout=45,env=env)
        self.assertEqual(p.returncode,0,p.stderr)
        result=json.loads(p.stdout);self.assertTrue(result['native_telegram_notice_suppressed']);self.assertTrue(result['native_read_projection_reduced']);self.assertTrue(result['canonical_transcript_unchanged']);self.assertTrue(result['write_and_mixed_receipts_preserved']);self.assertTrue(result['oversized_prompt_blocked']);self.assertEqual(result['effective_context_tokens'],131072)
