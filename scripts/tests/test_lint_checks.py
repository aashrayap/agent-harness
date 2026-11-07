from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


one_home = load("one-home-check")
forbidden = load("forbidden-words")
manifests = load("validate-skill-manifests")
no_comments = load("no-comments")
private = load("private-boundary")


class LintCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def put(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_profile_lint_fails_the_813e1ab_trusted_projects_and_permission_bypasses(self):
        spec = importlib.util.spec_from_file_location("profile_lint", ROOT / "scripts/profile-lint.py")
        lint = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lint)
        before_813e1ab = 'model = "gpt-5"\n\n[projects."__HOME__"]\ntrust_level = "trusted"\n'
        self.assertIn("trusted-project allowlist", " ".join(lint.config_problems("codex/config.work.toml", before_813e1ab)))
        bypass = '{"permissions": {"defaultMode": "bypassPermissions"}, "skipDangerousModePermissionPrompt": true}'
        self.assertIn("permission bypass", " ".join(lint.config_problems("claude/settings.json", bypass)))
        self.assertIn("permission bypass", " ".join(lint.config_problems(
            "codex/config.toml", 'approval_policy = "never"\nsandbox_mode = "danger-full-access"\n')))
        for relative in ("claude/model-lock.json", "codex/config.toml", "claude/hooks.json"):
            self.assertEqual([], lint.config_problems(relative, (ROOT / relative).read_text()), relative)
        self.assertEqual([], lint.config_problems("claude/hooks/merge-gate.py", "trust_level"))

    def test_dropped_rules_fails_the_297314a_agents_trim_and_passes_its_repair(self):
        spec = importlib.util.spec_from_file_location("dropped_rules", ROOT / "scripts/dropped-rules.py")
        rules = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rules)
        if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", "297314a^{commit}"],
                          capture_output=True).returncode:
            self.skipTest("commit 297314a is not in this clone")
        show = lambda ref: subprocess.run(["git", "-C", str(ROOT), "show", ref], capture_output=True,
                                          text=True, check=True).stdout
        before = show("0a1be7a^:AGENTS.md")
        trimmed = rules.dropped(before, show("297314a^:AGENTS.md"))
        self.assertIn("Preserve dirty work and use supported owner transactions for state.", trimmed)
        repaired = rules.dropped(before, show("297314a:AGENTS.md"))
        self.assertNotIn("Preserve dirty work and use supported owner transactions for state.", repaired)
        self.assertLess(len(repaired), len(trimmed))
        reworded = before.replace("Preserve dirty work and use supported owner transactions for state.",
                                  "Preserve dirty work, and use the supported owner transactions for state.")
        self.assertEqual([], rules.dropped(before, reworded))
        quoted = show("297314a^:AGENTS.md") + "\nDropped: " + " ".join(trimmed)
        self.assertEqual([], rules.dropped(before, quoted))

    def test_one_home_flags_a_sentence_in_two_files(self):
        sentence = "Every Task and Chat has exactly one home in the dashboard.\n"
        self.put("a.md", sentence)
        self.put("b.md", "Intro.\n" + sentence.replace("dashboard", "dash-board"))
        self.put("c.md", "Every Task has a home.\n")
        found = one_home.duplicates(self.root, ["a.md", "b.md", "c.md"])
        self.assertEqual([["a.md", "b.md"]], [files for files, _ in found])

    def test_forbidden_words_respect_allowlist_and_apple_watch(self):
        self.put("README.md", "Ask the Atlas.\nApple Watch steps.\n```mermaid\n```\n")
        self.put("scripts/fixtures/retired-runtime.json", "Atlas is retired.\n")
        found = forbidden.findings(self.root, ["README.md", "scripts/fixtures/retired-runtime.json"])
        self.assertEqual(["README.md:1: retired or forbidden: Atlas"], found)

    def test_forbidden_words_retire_router_but_keep_the_config_fallback(self):
        self.put("README.md", "Ask the Router.\nUse $router.\nconfig router_session\n")
        found = forbidden.findings(self.root, ["README.md"])
        self.assertEqual(["README.md:1: retired or forbidden: Router",
                          "README.md:2: retired or forbidden: Router"], found)

    def test_private_boundary_flags_names_home_paths_and_markers(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        paths = ["notes.private.md", ".env", "scripts/a.py", "tests/test_a.py", "README.md", "docs/a.md"]
        home = "/" + "Users/someone/"
        for path, text in zip(paths, ["x\n", "A=1\n", f'HOME = "{home}data"\n',
                                      f'HOME = "{home}fixture"\n',
                                      "see ~/.private and /Users/x/app\n", "Dr Example said\n"]):
            self.put(path, text)
        self.put(".git/info/private-markers", "Dr Example\n")
        self.assertEqual(["notes.private.md: private file name is tracked",
                          ".env: private file name is tracked",
                          "scripts/a.py:1: absolute home path; use ~ or an env var",
                          "docs/a.md:1: private marker"],
                         private.problems(self.root, paths))

    def test_private_boundary_lists_non_ascii_paths_unquoted(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.put(".git/info/private-markers", "Dr Example\n")
        (self.root / "passé.jpg").write_bytes(b"\xff\xd8")
        subprocess.run(["git", "-C", str(self.root), "add", "passé.jpg"], check=True)
        self.assertEqual(["passé.jpg"], [f.split(":")[0] for f in private.problems(self.root)])

    def test_private_boundary_reads_markers_from_a_worktree(self):
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
               "-c", "core.hooksPath=/dev/null"]
        main, linked = self.root / "main", self.root / "linked"
        subprocess.run(git + ["init", "-q", str(main)], check=True)
        subprocess.run(git + ["-C", str(main), "commit", "-q", "--allow-empty", "-m", "start"],
                       check=True)
        subprocess.run(git + ["-C", str(main), "worktree", "add", "-q", str(linked)], check=True)
        (main / ".git/info/private-markers").write_text("Dr Example\n")
        (linked / "a.md").write_text("Dr Example said\n")
        self.assertTrue((linked / ".git").is_file())
        self.assertEqual(["a.md:1: private marker"], private.problems(linked, ["a.md"]))

    def test_private_boundary_fails_a_tracked_scan_unless_allowlisted_with_a_reason(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.put(".git/info/private-markers", "Dr Example\n")
        for path in ("scan.pdf", "docs/photo.JPG", "a.heic", "letter.docx", "logo.png"):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_bytes(b"%PDF-1.4 binary")
        paths = ["scan.pdf", "docs/photo.JPG", "a.heic", "letter.docx", "logo.png", "docs/a.svg"]
        self.put("docs/a.svg", "<svg/>\n")
        self.put("scripts/private-boundary.allow", "# path<TAB>reason\nlogo.png\tproject logo, no personal data\nletter.docx\n")
        found = private.problems(self.root, paths)
        self.assertEqual(["scripts/private-boundary.allow:3: give a reason after a tab",
                          "scan.pdf", "docs/photo.JPG", "a.heic"],
                         [found[0]] + [f.split(":")[0] for f in found[1:]])

    def test_private_boundary_flags_a_numbers_and_ssns_but_not_dates_versions_or_phones(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.put(".git/info/private-markers", "Dr Example\n")
        hits = ["Receipt A" + "123456789", "A-" + "123-456-789 on the card", "A " + "123 456 789",
                "A" + "12345678", "SSN " + "123-45-" + "6789.", "ssn: " + "123 45 " + "6789",
                "A#" + "123456789", "A–" + "123–456–789"]
        misses = ["2026-10-17 and 10/17/2026", "version 1.234.567 and 12.345.6789",
                  "call 555-123-4567 or (555) 123 4567 or +1 555 12 3456",
                  "sha a123456789 0xA123456789 A1234567890 BA123456789",
                  "zip 12345-6789 and 000-12-3456 and 900-12-3456", "id 123456789",
                  "versions A12345678.1 and 123-45-6789.2"]
        self.put("a.md", "\n".join(hits + misses) + "\n")
        self.assertEqual(["a.md:1: looks like an A-number", "a.md:2: looks like an A-number",
                          "a.md:3: looks like an A-number", "a.md:4: looks like an A-number",
                          "a.md:5: looks like an SSN", "a.md:6: looks like an SSN",
                          "a.md:7: looks like an A-number", "a.md:8: looks like an A-number"],
                         private.problems(self.root, ["a.md"]))

    def test_private_boundary_warns_without_a_names_list(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.put("a.md", "fine\n")
        self.assertEqual([], private.problems(self.root, ["a.md"]))
        self.put(".git/info/private-markers", "\n")
        self.assertEqual([], private.problems(self.root, ["a.md"]))
        script = self.root / "scripts/private-boundary.py"
        script.parent.mkdir()
        script.write_bytes((ROOT / "scripts/private-boundary.py").read_bytes())
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        environment = {k: v for k, v in os.environ.items() if k != "CI"}
        run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, env=environment)
        self.assertEqual(0, run.returncode, run.stdout)
        self.assertIn("WARNING: no private names list: create", run.stdout)
        self.assertIn("private-markers", run.stdout)
        self.assertIn("private-boundary: PASS", run.stdout)
        run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                             env={**environment, "CI": "true"})
        self.assertEqual(0, run.returncode, run.stdout)
        self.assertIn("names scan skipped in CI: no private list", run.stdout)

    def test_skill_description_length_is_capped(self):
        for length, expected in ((200, []), (201, ["SKILL.md description is 201 chars; keep it at most 200"])):
            self.put("skills/x/SKILL.md", "---\nname: x\ndescription: >\n  " + "d" * length + "\n---\n")
            result = manifests.Result()
            manifests.check_skill(self.root / "skills/x", result)
            messages = [f.message for f in result.findings if "description" in f.message]
            self.assertEqual(expected, messages)

    def test_frontmatter_yaml_would_reject_is_an_error(self):
        head = "---\nname: x\n"
        for broken in ("description: Create pages: a clean overview", "description: first line\n  second: line",
                       "metadata:\n  short: a: b", "description:\tb", "argument-hint: [a] b: c",
                       "description: `tool` verbs", "description: cut #here", "description: ends with:",
                       "description: 'it's'", 'description: "a" b"', "argument-hint: [a]]", "description: >b",
                       "metadata:\n  b: |\n    t\n  c: d: e", "metadata:\n  a: 1\n b: 2", "metadata:\n  a: 1\n    b: 2",
                       "description: #foo", "description: a\t#b", "x: [@]", "x: b\t",
                       "description: |\n  ok\n bad: a: b", "description: |\n   odd\n  b"):
            self.assertTrue(manifests.frontmatter_problems(f"{head}{broken}\n---\n"), broken)
        for safe in ('description: "Create pages: a clean overview"', "description: >\n  Folded: text", "description: >-\n  x",
                     "metadata:\n  short: ok", "argument-hint: [a, b]", "description: https://x.test/a#b",
                     "disable-model-invocation: true", "description: 'it''s'", 'description: "a \\"b\\""', "description: |\n  x\n\n  y"):
            self.assertEqual([], manifests.frontmatter_problems(f"{head}{safe}\n---\n"), safe)
        self.put("skills/x/SKILL.md", head + "description: a: b\n---\n")
        result = manifests.Result()
        manifests.check_skill(self.root / "skills/x", result)
        self.assertTrue(any("must stay a plain form" in f.message for f in result.findings))

    def comments(self, name, text):
        return [line for _, line in no_comments.scan(Path(name), text)]

    def test_no_comments_ignores_hash_as_data(self):
        cases = {
            "a.py": '#!/usr/bin/env python3\nx = "# not a comment"\nurl = "https://x.test/#frag"\n',
            "a.sh": '#!/usr/bin/env bash\necho "$#" ${#items[@]} \'#x\' a#b\ncat <<EOF\n# heredoc text\nEOF\n',
            "a.md": "# Heading\n\n[link](#anchor) `<!-- code -->`\n\n```bash\necho '#1'\n```\n",
            "a.html": '<style>a { color: #fff; }</style><script>var u = "http://x"; var r = /\\/\\//;</script>\n',
            "a.yaml": 'color: "#fff"\nkey: a#b\n',
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                self.assertEqual([], self.comments(name, text))

    def test_no_comments_flags_every_comment_form(self):
        cases = {
            "a.py": ('x = 1  # note\ndef f():\n    """Doc."""\n    return 1\n', 2),
            "a.sh": ("#!/bin/sh\n# note\necho hi # tail\n", 2),
            "a.md": ("<!-- note -->\n```bash\nls  # tail\n```\n```js\n// note\n```\n", 3),
            "a.html": ("<!-- x --><style>/* c */</style><script>a(); // c\n/* d */</script>\n", 4),
            "a.yaml": ("# note\nkey: 1  # tail\n", 2),
            ".gitignore": ("# note\n*.log\n", 1),
        }
        for name, (text, count) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(count, len(self.comments(name, text)))


if __name__ == "__main__":
    unittest.main()
