from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/pr-rows.py"
SPEC = importlib.util.spec_from_file_location("pr_rows", SCRIPT)
pr_rows = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pr_rows)

GOOD = ("[dot-agent#9](https://github.com/octo/dot-agent/pull/9) · v2.1.0 · "
        "Standards land — every repo gets the starter files · checks ✅ · verdict PASS · risk high · "
        "needs: merge yes/no")
LAYERS = {name: {"status": "PASS", "evidence": "x"} for name in ("checks", "contract", "live", "review")}


class PrRowsTest(unittest.TestCase):
    def test_a_complete_row_passes(self):
        self.assertEqual([], pr_rows.check_row(GOOD))

    def test_a_row_missing_a_field_fails_and_names_it(self):
        parts = GOOD.split(" · ")
        for index, name in enumerate(["link", "version", "title", "checks", "verdict", "risk", "needs"]):
            row = " · ".join(parts[:index] + parts[index + 1:])
            self.assertEqual([name], pr_rows.check_row(row), row)

    def test_owner_in_the_link_or_a_title_without_what_fails(self):
        self.assertEqual(["link"], pr_rows.check_row(GOOD.replace("[dot-agent#9]", "[octo/dot-agent#9]")))
        self.assertEqual(["title"], pr_rows.check_row(GOOD.replace(" — every repo gets the starter files", "")))
        self.assertEqual([], pr_rows.check_row(GOOD.replace("merge yes/no", "decision — pick A or B")))

    def test_check_command_skips_group_headings_and_fails_a_row_missing_a_field(self):
        broken = GOOD.replace(" · risk high", "")
        result = subprocess.run([sys.executable, str(SCRIPT), "--check", "-"],
                                input="Needs you\n" + GOOD + "\n**Running**\n" + broken + "\n",
                                capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertIn("row missing risk", result.stderr)
        ok = subprocess.run([sys.executable, str(SCRIPT), "--check", "-"], input="## Done\n" + GOOD + "\n",
                            capture_output=True, text=True)
        self.assertEqual(0, ok.returncode, ok.stderr)

    def pr(self, **extra):
        return {"number": 9, "title": "2.1.0: Standards land: every repo gets the starter files",
                "url": "https://github.com/octo/dot-agent/pull/9", "headRefOid": "a" * 40,
                "isDraft": False, "body": "", "mergedAt": None,
                "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"state": "SUCCESS"}], **extra}

    def write(self, raw, **extra):
        target = Path(raw) / "verdicts" / f"{'a' * 40}.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps({"sha": "a" * 40, "layers": LAYERS, "findings": [], "verdict": "PASS",
                                      "limits": [], **extra}))

    def test_generated_rows_take_verdict_risk_and_group_from_state(self):
        repo, agents = "octo/dot-agent", [("modified", "AGENTS.md")]
        with tempfile.TemporaryDirectory() as raw, mock.patch.dict(os.environ, {"DOT_AGENT_STATE_HOME": raw}):
            group, row = pr_rows.row_for(repo, self.pr(), agents)
            self.assertEqual("Running", group)
            self.assertIn("verdict BLOCKED · risk high · needs: agent: a PASS verdict", row)
            self.write(raw, sha="b" * 40)
            self.assertIn("verdict BLOCKED", pr_rows.row_for(repo, self.pr(), agents)[1])
            self.write(raw)
            self.assertEqual(("Needs you", GOOD), pr_rows.row_for(repo, self.pr(), agents))
            group, row = pr_rows.row_for(repo, self.pr(), [("modified", "README.md")])
            self.assertEqual("Running", group)
            self.assertIn("risk low · needs: none, the agent merges", row)
            self.assertIn("risk high", pr_rows.row_for(repo, self.pr(), None)[1])
            self.write(raw, approved={"words": "yes", "at": "now"})
            self.assertEqual("Running", pr_rows.row_for(repo, self.pr(), agents)[0])
            failing = self.pr(statusCheckRollup=[{"conclusion": "FAILURE"}])
            self.assertIn("checks ❌", pr_rows.row_for(repo, failing, agents)[1])
            self.assertEqual("Done", pr_rows.row_for(repo, self.pr(mergedAt="2026-10-16T00:00:00Z"), agents)[0])
            finding = {"severity": "BLOCKING", "kind": "x", "where": "a.py:1", "summary": "s",
                       "outcome": "open", "reason": ""}
            self.write(raw, findings=[finding], verdict="BLOCKED")
            self.assertIn("needs: agent: fix 1 BLOCKING", pr_rows.row_for(repo, self.pr(), agents)[1])

    def test_a_title_without_a_what_takes_the_first_why_sentence(self):
        pr = self.pr(title="2.2.0: verification spine", body="## Why\nBranch protection is `off`. More.\n## Scope\nx")
        with tempfile.TemporaryDirectory() as raw, mock.patch.dict(os.environ, {"DOT_AGENT_STATE_HOME": raw}):
            row = pr_rows.row_for("octo/dot-agent", pr, [])[1]
        self.assertIn(" · verification spine — Branch protection is off. · ", row)
        self.assertEqual([], pr_rows.check_row(row))

    def test_an_unversioned_title_takes_the_head_branch_version_file_or_prints_a_dash(self):
        pr = self.pr(title="chore(template): apply template 1")
        encoded = subprocess.CompletedProcess([], 0, stdout="MC4xLjEK\n", stderr="")
        missing = subprocess.CompletedProcess([], 1, stdout="", stderr="Not Found")
        with mock.patch.object(pr_rows.subprocess, "run", return_value=encoded) as run:
            self.assertEqual("0.1.1", pr_rows.branch_version("octo/web-app", "a" * 40))
        self.assertIn(f"repos/octo/web-app/contents/VERSION?ref={'a' * 40}", run.call_args.args[0])
        with mock.patch.object(pr_rows.subprocess, "run", return_value=missing):
            self.assertEqual("", pr_rows.branch_version("octo/web-app", "a" * 40))
        with tempfile.TemporaryDirectory() as raw, mock.patch.dict(os.environ, {"DOT_AGENT_STATE_HOME": raw}):
            row = pr_rows.row_for("octo/web-app", pr, [], "0.1.1")[1]
            self.assertIn(" · v0.1.1 · chore(template) — apply template 1 · ", row)
            self.assertEqual([], pr_rows.check_row(row))
            dash = pr_rows.row_for("octo/web-app", pr, [], "")[1]
            self.assertIn(" · v— · chore(template) — ", dash)
            self.assertEqual([], pr_rows.check_row(dash))
            self.assertIn(" · v2.1.0 · ", pr_rows.row_for("octo/dot-agent", self.pr(), [], "")[1])
        self.assertEqual(["version"], pr_rows.check_row(GOOD.replace("v2.1.0", "v?")))

    def test_rows_print_under_needs_you_running_and_done(self):
        rows = [("Done", "d"), ("Needs you", "n"), ("Running", "r1"), ("Running", "r2")]
        self.assertEqual(["Needs you", "n", "Running", "r1", "r2", "Done", "d"], pr_rows.grouped(rows))
        self.assertEqual(["Done", "d"], pr_rows.grouped([("Done", "d")]))

    def test_global_communication_rules_name_scripts_by_absolute_path(self):
        text = (ROOT / "AGENTS.md").read_text()
        section = text.split("## Communication", 1)[1].split("\n## ", 1)[0]
        for path in re.findall(r"`([^`\s]*scripts/[^`\s]+)", section):
            self.assertTrue(path.startswith("~/.dot-agent/"), path)


if __name__ == "__main__":
    unittest.main()
