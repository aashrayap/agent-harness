from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
README_CHECK = ROOT / "scripts/readme-check.py"
DOC_FRESH = ROOT / "scripts/doc-fresh.py"
GOOD = (ROOT / "template/README.md").read_text()


def run(*command, cwd=None, env=None):
    return subprocess.run([sys.executable, *map(str, command)], cwd=cwd, env=env, capture_output=True, text=True)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "core.hooksPath=/dev/null", *args], check=True, capture_output=True)


class ReadmeCheckTests(unittest.TestCase):
    def check(self, readme, version="0.1.0"):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            (repo / "README.md").write_text(readme)
            (repo / "VERSION").write_text(version + "\n")
            result = run(README_CHECK, repo, "--json")
            return result.returncode, json.loads(result.stdout)["problems"]

    def test_readme_check_passes_the_template_readme(self):
        self.assertEqual((0, []), self.check(GOOD))

    def test_readme_check_fails_a_status_version_that_is_not_VERSION(self):
        code, found = self.check(GOOD, "0.2.0")
        self.assertEqual(1, code)
        self.assertIn("Status Version 0.1.0 is not VERSION 0.2.0", found)

    def test_readme_check_fails_history_a_missing_diagram_and_length(self):
        no_diagram = GOOD.split("```mermaid")[0] + "## History\n\n- 2026-10-01 started\n" + "\nmore\n" * 40
        code, found = self.check(no_diagram)
        self.assertEqual(1, code)
        self.assertIn("0 Mermaid diagrams (want 1 or 2)", found)
        self.assertTrue(any(problem.startswith("history belongs in RELEASES.md") for problem in found))
        self.assertTrue(any(problem.endswith("(max 80)") for problem in found))

    def test_readme_check_lints_its_diagrams(self):
        code, found = self.check(GOOD.replace("class repo todo", "classDef hot fill:#f00"))
        self.assertEqual(1, code)
        self.assertTrue(any(problem.startswith("diagram:") for problem in found))

    def test_the_dot_agent_readme_before_2_17_0_fails_readme_check(self):
        old = subprocess.run(["git", "-C", str(ROOT), "show", "a031c96:README.md"], capture_output=True, text=True)
        if old.returncode:
            self.skipTest("commit a031c96 is not in this clone")
        code, found = self.check(old.stdout, "2.16.0")
        self.assertEqual(1, code)
        self.assertIn("no '## Status' table", found)

    def test_readme_check_passes_dot_agents_own_readme(self):
        self.assertEqual(0, run(README_CHECK, ROOT).returncode)


class DocFreshTests(unittest.TestCase):
    def repo_with_change(self, raw, files):
        repo = Path(raw)
        git(repo, "init", "-q", "-b", "main")
        (repo / "README.md").write_text("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "start")
        git(repo, "checkout", "-q", "-b", "topic")
        for name in files:
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text("changed\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "change")
        return repo

    def fresh(self, repo, body=None):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_EVENT_PATH"}
        args = [DOC_FRESH, "main"]
        if body is not None:
            (repo / ".body").write_text(body)
            args += ["--body", repo / ".body"]
        return run(*args, cwd=repo, env=env)

    def test_doc_fresh_fails_a_behavior_change_with_no_doc_and_no_reason(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.fresh(self.repo_with_change(raw, ["scripts/check"]), "Adds a check.")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("No doc change needed: <why>", result.stdout)

    def test_doc_fresh_accepts_a_doc_update_or_a_stated_reason(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual(0, self.fresh(self.repo_with_change(raw, ["tool.py", "RELEASES.md"]), "").returncode)
        with tempfile.TemporaryDirectory() as raw:
            repo = self.repo_with_change(raw, ["tool.py"])
            self.assertEqual(0, self.fresh(repo, "Refactor.\n\nNo doc change needed: same behavior\n").returncode)

    def test_doc_fresh_counts_any_file_under_docs_as_a_doc(self):
        for docs in (["tool.py", "docs/setup.md"], ["tool.py", "docs/diagram.svg"]):
            with tempfile.TemporaryDirectory() as raw:
                self.assertEqual(0, self.fresh(self.repo_with_change(raw, docs), "Adds a tool.").returncode, docs)

    def test_doc_fresh_reads_the_pr_body_from_the_github_event(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self.repo_with_change(raw, ["tool.py"])
            event = repo / ".event.json"
            event.write_text(json.dumps({"pull_request": {"body": "No doc change needed: test only"}}))
            env = dict(os.environ, GITHUB_EVENT_PATH=str(event))
            self.assertEqual(0, run(DOC_FRESH, "main", cwd=repo, env=env).returncode)
            event.write_text(json.dumps({"pull_request": {"body": "Adds a tool."}}))
            self.assertEqual(1, run(DOC_FRESH, "main", cwd=repo, env=env).returncode)

    def test_doc_fresh_fails_in_ci_without_a_base(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = self.repo_with_change(raw, ["tool.py"])
            env = dict(os.environ, CI="true")
            self.assertEqual(1, run(DOC_FRESH, "origin/nowhere", cwd=repo, env=env).returncode)

    def test_doc_fresh_skips_locally_without_a_pr_body(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.fresh(self.repo_with_change(raw, ["tool.py"]))
            self.assertEqual(0, result.returncode)
            self.assertIn("SKIP locally", result.stdout)


if __name__ == "__main__":
    unittest.main()
