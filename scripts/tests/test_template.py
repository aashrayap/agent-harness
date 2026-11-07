from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKELETON = ["README.md", "AGENTS.md", "CLAUDE.md", "CONSTRAINTS.tsv", "GLOSSARY.md",
            "VERIFY.md", "VERSION", "RELEASES.md", "scripts/check", "scripts/private-boundary.py"]


class TemplateTests(unittest.TestCase):
    def run_in(self, repo, *command):
        environment = {k: v for k, v in os.environ.items() if k != "CI"}
        environment["PYTHON"] = sys.executable
        return subprocess.run(command, cwd=repo, env=environment, capture_output=True, text=True)

    def test_a_repo_made_from_the_template_passes_its_own_check_and_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            self.run_in(repo, "git", "init", "-q", "-b", "main")
            mine = (ROOT / "template/README.md").read_text().replace("# REPO", "# Mine")
            (repo / "README.md").write_text(mine)
            applied = self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertIn("kept   README.md", applied.stdout)
            self.assertEqual(mine, (repo / "README.md").read_text())
            for relative in SKELETON:
                self.assertTrue((repo / relative).is_file(), relative)
            self.assertEqual("@AGENTS.md\n", (repo / "CLAUDE.md").read_text())
            self.run_in(repo, "git", "add", "-A")
            self.run_in(repo, "git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=t",
                        "-c", "user.email=t@example.com", "commit", "-qm", "start")
            unlisted = self.run_in(repo, "scripts/check")
            self.assertEqual(0, unlisted.returncode, unlisted.stdout)
            self.assertIn("WARNING: no private names list: create", unlisted.stdout)
            (repo / ".git/info/private-markers").write_text("Dr Example\n")
            checked = self.run_in(repo, "scripts/check", "--tests")
            self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)
            self.assertIn("private-boundary: PASS", checked.stdout)
            again = self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
            self.assertNotIn("added", again.stdout)

    def test_apply_accepts_a_worktree_and_refuses_a_subfolder_or_a_plain_folder(self):
        with tempfile.TemporaryDirectory() as raw:
            repo, tree, plain = Path(raw) / "repo", Path(raw) / "tree", Path(raw) / "plain"
            repo.mkdir()
            plain.mkdir()
            self.run_in(repo, "git", "init", "-q", "-b", "main")
            self.run_in(repo, "git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q",
                        "--allow-empty", "-m", "start")
            self.run_in(repo, "git", "worktree", "add", "-q", "-b", "side", str(tree))
            self.assertTrue((tree / ".git").is_file())
            applied = self.run_in(tree, "bash", str(ROOT / "template/apply.sh"), str(tree))
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertTrue((tree / "VERIFY.md").is_file())
            (repo / "sub").mkdir()
            for target in (repo / "sub", plain):
                refused = self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(target))
                self.assertEqual(1, refused.returncode, target)
                self.assertIn("usage:", refused.stderr)

    def test_a_repo_missing_a_skeleton_file_fails_its_check(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            self.run_in(repo, "git", "init", "-q", "-b", "main")
            self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
            (repo / "VERIFY.md").unlink()
            checked = self.run_in(repo, "scripts/check")
            self.assertNotEqual(0, checked.returncode)
            self.assertIn("skeleton: missing VERIFY.md", checked.stdout)

    def test_template_check_lint_flags_a_syntax_error(self):
        for name, text in (("tool.py", "def broken(:\n"), ("run.sh", "if then\n"), ("data.json", "{nope")):
            with tempfile.TemporaryDirectory() as raw:
                repo = Path(raw)
                self.run_in(repo, "git", "init", "-q", "-b", "main")
                self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
                self.run_in(repo, "git", "add", "-A")
                self.assertIn("lint: PASS", self.run_in(repo, "scripts/check").stdout)
                (repo / name).write_text(text)
                self.run_in(repo, "git", "add", name)
                checked = self.run_in(repo, "scripts/check")
                self.assertNotEqual(0, checked.returncode, name)
                self.assertNotIn("lint: PASS", checked.stdout, name)

    def test_conform_checks_every_template_item_on_a_template_repo_and_names_a_miss(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            self.run_in(repo, "git", "init", "-q", "-b", "main")
            self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
            conform = [sys.executable, str(ROOT / "template/conform.py"), str(repo), "--json"]
            passed = self.run_in(repo, *conform)
            self.assertEqual(0, passed.returncode, passed.stdout)
            self.assertEqual(15, json.loads(passed.stdout)[0]["passed"])
            (repo / "GLOSSARY.md").unlink()
            missed = self.run_in(repo, *conform)
            self.assertEqual(1, missed.returncode)
            self.assertFalse(json.loads(missed.stdout)[0]["checks"]["GLOSSARY.md"])
            self.assertFalse((repo / "conform.py").exists())
            empty = self.run_in(repo, sys.executable, str(ROOT / "template/conform.py"), "--json")
            self.assertEqual(2, empty.returncode)
            self.assertIn("usage:", empty.stderr)

    def sync(self, *args):
        result = self.run_in(ROOT, sys.executable, str(ROOT / "template/sync-rules.py"), *args, "--json")
        row = json.loads(result.stdout or "[{}]")[0]
        return result.returncode, row.get("status", row.get("gaps"))

    def test_sync_rules_writes_the_cloud_safe_slice_with_a_stamp_and_check_catches_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            rules = Path(raw) / ".claude/rules/dot-agent.md"
            self.assertEqual((1, "missing"), self.sync("check", raw))
            self.assertEqual((1, "no folder"), self.sync("write", f"{raw}/typo"))
            self.assertFalse(Path(raw, "typo").exists())
            self.assertEqual("written", self.sync("write", raw)[1])
            head, _, body = rules.read_text().partition("\n")
            self.assertRegex(head, rf"^<!-- dot-agent {(ROOT / 'VERSION').read_text().strip()} sha256:[0-9a-f]{{64}} ")
            pause = (ROOT / "AGENTS.md").read_text().split("## Always pause")[1].split("\n\n")[2]
            bullets = [" ".join(bullet.split()) for bullet in ("\n" + pause).split("\n- ")[1:]]
            merge = "merging a high-risk PR: " + bullets[0].split(": ", 1)[1].split(". `HIGH_RISK`")[0] + ";\n"
            for kept in ["## Models", "## Judgment", "## Communication", "the owner's explicit instruction.\n", merge,
                         "\nCompleted, verified topic-branch work ships:", "instead of adding prose here.\n",
                         "## Every repo", "The repo is the memory", "its own AGENTS.md wins.", "\n| For | Go to |\n|---|---|\n| What a word means | `GLOSSARY.md` |\n",
                         "- Domains: work belongs", "Diagrams: draw small",
                         "In committed Markdown, write Mermaid in a fenced `mermaid` block. Elsewhere, use a labeled tree."] + bullets[1:]:
                self.assertIn(kept, body)
            for dropped in ("mermaid-widget", "legend and click-to-zoom", "show_widget", "setup.sh", "setup pins", "verify-profile",
                            "~/", "verdict.py", "Agents may merge", "Any other harness update", "ChatGPT",
                            "`correct`"):
                self.assertNotIn(dropped, body)
            self.assertEqual((0, "current"), self.sync("check", raw))
            old = body.replace("Simpler", "Older")
            rules.write_text(f"<!-- dot-agent 0 sha256:{hashlib.sha256(old.encode()).hexdigest()} x -->\n{old}")
            self.assertEqual((1, "stale"), self.sync("check", raw))
            self.assertEqual("written", self.sync("write", raw)[1])

    def test_sync_rules_write_refuses_a_hand_edited_file_and_conform_flags_it(self):
        with tempfile.TemporaryDirectory() as raw:
            self.run_in(raw, "git", "init", "-q", "-b", "main")
            self.run_in(raw, "bash", str(ROOT / "template/apply.sh"), raw)
            self.sync("write", raw)
            conform = [sys.executable, str(ROOT / "template/conform.py"), raw]
            self.assertEqual(0, self.run_in(raw, *conform).returncode)
            rules = Path(raw) / ".claude/rules/dot-agent.md"
            edited = rules.read_text() + "- my own rule\n"
            rules.write_text(edited)
            self.assertEqual((1, "hand-edited"), self.sync("write", raw))
            self.assertEqual(edited, rules.read_text())
            self.assertIn("MISS .claude/rules/dot-agent.md stamp", self.run_in(raw, *conform).stdout)

    def test_sync_rules_drift_names_each_gap_and_its_fix_and_skips_repos_off_the_template(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual((0, None), self.sync("drift", raw))
            self.run_in(raw, "git", "init", "-q", "-b", "main")
            self.run_in(raw, "bash", str(ROOT / "template/apply.sh"), raw)
            self.assertEqual((0, []), self.sync("drift", raw))
            self.sync("write", raw)
            rules = Path(raw, ".claude/rules/dot-agent.md")
            rules.write_text(rules.read_text() + "- my own rule\n")
            code, gaps = self.sync("drift", raw)
            self.assertEqual(1, code)
            self.assertRegex(" ".join(gaps), r"its cloud rules file is hand-edited: .*sync-rules.py write")
            rules.unlink()
            agents = Path(raw, "AGENTS.md")
            agents.write_text(agents.read_text().replace("Follows template 2.", "Follows template 0."))
            Path(raw, "GLOSSARY.md").unlink()
            gaps = self.sync("drift", raw)[1]
            self.assertEqual(["it follows template 0, not 2", "conform misses GLOSSARY.md"], [g.split(":")[0] for g in gaps])
            self.assertEqual((0, []), self.sync("drift", str(ROOT)))

    def test_dot_agent_ships_its_skills_as_a_plugin_from_the_committed_copy(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(("dot-agent", "./.claude/skills/"), (plugin["name"], plugin["skills"]))
        self.assertTrue(list((ROOT / ".claude/skills").glob("*/SKILL.md")))
        self.assertEqual([("dot-agent", "./")], [(p["name"], p["source"]) for p in market["plugins"]])

    def test_the_template_files_are_starters_that_apply_copies_alone(self):
        self.assertEqual((ROOT / "scripts/private-boundary.py").read_bytes(),
                         (ROOT / "template/scripts/private-boundary.py").read_bytes())
        self.assertNotIn('dirname "$TEMPLATE"', (ROOT / "template/apply.sh").read_text())
        self.assertIn("Follows template 2.", (ROOT / "template/AGENTS.md").read_text())
        for verify in (ROOT / "VERIFY.md", ROOT / "template/VERIFY.md"):
            self.assertNotIn("fails until", verify.read_text(), verify)
        for relative in ("AGENTS.md", "VERIFY.md", "RELEASES.md", "CONSTRAINTS.tsv", "README.md"):
            text = (ROOT / "template" / relative).read_text()
            for personal in (r"\bAsh\b", r"\bhis\b", r"\bpos\b", r"~/\.dot-agent", r"verdict\.py"):
                self.assertNotRegex(text, personal, relative)

    def test_conform_validates_launchpad_json_only_when_present(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            self.run_in(repo, "git", "init", "-q", "-b", "main")
            self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
            conform = [sys.executable, str(ROOT / "template/conform.py"), str(repo), "--json"]
            item = "launchpad.json matches template/schemas/launchpad.schema.json (or no file)"
            entry = {"name": "example-api", "class": "writable", "path": "repos/example-api",
                     "remote": "git@example.com:team/example-api", "role": "The backend.", "host": "Git host"}
            launchpad = {"version": 1, "name": "Launchpad", "kind": "domain", "repositories": [entry]}
            (repo / "launchpad.json").write_text(json.dumps(launchpad))
            self.assertTrue(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"][item])
            for broken in ({**entry, "class": "vendored"}, {k: v for k, v in entry.items() if k != "remote"}):
                (repo / "launchpad.json").write_text(json.dumps({**launchpad, "repositories": [broken]}))
                self.assertFalse(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"][item], broken)
            (repo / "launchpad.json").write_text(json.dumps({**launchpad, "version": True}))
            self.assertFalse(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"][item])
            (repo / "launchpad.json").write_text("{nope")
            self.assertFalse(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"][item])

    def test_conform_accepts_a_claude_symlink_and_needs_the_exact_ci_command(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            self.run_in(repo, "git", "init", "-q", "-b", "main")
            self.run_in(repo, "bash", str(ROOT / "template/apply.sh"), str(repo))
            conform = [sys.executable, str(ROOT / "template/conform.py"), str(repo), "--json"]
            (repo / "CLAUDE.md").unlink()
            (repo / "CLAUDE.md").symlink_to("AGENTS.md")
            self.assertEqual(0, self.run_in(repo, *conform).returncode)
            (repo / "CLAUDE.md").unlink()
            (repo / "CLAUDE.md").symlink_to("README.md")
            self.assertFalse(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"][
                "CLAUDE.md is @AGENTS.md or a symlink to it"])
            ci = repo / ".github/workflows/ci.yml"
            original = ci.read_text()
            for form in ("run: |\n          scripts/check --tests", 'run: "./scripts/check --tests"',
                         "run: bash scripts/check --tests  # gate"):
                ci.write_text(original.replace("run: scripts/check --tests", form))
                self.assertTrue(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"][
                    "CI runs scripts/check --tests"], form)
            ci.write_text(original.replace("run: scripts/check --tests", "run: echo skip scripts/check"))
            self.assertFalse(json.loads(self.run_in(repo, *conform).stdout)[0]["checks"]["CI runs scripts/check --tests"])


if __name__ == "__main__":
    unittest.main()
