from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("verify_profile", SCRIPTS / "verify-profile.py")
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class AutomationModelTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)

    def put(self, name: str, text: str) -> None:
        folder = self.home / "automations" / name
        folder.mkdir(parents=True)
        (folder / "automation.toml").write_text(text, encoding="utf-8")

    def test_only_pinned_off_policy_models_warn(self):
        self.put("sol", 'kind = "cron"\nmodel = "gpt-6.1-sol"\n')
        self.put("astra", 'kind = "cron"\nmodel = "gpt-6-astra"\n')
        self.put("heartbeat", 'kind = "heartbeat"\nprompt = "inherits its thread"\n')
        self.put("old", 'kind = "cron"\nmodel = "gpt-5.5"\n')
        self.put("broken", 'kind = "cron\n')
        warnings = verify.automation_model_warnings(self.home)
        self.assertEqual(2, len(warnings), warnings)
        self.assertIn("automation old: model 'gpt-5.5' is not gpt-6-astra or gpt-6.1-sol",
                      warnings)
        self.assertTrue(any(line.startswith("automation broken: unreadable") for line in warnings))
        failures_before = list(verify.failures)
        out = io.StringIO()
        with redirect_stdout(out):
            for line in warnings:
                verify.warn(line)
        self.assertIn("  WARN  automation old:", out.getvalue())
        self.assertEqual(failures_before, verify.failures)

    def test_no_automations_folder_is_fine(self):
        self.assertEqual([], verify.automation_model_warnings(self.home))


if __name__ == "__main__":
    unittest.main()
