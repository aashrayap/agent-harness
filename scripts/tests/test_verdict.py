from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/engineering/verify/scripts/verdict.py"
LAYERS = ["--layer", "checks=PASS:check passed", "--layer", "contract=PASS",
          "--layer", "live=SKIP:no surface", "--layer", "review=PASS:quick review, no findings"]


def load_module():
    spec = importlib.util.spec_from_file_location("verdict", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN = re.compile(r"""(?:^|;|&&|\|\||\||\(|\bthen|\bdo|\bif|\bexec|!)[ \t]*(?:\w+=(?:"[^"]*"|\S*)[ \t]+)*"""
                 r"""(?:bash|sh|zsh|source|\.|python3?|uv\s+run\s+python|run_python_audit|"\$\{python\[@\]\}")"""
                 r"""((?:\s+-[A-Za-z]+)*)\s+("[^"]*"|'[^']*'|[^\s;&|)]+)""", re.M)
WORD = re.compile(r"""["']?([^\s"';&|()<>`]*(?:/|\.sh\b|\.py\b)[^\s"';&|()<>`]*)""")
ASSIGN = re.compile(r"""^\s*(?:local\s+|export\s+|readonly\s+)?([A-Za-z_]\w*)=("[^"]*"|'[^']*'|[^\s;]*)""", re.M)
OUTSIDE = {"-", "$script", "$hook"}


def expand(value: str, names: dict[str, str]) -> str:
    def one(match: re.Match) -> str:
        return names.get(match.group(1) or match.group(2), "*")
    for _ in range(5):
        value = re.sub(r"\$\{(\w+)(?:[:?=+-][^}]*)?\}|\$(\w+)", one, value)
    return value.strip("\"'")


def resolve(target: str, here: Path) -> list[Path]:
    if not target or target.rsplit("/", 1)[-1] in ("", "*", ".", ".."):
        return []
    if target.startswith("/"):
        if not target.startswith(f"{ROOT}/"):
            return []
        return [p for p in ROOT.glob(target.removeprefix(f"{ROOT}/")) if p.is_file()]
    return [p for base in (here, ROOT) for p in base.glob(target) if p.is_file()]


def runnable(path: Path) -> bool:
    return path.suffix in (".sh", ".py") or os.access(path, os.X_OK)


def python_refs(path: Path) -> list[Path]:
    tree = ast.parse(path.read_text())
    dotted: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dotted += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            dotted += [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
    found = [p for name in dotted for base in (path.parent, ROOT)
             for p in (base / f"{name.replace('.', '/')}.py", base / name.replace(".", "/") / "__init__.py")
             if p.is_file()]
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"\.(sh|py)$", node.value):
            found += [p for p in resolve(node.value, path.parent) if runnable(p)]
    return found


def setup_runs() -> set[Path]:
    seen: set[Path] = set()
    queue = [ROOT / "setup.sh"]
    while queue:
        path = queue.pop().resolve()
        if path in seen or not path.is_file() or path.is_relative_to((ROOT / "state").resolve()):
            continue
        seen.add(path)
        if path.suffix == ".py":
            queue += python_refs(path)
            continue
        text = path.read_text()
        names = {"DOT_AGENT_SOURCE_ROOT": str(ROOT), "probe_root": str(ROOT)}
        assigned: dict[str, str] = {}
        for name, value in ASSIGN.findall(text):
            value = value.strip("\"'")
            assigned[name] = value if assigned.get(name, value) == value else "*"
        names = {**assigned, **names}
        for flags, target in RUN.findall(text):
            if "-c" in flags.split():
                continue
            if "-m" in flags.split():
                target = target.replace(".", "/") + ".py"
            if not resolve(expand(target, names), path.parent) and target.strip("\"'") not in OUTSIDE:
                raise AssertionError(f"{path.relative_to(ROOT)} runs {target}, which the test cannot resolve")
            queue += resolve(expand(target, names), path.parent)
        for word in WORD.findall(text):
            queue += [p for p in resolve(expand(word, names), path.parent) if runnable(p)]
    return {p for p in seen if p.is_relative_to(ROOT)}

class VerdictTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.state = self.tmp / "state"
        self.repo.mkdir()
        self.env = {**os.environ, "DOT_AGENT_STATE_HOME": str(self.state),
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        self.git("init", "-q")
        self.commit("one")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, text: str) -> str:
        (self.repo / "file.txt").write_text(text)
        self.git("add", "file.txt")
        self.git("commit", "-qm", text)
        return self.git("rev-parse", "HEAD")

    def run_verdict(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True)

    def test_record_pins_the_verdict_to_head(self) -> None:
        sha = self.git("rev-parse", "HEAD")
        result = self.run_verdict("record", "--claim", "c", *LAYERS, "--limit", "no UI")
        self.assertEqual(0, result.returncode, result.stderr)
        entry = json.loads((self.state / "verdicts" / f"{sha}.json").read_text())
        self.assertEqual(sha, entry["sha"])
        self.assertEqual("PASS", entry["verdict"])
        self.assertEqual("PASS", entry["layers"]["review"]["status"])
        self.assertEqual("quick review, no findings", entry["layers"]["review"]["evidence"])
        self.assertEqual([], entry["findings"])
        self.assertEqual(["no UI"], entry["limits"])
        self.assertEqual(0, self.run_verdict("check", "--claim", "c").returncode)

    def test_check_fails_once_head_moves(self) -> None:
        self.run_verdict("record", "--claim", "c", *LAYERS)
        self.commit("two")
        result = self.run_verdict("check", "--claim", "c")
        self.assertEqual(1, result.returncode)
        self.assertIn("no verdict recorded for HEAD", result.stderr)

    def test_check_reports_a_blocked_verdict_with_its_open_findings(self) -> None:
        finding = ["--finding", "BLOCKING|race|a.py:4|two writers race|open"]
        self.run_verdict("record", "--claim", "c", *LAYERS, *finding)
        result = self.run_verdict("check", "--claim", "c")
        self.assertEqual(1, result.returncode)
        self.assertIn("verdict: BLOCKED for", result.stdout)
        self.assertIn("open finding: BLOCKING a.py:4 two writers race", result.stdout)

    def test_check_fails_on_a_dirty_tree_or_a_failed_layer(self) -> None:
        failing = [*LAYERS[:-1], "review=FAIL:refuted"]
        self.assertEqual(1, self.run_verdict("record", "--claim", "c", *failing).returncode)
        self.assertEqual(1, self.run_verdict("check", "--claim", "c").returncode)
        (self.repo / "file.txt").write_text("edited")
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_untracked_files_block_record_and_check(self) -> None:
        self.assertEqual(0, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)
        (self.repo / "helper.py").write_text("x = 1")
        self.assertEqual(1, self.run_verdict("check", "--claim", "c").returncode)
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_record_requires_every_layer(self) -> None:
        result = self.run_verdict("record", "--claim", "c", *LAYERS[:4])
        self.assertEqual(2, result.returncode)
        self.assertIn("missing layers: live, review", result.stderr)
        self.assertFalse((self.state / "verdicts").exists())

    def record_pass(self) -> str:
        self.assertEqual(0, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)
        return self.git("rev-parse", "HEAD")

    def test_check_refuses_a_different_claim(self) -> None:
        self.record_pass()
        result = self.run_verdict("check", "--claim", "other")
        self.assertEqual(1, result.returncode)
        self.assertIn("does not match", result.stderr)

    def test_untracked_files_count_even_when_config_hides_them(self) -> None:
        self.record_pass()
        self.git("config", "status.showUntrackedFiles", "no")
        (self.repo / "helper.py").write_text("x = 1")
        self.assertEqual(1, self.run_verdict("check", "--claim", "c").returncode)
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_assume_unchanged_edits_block_record_and_check(self) -> None:
        self.record_pass()
        self.git("update-index", "--assume-unchanged", "file.txt")
        (self.repo / "file.txt").write_text("hidden edit")
        self.assertEqual(1, self.run_verdict("check", "--claim", "c").returncode)
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_skip_worktree_edits_block_record_and_check(self) -> None:
        self.record_pass()
        self.git("update-index", "--skip-worktree", "file.txt")
        (self.repo / "file.txt").write_text("hidden edit")
        self.assertEqual(1, self.run_verdict("check", "--claim", "c").returncode)
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_ignored_submodule_changes_block_record(self) -> None:
        lib = self.tmp / "lib"
        lib.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=lib, env=self.env, check=True)
        (lib / "lib.py").write_text("ok")
        subprocess.run(["git", "add", "lib.py"], cwd=lib, env=self.env, check=True)
        subprocess.run(["git", "commit", "-qm", "lib"], cwd=lib, env=self.env, check=True)
        self.git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "lib")
        self.git("commit", "-qm", "add lib")
        self.git("config", "diff.ignoreSubmodules", "all")
        (self.repo / "lib" / "lib.py").write_text("hidden edit")
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_mode_change_hidden_by_filemode_blocks_record(self) -> None:
        self.git("config", "core.fileMode", "false")
        (self.repo / "file.txt").chmod(0o755)
        self.assertEqual(2, self.run_verdict("record", "--claim", "c", *LAYERS).returncode)

    def test_limits_must_be_a_list(self) -> None:
        self.record_pass()
        path = next((self.state / "verdicts").glob("*.json"))
        entry = json.loads(path.read_text())
        entry["limits"] = "ab"
        path.write_text(json.dumps(entry))
        self.assertEqual(2, self.run_verdict("check", "--claim", "c").returncode)

    def test_pass_needs_a_passing_deterministic_layer(self) -> None:
        layers = ["--layer", "checks=SKIP", "--layer", "contract=SKIP",
                  "--layer", "live=PASS:ran it", "--layer", "review=PASS:read it"]
        self.assertEqual(1, self.run_verdict("record", "--claim", "c", *layers).returncode)
        sha = self.git("rev-parse", "HEAD")
        entry = json.loads((self.state / "verdicts" / f"{sha}.json").read_text())
        self.assertEqual("BLOCKED", entry["verdict"])

    def test_check_rejects_a_hand_edited_pass(self) -> None:
        sha = self.record_pass()
        path = self.state / "verdicts" / f"{sha}.json"
        entry = json.loads(path.read_text())
        entry["layers"]["checks"]["status"] = "SKIP"
        entry["layers"]["contract"]["status"] = "SKIP"
        path.write_text(json.dumps(entry))
        result = self.run_verdict("check", "--claim", "c")
        self.assertEqual(2, result.returncode)
        self.assertIn("malformed verdict", result.stderr)

    def test_check_rejects_a_layer_without_status(self) -> None:
        sha = self.record_pass()
        path = self.state / "verdicts" / f"{sha}.json"
        entry = json.loads(path.read_text())
        del entry["layers"]["live"]["status"]
        path.write_text(json.dumps(entry))
        result = self.run_verdict("check", "--claim", "c")
        self.assertEqual(2, result.returncode)
        self.assertIn("every layer needs a status", result.stderr)

    def test_check_exits_cleanly_on_corrupt_json(self) -> None:
        sha = self.record_pass()
        (self.state / "verdicts" / f"{sha}.json").write_text("{not json")
        result = self.run_verdict("check", "--claim", "c")
        self.assertEqual(2, result.returncode)
        self.assertIn("unreadable verdict", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_record_rejects_empty_live_or_review_evidence(self) -> None:
        for layers in ([*LAYERS[:4], "--layer", "live=SKIP", *LAYERS[6:]],
                       [*LAYERS[:6], "--layer", "review=PASS:"]):
            result = self.run_verdict("record", "--claim", "c", *layers)
            self.assertEqual(2, result.returncode)
            self.assertIn("need evidence", result.stderr)
        self.assertFalse((self.state / "verdicts").exists())

    def test_record_rejects_evidence_carried_from_a_commit_that_differs(self) -> None:
        old = self.git("rev-parse", "HEAD")
        self.commit("two")
        carried = [*LAYERS[:6], "--layer", f"review=PASS:carried from {old[:10]}"]
        result = self.run_verdict("record", "--claim", "c", *carried)
        self.assertEqual(2, result.returncode)
        self.assertIn("rerun review on HEAD", result.stderr)
        unknown = [*LAYERS[:6], "--layer", "review=PASS:carried from deadbeefdead"]
        self.assertIn("not a commit", self.run_verdict("record", "--claim", "c", *unknown).stderr)
        for loose in (f"Carried from {old[:8]}.", "carried from the previous commit"):
            result = self.run_verdict("record", "--claim", "c", *LAYERS[:6], "--layer", f"review=PASS:{loose}")
            self.assertEqual(2, result.returncode, loose)

    def test_record_accepts_evidence_carried_from_an_identical_tree(self) -> None:
        old = self.git("rev-parse", "HEAD")
        self.git("commit", "-q", "--allow-empty", "-m", "rebased")
        carried = [*LAYERS[:6], "--layer", f"review=PASS:carried from {old}"]
        self.assertEqual(0, self.run_verdict("record", "--claim", "c", *carried).returncode)

    def test_pass_needs_a_passing_review(self) -> None:
        skipped = [*LAYERS[:6], "--layer", "review=SKIP:low risk"]
        self.assertEqual(1, self.run_verdict("record", "--claim", "c", *skipped).returncode)
        sha = self.git("rev-parse", "HEAD")
        self.assertEqual("BLOCKED", json.loads((self.state / "verdicts" / f"{sha}.json").read_text())["verdict"])

    def test_findings_need_file_line_and_dismissals_need_a_reason(self) -> None:
        for bad in ("BLOCKING|unpinned-merge|merge-gate.py|no line|fixed",
                    "NOTE|naming|a.py:3|long name|dismissed",
                    "NOTE|naming|a.py:3|long name|dismissed|matches the caller's name",
                    "NOTE|naming|a.py:3|long name|fixed||sloppy",
                    "MAJOR|naming|a.py:3|long name|fixed",
                    "NOTE|Bad Kind|a.py:3|long name|fixed",
                    "NOTE|naming|a.py:3|long name"):
            result = self.run_verdict("record", "--claim", "c", *LAYERS, "--finding", bad)
            self.assertEqual(2, result.returncode, bad)
        self.assertFalse((self.state / "verdicts").exists())
        good = ["--finding", "BLOCKING|unpinned-merge|hooks/gate.py:40|merge not pinned|fixed",
                "--finding", "NOTE|naming|a.py:3|long name|dismissed|matches the caller's name|unmapped case"]
        self.assertEqual(0, self.run_verdict("record", "--claim", "c", *LAYERS, *good).returncode)
        sha = self.git("rev-parse", "HEAD")
        entry = json.loads((self.state / "verdicts" / f"{sha}.json").read_text())
        self.assertEqual(["fixed", "dismissed"], [f["outcome"] for f in entry["findings"]])
        self.assertEqual("matches the caller's name", entry["findings"][1]["reason"])
        self.assertEqual("unmapped case", entry["findings"][1]["cause"])

    def test_an_open_blocking_finding_blocks_the_verdict_and_the_gate(self) -> None:
        finding = ["--finding", "BLOCKING|lost-data|store.py:9|overwrites the owner's file|open"]
        result = self.run_verdict("record", "--claim", "c", *LAYERS, *finding)
        self.assertEqual(1, result.returncode)
        self.assertIn("open BLOCKING: store.py:9", result.stdout)
        sha = self.git("rev-parse", "HEAD")
        self.assertIn("1 open BLOCKING finding", self.run_verdict("gate", sha).stderr)
        note = ["--finding", "NOTE|naming|a.py:3|long name|open"]
        self.assertEqual(0, self.run_verdict("record", "--claim", "c", *LAYERS, *note).returncode)

    def test_gate_needs_pass_and_owner_approval_for_high_risk(self) -> None:
        sha = self.record_pass()
        self.assertEqual(0, self.run_verdict("gate", sha).returncode)
        verdict = load_module()
        os.environ["DOT_AGENT_STATE_HOME"] = str(self.state)
        self.addCleanup(os.environ.pop, "DOT_AGENT_STATE_HOME", None)
        self.assertIn("high risk (hooks", verdict.gate(sha, ["hooks, CI or the merge gate"]))
        self.assertEqual(1, self.run_verdict("approve", "f" * 40, "--words", "x").returncode)
        self.assertEqual(0, self.run_verdict("approve", sha, "--words", "The owner: yes, merge it").returncode)
        self.assertEqual("", verdict.gate(sha, ["hooks, CI or the merge gate"]))
        self.commit("two")
        blocked = ["--layer", "checks=SKIP", "--layer", "contract=BLOCKED:no runner",
                   "--layer", "live=SKIP:none", "--layer", "review=PASS:quick"]
        self.run_verdict("record", "--claim", "c", *blocked)
        head = self.git("rev-parse", "HEAD")
        self.assertIn("merging needs PASS", self.run_verdict("gate", head).stderr)
        self.assertEqual(1, self.run_verdict("approve", head, "--words", "The owner: yes").returncode)

    def test_every_script_scripts_check_runs_is_high_risk(self) -> None:
        verdict = load_module()
        check = (ROOT / "scripts/check").read_text()
        scripts = re.findall(r"^\s*run (?:\"\$py\"|bash) (\S+\.(?:py|sh))", check, re.M)
        self.assertGreater(len(scripts), 12)
        for path in scripts:
            self.assertTrue(verdict.risk([("changed", path)]), path)

    def test_a_dismissed_blocking_finding_makes_the_merge_high_risk(self) -> None:
        dismissed = ["--finding", "BLOCKING|race|a.py:4|two writers race|dismissed|single writer by design|agent-wrong"]
        self.assertEqual(0, self.run_verdict("record", "--claim", "c", *LAYERS, *dismissed).returncode)
        sha = self.git("rev-parse", "HEAD")
        self.assertIn("a BLOCKING finding was dismissed", self.run_verdict("gate", sha).stderr)

    def test_risk_is_high_for_each_listed_path_and_a_dismissed_blocking_finding(self) -> None:
        verdict = load_module()
        high = ["setup.sh", "template/apply.sh", "x/install.sh", "scripts/retire-managed-runtime.py",
                "claude/hooks/merge-gate.py", ".githooks/pre-commit", ".github/workflows/ci.yml",
                "claude/hooks.json", "skills/engineering/verify/scripts/verdict.py", "AGENTS.md",
                "template/CLAUDE.md", "CONSTRAINTS.tsv", "claude/model-lock.json", "codex/config.toml",
                "scripts/private-boundary.py", ".env", "auth/token_store.py", "billing.py",
                "scripts/deploy.sh", "mail/send.py", "scripts/check", "template/scripts/check",
                "scripts/toml_edit.py", "scripts/settings-drift-audit.py", "scripts/toml_compat.py",
                "profiles/x/ensure.sh", ".gitignore", ".claude/settings.json", "scripts/no-comments.allow",
                "scripts/cloud-setup.sh"]
        for path in high:
            self.assertTrue(verdict.risk([("changed", path)]), path)
        low = ["web/.gitignore", "src/conform.py", "app/handoff.py", "src/foo.allow", "README.md", "skills/engineering/verify/SKILL.md", "scripts/pr-rows.py", "RELEASES.md",
               "VERSION", "scripts/tests/test_pr_rows.py", "docs/notes.md"]
        for path in low:
            self.assertEqual([], verdict.risk([("changed", path)]), path)
        self.assertEqual(["deletes docs/old.md"], verdict.risk([("removed", "docs/old.md")]))
        dismissed = [{"severity": "BLOCKING", "outcome": "dismissed"}]
        self.assertEqual(["a BLOCKING finding was dismissed"], verdict.risk([], dismissed))
        self.assertEqual([], verdict.risk([], [{"severity": "NOTE", "outcome": "dismissed"}]))

    def test_every_file_setup_runs_is_high_risk(self) -> None:
        verdict = load_module()
        ran = {str(p.relative_to(ROOT)) for p in setup_runs()}
        self.assertTrue({"setup.sh", "scripts/toml_edit.py", "scripts/toml_compat.py"} <= ran, sorted(ran))
        for path in sorted(ran):
            self.assertIn("setup or install", verdict.risk([("changed", path)]), path)
        self.assertIn("setup or install", verdict.risk([("changed", "profiles/personal/provided-skills")]))

    def test_setup_runs_follows_every_invocation_form(self) -> None:
        global ROOT
        root = self.tmp.resolve() / "fake"
        for name in ("a.sh", "b.sh", "c.py", "d.sh", "m.py", "helper.py", "pkg/__init__.py", "pkg/mod.py",
                     "sub.sh", "lib.sh"):
            (root / "scripts" / name).parent.mkdir(parents=True, exist_ok=True)
            (root / "scripts" / name).write_text("")
        (root / "scripts/c.py").write_text("import os, helper\nfrom pkg import mod\n")
        (root / "scripts/m.py").write_text("import subprocess\nsubprocess.run(['bash', 'sub.sh'])\n")
        (root / "setup.sh").write_text(
            'D=$DOT_AGENT_SOURCE_ROOT/scripts\n"$DOT_AGENT_SOURCE_ROOT/scripts/a.sh"\nbash $D/b.sh\n'
            'python3 "${DOT_AGENT_SOURCE_ROOT:?}/scripts/c.py"\ncd "$DOT_AGENT_SOURCE_ROOT" && bash scripts/d.sh\n'
            'python3 -m scripts.m\n. scripts/lib.sh\npython3 - "$x" <<\'PY\'\nPY\n')
        saved, ROOT = ROOT, root
        try:
            ran = {str(p.relative_to(root)) for p in setup_runs()}
            self.assertEqual({"setup.sh", *(f"scripts/{n}" for n in ("a.sh", "b.sh", "c.py", "d.sh", "m.py",
                              "helper.py", "pkg/__init__.py", "pkg/mod.py", "sub.sh", "lib.sh"))}, ran)
            (root / "setup.sh").write_text('bash "$UNKNOWN_DIR/run.sh"\n')
            with self.assertRaises(AssertionError):
                setup_runs()
        finally:
            ROOT = saved

    def test_the_always_pause_list_names_every_high_risk_category(self) -> None:
        labels = [label for label, _ in load_module().HIGH_RISK]
        agents = " ".join((ROOT / "AGENTS.md").read_text().split())
        start = agents.index("- merging a high-risk PR")
        bullet = agents[start:agents.index(" - ", start + 1)]
        row = next(line for line in (ROOT / "CONSTRAINTS.tsv").read_text().splitlines()
                   if line.startswith("merge-risk\t"))
        for text in (bullet, row):
            self.assertIn("HIGH_RISK", text)
            self.assertIn("delet", text)
            self.assertIn("dismissed BLOCKING" if text is row else "BLOCKING finding was dismissed", text)
            for label in labels:
                self.assertIn(label, text, label)

    def test_risk_command_reads_the_branch_diff(self) -> None:
        base = self.git("rev-parse", "HEAD")
        (self.repo / "AGENTS.md").write_text("x")
        self.git("add", "AGENTS.md")
        self.git("rm", "-q", "file.txt")
        self.git("commit", "-qm", "agents")
        result = self.run_verdict("risk", "--base", base)
        self.assertEqual("Risk: high (AGENTS.md or CLAUDE.md, deletes file.txt)", result.stdout.strip())

    def test_kinds_names_a_kind_seen_twice(self) -> None:
        self.run_verdict("record", "--claim", "c", *LAYERS,
                         "--finding", "NOTE|stale-doc|a.md:1|stale line|fixed")
        self.commit("two")
        self.run_verdict("record", "--claim", "c", *LAYERS,
                         "--finding", "NOTE|stale-doc|b.md:2|stale line|fixed",
                         "--finding", "NOTE|naming|c.py:3|long|fixed")
        result = self.run_verdict("kinds")
        self.assertIn("stale-doc: seen 2 times", result.stdout)
        self.assertIn("propose a lint rule or CONSTRAINTS.tsv row", result.stdout)
        self.assertNotIn("naming", result.stdout)

    def test_a_blocked_pr_body_must_list_its_open_blocking_findings(self) -> None:
        verdict = load_module()
        layers = {name: {"status": "PASS", "evidence": "x"} for name in ("checks", "contract", "live", "review")}
        finding = {"severity": "BLOCKING", "kind": "risk-coverage-gap", "where": "setup.sh:398",
                   "summary": "setup.sh runs profiles/work/ensure.sh but HIGH_RISK does not match it",
                   "outcome": "open", "reason": ""}
        entry = {"verdict": "BLOCKED", "layers": layers, "findings": [finding]}
        pr_314 = ("## Verification\n- `scripts/check --tests`: green.\n- Independent review found 2 BLOCKING "
                  "(stale merge wording; scripts setup.sh runs classified low risk). All fixed.\n\n"
                  "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n")
        self.assertIn("omits the open BLOCKING finding setup.sh:398", verdict.body_problems(entry, pr_314)[0])
        listed = pr_314.replace("All fixed.", "Open BLOCKING: setup.sh:398 ensure.sh is low risk.")
        self.assertEqual([], verdict.body_problems(entry, listed))
        self.assertIn("needs a ## Verification", verdict.body_problems(entry, "## Summary\nx\n")[0])
        live = dict(layers, live={"status": "BLOCKED", "evidence": "no Mac"})
        blocked = {"verdict": "BLOCKED", "layers": live, "findings": []}
        self.assertIn("blocked layer (live)", verdict.body_problems(blocked, "## Verification\n- ok\n")[0])
        self.assertEqual([], verdict.body_problems(blocked, "## Verification\n- Live blocked: no Mac\n"))
        self.assertTrue(verdict.body_problems(blocked, "## Verification\n- all checks green; delivered live\n"))
        self.assertEqual([], verdict.body_problems({"verdict": "PASS", "layers": layers}, ""))

    def test_check_with_a_body_exits_zero_when_a_blocked_pr_may_open(self) -> None:
        finding = ["--finding", "BLOCKING|lost-data|store.py:9|overwrites the owner's file|open"]
        self.run_verdict("record", "--claim", "c", *LAYERS, *finding)
        body = self.tmp / "body.md"
        body.write_text("## Verification\n- green\n")
        self.assertEqual(1, self.run_verdict("check", "--claim", "c", "--body", str(body)).returncode)
        body.write_text("## Verification\n- open BLOCKING store.py:9 overwrites the owner's file\n")
        self.assertEqual(0, self.run_verdict("check", "--claim", "c", "--body", str(body)).returncode)

    def test_kinds_by_cause_counts_each_cause(self) -> None:
        self.run_verdict("record", "--claim", "c", *LAYERS,
                         "--finding", "NOTE|stale-doc|a.md:1|stale line|fixed||missing context",
                         "--finding", "NOTE|stale-doc|b.md:1|stale line|open||missing-context",
                         "--finding", "NOTE|naming|c.py:3|long|fixed")
        result = self.run_verdict("kinds", "--by-cause")
        self.assertIn("missing context: 2 (stale-doc 2)", result.stdout)
        self.assertIn("unknown: 1 (naming 1)", result.stdout)
        self.assertIn("stale-doc: seen 2 times, cause missing context", self.run_verdict("kinds").stdout)

    def test_outside_a_git_repo_exits_cleanly(self) -> None:
        outside = self.tmp / "outside"
        outside.mkdir()
        for args in (["check", "--claim", "c"], ["record", "--claim", "c", *LAYERS]):
            result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=outside,
                                    env={**self.env, "GIT_CEILING_DIRECTORIES": str(self.tmp)},
                                    capture_output=True, text=True)
            self.assertEqual(2, result.returncode, result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
