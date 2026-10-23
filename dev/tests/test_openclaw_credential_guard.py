"""Run the dependency-free Node credential-boundary regressions with unittest."""
import pathlib
import shutil
import subprocess
import unittest


class CredentialGuard(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for the OpenClaw plugin tests")
    def test_pre_model_and_persistence_boundaries(self):
        path = pathlib.Path(__file__).with_name("openclaw_credential_guard.test.mjs")
        result = subprocess.run(["node", "--test", str(path)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
