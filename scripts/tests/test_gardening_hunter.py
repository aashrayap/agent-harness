from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "claude/scheduled-tasks/gardening-hunter/SKILL.md"
BRIEF = ROOT / "skills/engineering/deslop/references/scheduled-hunter.md"


class GardeningHunterTests(unittest.TestCase):
    def test_runner_is_tracked_and_installed_by_setup(self):
        self.assertTrue(RUNNER.is_file())
        self.assertIn("claude/scheduled-tasks/gardening-hunter/SKILL.md",
                      (ROOT / "setup.sh").read_text())

    def test_hunter_never_runs_the_miner(self):
        for path in (RUNNER, BRIEF):
            text = path.read_text()
            self.assertNotIn("verdict.py kinds", text, path)

    def test_hunter_reports_template_drift_and_never_writes(self):
        text = RUNNER.read_text()
        for needed in ("scheduled-hunter.md", "template/sync-rules.py drift", "`template-drift`",
                       "Never run `write` or `apply.sh`", "Report only."):
            self.assertIn(needed, text)


if __name__ == "__main__":
    unittest.main()
