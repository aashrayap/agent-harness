from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from toml_edit import strict_loads

CLOUD_RULES = "**/.claude/rules/dot-agent.md"


class ManagedRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.make_home("home")

    def make_home(self, name):
        self.home = Path(self.temporary.name).resolve() / name
        self.source = self.home / ".dot-agent"
        shutil.copytree(ROOT, self.source, ignore=shutil.ignore_patterns(
            ".git", "state", "__pycache__", "*.pyc", "*.pyo"))
        subprocess.run(["git", "init", "--quiet", str(self.source)], check=True)
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.home)
        for key in ("DOT_AGENT_HOME", "DOT_AGENT_STATE_HOME", "CODEX_HOME", "CLAUDE_HOME"):
            self.env.pop(key, None)

    def setup(self, *args, success=True):
        result = subprocess.run(["bash", str(self.source / "setup.sh"), *args],
                                env=self.env, cwd=self.source, text=True,
                                capture_output=True, timeout=120)
        if success:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result

    def retire(self, *args):
        result = subprocess.run([
            sys.executable, str(self.source / "scripts/retire-managed-runtime.py"),
            "--source", str(self.source), "--home", str(self.home),
            "--state", str(self.source / "state"), *args,
        ], cwd=self.source, env=self.env, text=True, capture_output=True,
            timeout=30, umask=0o022)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result

    def put(self, relative, text):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def snapshot(self):
        return {str(p.relative_to(self.home)):
                ("link", os.readlink(p)) if p.is_symlink() else
                ("file", hashlib.sha256(p.read_bytes()).hexdigest()) if p.is_file()
                else ("dir", "")
                for p in self.home.rglob("*") if ".git" not in p.parts}

    def seed_old_claude(self):
        manifest = json.loads((self.source / "scripts/fixtures/retired-runtime.json").read_text())
        settings = manifest["claude_settings"]
        settings["effortLevel"] = "max"
        settings["custom"] = {"keep": True}
        settings["enabledPlugins"]["my-plugin"] = True
        settings["hooks"]["SessionStart"][0]["hooks"].append(
            {"type": "command", "command": "echo custom"})
        settings["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": "echo stop"}]}]
        self.put(".dot-agent/state/generated/AGENTS.md", "previous effective instructions\n")
        self.put(".claude/settings.json", json.dumps(settings))
        self.put(".claude/projects/keep/conversation.jsonl", "unique conversation\n")
        self.put(".claude/skills/custom/SKILL.md", "owner's custom skill\n")
        self.put(".claude/skills/grill-me/private-note.txt", "keep custom companion\n")
        for relative, target in {
            ".claude/CLAUDE.md": self.source / "state/generated/AGENTS.md",
            ".claude/statusline-enhanced.sh": self.source / "claude/statusline-enhanced.sh",
            ".claude/skills/grill-me/SKILL.md": self.source / "skills/engineering/grill-me/SKILL.md",
            ".claude/skills/grill-me/references": self.source / "skills/engineering/grill-me/references",
        }.items():
            path = self.home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)

    def test_exact_retirement_preserves_mixed_custom_settings_history_and_links(self):
        self.seed_old_claude()
        self.put(".codex/config.toml", 'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"\ncustom = "keep"\n')
        hooks = {"hooks": {"SessionStart": [{"matcher": "startup|resume", "hooks": [
            {"type": "command", "command": "cat ~/.dot-agent/claude/caveman-boot.txt"},
            {"type": "command", "command": "echo custom"}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "~/.dot-agent/codex/title-hook.sh"}]}]}}
        self.put(".codex/hooks.json", json.dumps(hooks))
        self.put(".codex/skills/user-plugin/SKILL.md", "keep unrelated skill\n")
        self.setup()
        settings = json.loads((self.home / ".claude/settings.json").read_text())
        self.assertEqual("max", settings["effortLevel"])
        self.assertEqual({"my-plugin": True}, settings["enabledPlugins"])
        self.assertEqual({"keep": True}, settings["custom"])
        self.assertEqual([{"type": "command", "command": "echo custom"}],
                         settings["hooks"]["SessionStart"][0]["hooks"])
        self.assertIn("Stop", settings["hooks"])
        self.assertFalse((self.home / ".claude/CLAUDE.md").is_symlink())
        self.assertFalse((self.home / ".claude/skills/grill-me/SKILL.md").is_symlink())
        self.assertEqual("keep custom companion\n",
                         (self.home / ".claude/skills/grill-me/private-note.txt").read_text())
        self.assertEqual("unique conversation\n",
                         (self.home / ".claude/projects/keep/conversation.jsonl").read_text())
        self.assertTrue((self.home / ".codex/skills/user-plugin/SKILL.md").is_file())
        config = (self.home / ".codex/config.toml").read_text()
        self.assertIn('model = "gpt-6.1-sol"', config)
        self.assertIn('model_reasoning_effort = "high"', config)
        self.assertIn('custom = "keep"', config)
        self.assertEqual({"hooks": {"SessionStart": [{"matcher": "startup|resume",
            "hooks": [{"type": "command", "command": "echo custom"}]}]}},
            json.loads((self.home / ".codex/hooks.json").read_text()))
        receipts = list((self.source / "state/backups/retirement").glob("*/receipt.json"))
        self.assertGreaterEqual(len(receipts), 1)
        saved_instructions = list((self.source / "state/backups/retirement").glob(
            "*/.claude/CLAUDE.md.resolved"))
        self.assertEqual(1, len(saved_instructions))
        self.assertEqual("previous effective instructions\n", saved_instructions[0].read_text())
        self.assertTrue(any(p.name == "conversation.jsonl" for p in (self.home / ".claude").rglob("*")))
        before = self.snapshot()
        self.setup()
        self.assertEqual(before, self.snapshot(), "Repeat install must leave bytes and recovery inventory stable")

    def test_a_retired_skill_now_linked_from_its_own_repo_is_left_to_that_repo(self):
        self.setup("--runtime", "claude")
        registry = self.source / "state/managed-claude-skills.json"
        entries = json.loads(registry.read_text())
        entries["moved-out"] = {"SKILL.md": "0" * 64}
        registry.write_text(json.dumps(entries))
        owner = self.put("moved-out/SKILL.md", "---\nname: moved-out\ndescription: d\n---\n").parent
        link = self.home / ".claude/skills/moved-out"
        link.symlink_to(owner)
        self.setup("--runtime", "claude")
        self.assertEqual(owner, link.resolve())
        self.assertNotIn("moved-out", json.loads(registry.read_text()))

    def test_check_mode_detects_residue_without_mutation(self):
        self.setup()
        self.assertFalse((self.home / ".claude").exists(), "Codex scope must not create ~/.claude")
        self.seed_old_claude()
        before = self.snapshot()
        result = self.setup("--check-instructions", success=False)
        self.assertIn("STALE managed target", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_unknown_runtime_is_rejected_before_mutation(self):
        before = self.snapshot()
        self.setup("--runtime", "gemini", success=False)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.home / ".claude").exists())

    def test_claude_runtime_fresh_install_for_both_profiles(self):
        for profile in ("work", "personal"):
            with self.subTest(profile=profile):
                self.make_home(f"home-{profile}")
                self.put(".dot-agent/state/machine-profile", f"{profile}\n")
                self.setup("--runtime", "claude")
                self.assertFalse((self.home / ".codex").exists(), "Claude scope must not create ~/.codex")
                self.assertEqual("claude\n", (self.source / "state/runtime-scope").read_text())
                self.assertEqual(f"@{self.source / 'state/generated/AGENTS.md'}",
                                 (self.home / ".claude/CLAUDE.md").read_text().splitlines()[0])
                self.assertEqual((self.source / "skills/engineering/grill-me/SKILL.md").read_bytes(),
                                 (self.home / ".claude/skills/grill-me/SKILL.md").read_bytes())
                self.assertEqual(profile == "personal",
                                 (self.home / ".claude/skills/unslop").exists())
                self.assertTrue((self.source / "state/managed-claude-skills.json").is_file())
                self.assertFalse((self.source / "state/managed-codex-skills.json").exists())
                before = self.snapshot()
                self.setup()
                self.setup("--check-instructions")
                self.assertEqual(before, self.snapshot(), "A bare rerun must reuse the Claude scope")

    def test_bytecode_never_blocks_a_rerun_and_setup_writes_none(self):
        lines = (self.source / "setup.sh").read_text().splitlines()
        export = lines.index("export PYTHONDONTWRITEBYTECODE=1")
        self.assertLess(export, next(i for i, line in enumerate(lines) if "python3" in line))
        self.env.pop("PYTHONDONTWRITEBYTECODE", None)
        self.setup("--runtime", "claude")
        self.assertEqual([], list(self.source.rglob("__pycache__")))
        cache = self.home / ".claude/skills/verify/scripts/__pycache__"
        cache.mkdir(parents=True)
        (cache / "verdict.cpython-313.pyc").write_bytes(b"compiled")
        self.setup()
        self.assertTrue((self.home / ".claude/skills/verify/SKILL.md").is_file())

    def test_switch_from_all_to_claude_retires_only_managed_codex_copies(self):
        config = self.put(".codex/config.toml", 'custom = "keep"\n')
        self.put(".codex/skills/custom/SKILL.md", "owner's codex skill\n")
        self.put(".codex/sessions/keep.jsonl", "codex history\n")
        self.setup("--runtime", "all")
        edited = self.put(".codex/skills/show-me/SKILL.md", "owner edit\n")
        config_before = config.read_bytes()
        claude_before = {path: data for path, data in self.snapshot().items()
                         if path.startswith(".claude/")}
        self.setup("--runtime", "claude")
        self.assertEqual("claude\n", (self.source / "state/runtime-scope").read_text())
        self.assertFalse((self.home / ".codex/AGENTS.md").exists())
        self.assertFalse((self.home / ".codex/docs/harness-runtime-reference.md").exists())
        self.assertFalse((self.home / ".codex/skills/grill-me").exists())
        self.assertEqual("owner edit\n", edited.read_text())
        self.assertEqual("owner's codex skill\n",
                         (self.home / ".codex/skills/custom/SKILL.md").read_text())
        self.assertEqual("codex history\n", (self.home / ".codex/sessions/keep.jsonl").read_text())
        self.assertEqual(config_before, config.read_bytes())
        self.assertEqual(claude_before, {path: data for path, data in self.snapshot().items()
                                         if path.startswith(".claude/")})
        recovery = self.source / "state/backups/retirement"
        self.assertTrue(list(recovery.glob("*/.codex/AGENTS.md")))
        self.assertTrue(list(recovery.glob("*/.codex/skills/grill-me/SKILL.md")))
        self.assertTrue(list(recovery.glob("*/receipt.json")))
        verify = subprocess.run([sys.executable, str(self.source / "scripts/verify-profile.py")],
                                env=self.env, cwd=self.source, text=True, capture_output=True,
                                timeout=60)
        self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
        self.assertIn("runtime=claude", verify.stdout)
        before = self.snapshot()
        self.setup()
        self.setup("--check-instructions")
        self.assertEqual(before, self.snapshot(), "A bare rerun must reuse the Claude scope")

    def test_symlinked_runtime_directory_is_rejected_without_touching_destination(self):
        elsewhere = self.home / "keep-runtime"
        elsewhere.mkdir()
        (elsewhere / "owner-notes.md").write_text("preserve shared documents\n")
        for relative in (".codex", ".codex/skills", ".codex/docs",
                         ".claude", ".claude/skills", ".claude/docs"):
            with self.subTest(relative=relative):
                link = self.home / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(elsewhere)
                try:
                    before = self.snapshot()
                    result = self.setup(success=False)
                    self.assertIn("symlinked runtime directory", result.stdout)
                    self.assertEqual(before, self.snapshot())
                finally:
                    link.unlink()

    def assert_private_recovery(self):
        recovery = self.source / "state/backups/retirement"
        self.assertEqual(0o700, stat.S_IMODE(recovery.stat().st_mode))
        for path in recovery.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_dir():
                self.assertEqual(0o700, stat.S_IMODE(path.stat().st_mode), str(path))
            else:
                self.assertEqual(0, stat.S_IMODE(path.stat().st_mode) & 0o077, str(path))

    def test_private_claude_settings_symlink_stays_private_during_retirement(self):
        original = self.put("private-settings.json", json.dumps({
            "effortLevel": "high", "private_fixture_value": "keep"}))
        original.chmod(0o600)
        before = original.read_bytes()
        target = self.home / ".claude/settings.json"
        target.parent.mkdir(parents=True)
        target.symlink_to(original)
        self.retire()
        self.assertFalse(target.is_symlink())
        self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
        self.assertEqual({"private_fixture_value": "keep"}, json.loads(target.read_text()))
        saved = list((self.source / "state/backups/retirement").glob(
            "*/.claude/settings.json.resolved"))
        self.assertEqual(1, len(saved))
        self.assertEqual(before, saved[0].read_bytes())
        self.assertEqual(0o600, stat.S_IMODE(saved[0].stat().st_mode))
        self.assertEqual(before, original.read_bytes())
        self.assert_private_recovery()

    def test_private_codex_config_and_hooks_symlinks_do_not_widen_modes(self):
        originals = {
            "config.toml": 'model = "old"\nmodel_reasoning_effort = "medium"\nprivate_fixture = "keep"\n',
            "hooks.json": json.dumps({"private_fixture": "keep", "hooks": {
                "SessionStart": [{"hooks": [{"type": "command",
                    "command": "cat ~/.dot-agent/claude/caveman-boot.txt"}]}]}}),
        }
        (self.home / ".codex").mkdir()
        for name, content in originals.items():
            original = self.put("private-" + name, content)
            original.chmod(0o600)
            (self.home / ".codex" / name).symlink_to(original)
        self.retire("--codex-config")
        for name, content in originals.items():
            target = self.home / ".codex" / name
            self.assertFalse(target.is_symlink())
            self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
            original = self.home / ("private-" + name)
            self.assertEqual(content, original.read_text())
            saved = list((self.source / "state/backups/retirement").glob(
                "*/.codex/" + name + ".resolved"))
            self.assertEqual(1, len(saved))
            self.assertEqual(content, saved[0].read_text())
            self.assertEqual(0o600, stat.S_IMODE(saved[0].stat().st_mode))
        self.assert_private_recovery()

    def test_custom_status_line_is_preserved_as_one_command_object(self):
        command = {"type": "command", "command": "/owner/custom-status", "padding": 0}
        target = self.put(".claude/settings.json", json.dumps({
            "statusLine": command, "effortLevel": "high"}))
        self.retire()
        self.assertEqual({"statusLine": command}, json.loads(target.read_text()))
        manifest = json.loads((self.source / "scripts/fixtures/retired-runtime.json").read_text())
        target.write_text(json.dumps({"statusLine": manifest["claude_settings"]["statusLine"]}))
        self.retire()
        self.assertEqual({}, json.loads(target.read_text()))

    def test_custom_companion_blocks_whole_skill_retirement(self):
        self.setup()
        payload = self.home / ".codex/skills/bullet-style"
        original_entry = (payload / "SKILL.md").read_bytes()
        custom = self.put(".codex/skills/bullet-style/custom.txt", "unique companion\n")
        shutil.rmtree(self.source / "skills/style/bullet-style")
        result = self.setup(success=False)
        self.assertIn("Preserved edited or unverified retired skill", result.stdout)
        self.assertEqual("unique companion\n", custom.read_text())
        self.assertEqual(original_entry, (payload / "SKILL.md").read_bytes())
        self.assertFalse(list((self.source / "state/backups/retirement").glob(
            "*/.codex/skills/bullet-style")))

    def test_upgrade_retires_the_old_router_and_helper_skills(self):
        self.setup("--runtime", "all")
        for runtime in ("codex", "claude"):
            installed = self.home / f".{runtime}/skills"
            registry = self.source / f"state/managed-{runtime}-skills.json"
            entries = json.loads(registry.read_text())
            for old in ("router", "old-helper"):
                shutil.copytree(installed / "grill-me", installed / old)
                entries[old] = entries["grill-me"]
            registry.write_text(json.dumps(entries))
        self.setup()
        for runtime in ("codex", "claude"):
            registry = json.loads((self.source / f"state/managed-{runtime}-skills.json").read_text())
            for old in ("router", "old-helper"):
                self.assertFalse((self.home / f".{runtime}/skills/{old}").exists(), (runtime, old))
                self.assertTrue(list((self.source / "state/backups/retirement").glob(
                    f"*/.{runtime}/skills/{old}/SKILL.md")), (runtime, old))
                self.assertNotIn(old, registry)

    def test_setup_leaves_a_link_into_another_repo_alone(self):
        self.put(".dot-agent/profiles/personal/provided-skills", "helper\n")
        self.put(".dot-agent/state/machine-profile", "personal\n")
        self.setup("--runtime", "all")
        target = self.put("companion/skills/helper/SKILL.md", "companion helper\n").parent
        for runtime in ("codex", "claude"):
            registry = self.source / f"state/managed-{runtime}-skills.json"
            entries = json.loads(registry.read_text())
            entries["helper"] = entries["grill-me"]
            registry.write_text(json.dumps(entries))
            (self.home / f".{runtime}/skills/helper").symlink_to(target)
        self.setup()
        for runtime in ("codex", "claude"):
            link = self.home / f".{runtime}/skills/helper"
            self.assertEqual(str(target), os.readlink(link), runtime)
        verify = subprocess.run([sys.executable, str(self.source / "scripts/verify-profile.py")],
                                env=self.env, cwd=self.source, text=True, capture_output=True,
                                timeout=60)
        self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)

    def seed_retired_handoff(self):
        files = {"SKILL.md": "retired handoff\n", "agents/openai.yaml": "interface: {}\n"}
        signature = {"agents/": "directory"}
        for relative, text in files.items():
            self.put(f".codex/skills/handoff/{relative}", text)
            signature[relative] = hashlib.sha256(text.encode()).hexdigest()
        fixture = self.source / "scripts/fixtures/retired-runtime.json"
        manifest = json.loads(fixture.read_text())
        manifest["retired_payloads"]["handoff"] = [signature]
        fixture.write_text(json.dumps(manifest))
        return self.home / ".codex/skills/handoff"

    def test_frozen_retired_payload_can_retire_without_old_registry(self):
        self.setup()
        (self.source / "state/managed-codex-skills.json").unlink()
        self.seed_retired_handoff()
        self.retire()
        self.assertFalse((self.home / ".codex/skills/handoff").exists())
        saved = list((self.source / "state/backups/retirement").glob(
            "*/.codex/skills/handoff/SKILL.md"))
        self.assertEqual(1, len(saved))

    def test_retired_handoff_with_unknown_or_edited_content_blocks_install_and_check(self):
        self.setup()
        payload = self.seed_retired_handoff()
        custom = self.put(".codex/skills/handoff/custom.txt", "owner companion\n")
        for edited in (False, True):
            if edited:
                custom.unlink()
                (payload / "SKILL.md").write_text("owner-edited entrypoint\n")
            for args in ((), ("--check-instructions",)):
                with self.subTest(edited=edited, args=args):
                    before = self.snapshot()
                    result = self.setup(*args, success=False)
                    self.assertIn("BLOCKED: unresolved retired skills", result.stdout + result.stderr)
                    self.assertEqual(before, self.snapshot())
                    if not edited:
                        self.assertEqual("owner companion\n", custom.read_text())
                    else:
                        self.assertEqual("owner-edited entrypoint\n", (payload / "SKILL.md").read_text())
                    self.assertTrue((payload / "SKILL.md").is_file())

    def test_unsupported_valid_toml_is_rejected_before_any_setup_write(self):
        forms = (
            '"model" = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"\n',
            "'model' = 'gpt-5.6-sol'\nmodel_reasoning_effort = 'medium'\n",
            'model = "old"\n[features]\n"hooks" = false\n',
            'model = """gpt-5.6-sol\ncontinued"""\nmodel_reasoning_effort = "medium"\n',
            'custom = """preserve\nmodel = "inside a string"\n[features]\n"""\nmodel = "gpt-5.6-sol"\n',
            'custom = [\n"keep",\n"these",\n]\nmodel = "gpt-5.6-sol"\n',
        )
        for content in forms:
            with self.subTest(content=content):
                config = self.put(".codex/config.toml", content)
                before = self.snapshot()
                self.setup(success=False)
                self.assertEqual(content, config.read_text())
                self.assertEqual(before, self.snapshot())

    def test_direct_config_writer_rejects_quoted_duplicate_and_multiline_forms(self):
        forms = (
            '"model" = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"\n',
            '"model" = "first"\nmodel = "duplicate"\n',
            'model = """old\nvalue"""\n',
            'custom = """preserve\nmodel = "inside a string"\n[features]\n"""\nmodel = "old"\n',
        )
        interpreters = [sys.executable]
        modern = shutil.which("python3.13")
        if modern and modern != sys.executable:
            interpreters.append(modern)
        for interpreter in interpreters:
            for content in forms:
                with self.subTest(interpreter=interpreter, content=content):
                    config = self.put(".codex/config.toml", content)
                    before = self.snapshot()
                    result = subprocess.run([
                        interpreter, str(self.source / "scripts/retire-managed-runtime.py"),
                        "--source", str(self.source), "--home", str(self.home),
                        "--state", str(self.source / "state"), "--codex-config",
                    ], cwd=self.source, env=self.env, text=True, capture_output=True)
                    self.assertNotEqual(0, result.returncode, result.stdout)
                    self.assertEqual(content, config.read_text())
                    self.assertEqual(before, self.snapshot())

    def test_supported_toml_preserves_siblings_and_quoted_project_tables(self):
        config = self.put(".codex/config.toml",
            "model = 'old'\nmodel_reasoning_effort = 'medium'\n"
            "custom = 'unchanged'\n[projects.\"/fixture/project\"]\ntrust_level = 'trusted'\n")
        self.setup()
        text = config.read_text()
        self.assertIn('model = "gpt-6.1-sol"', text)
        self.assertIn("custom = 'unchanged'", text)
        self.assertIn('[projects."/fixture/project"]\ntrust_level = \'trusted\'', text)

    def test_drifted_codex_subagent_pins_converge(self):
        config = self.put(".codex/config.toml",
            'model = "gpt-6-astra"\nmodel_reasoning_effort = "ultra"\n'
            '[features]\nmulti_agent_v2 = true\n[agents]\n'
            'default_subagent_model = "gpt-6-astra"\ncustom = "keep"\n')
        self.setup()
        settings = strict_loads(config.read_text())
        self.assertEqual({"expose_spawn_agent_model_overrides": False},
                         settings["features"]["multi_agent_v2"])
        self.assertEqual({"default_subagent_model": "gpt-6.1-sol", "custom": "keep",
                          "default_subagent_reasoning_effort": "medium"}, settings["agents"])
        self.assertEqual(("gpt-6.1-sol", "high"),
                         (settings["model"], settings["model_reasoning_effort"]))

    def test_native_notice_and_tui_quoted_keys_survive_setup_and_repeat(self):
        notice = ('[notice.model_migrations]\n'
                  '"gpt-5.5" = "sanitized-fixture-target"\n'
                  "'older.model' = 'another-fixture-target'\n"
                  '\n[tui.model_availability_nux]\n'
                  '"gpt-5.5" = true\n')
        config = self.put(".codex/config.toml",
            'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"\n' + notice)
        self.setup()
        self.assertIn(notice, config.read_text())
        self.assertIn('model = "gpt-6.1-sol"', config.read_text())
        self.assertIn('model_reasoning_effort = "high"', config.read_text())
        before = self.snapshot()
        self.setup()
        self.setup("--check-instructions")
        self.assertEqual(before, self.snapshot())

    def test_fresh_profiles_and_switch_retire_only_recorded_skills(self):
        self.put(".dot-agent/profiles/work/provided-skills", "bullet-style\n")
        marker = self.put(".dot-agent/state/machine-profile", "personal\n")
        source = self.source / "skills/style/bullet-style/SKILL.md"
        source.write_text(source.read_text() + "\nFixture revision.\n")
        self.setup("--runtime", "all")
        self.assertTrue((self.home / ".codex/skills/bullet-style/SKILL.md").is_file())
        self.assertTrue((self.home / ".claude/skills/bullet-style/SKILL.md").is_file())
        self.put(".codex/skills/custom/SKILL.md", "preserve me\n")
        marker.write_text("work\n")
        self.setup()
        self.assertFalse((self.home / ".codex/skills/bullet-style").exists())
        self.assertFalse((self.home / ".claude/skills/bullet-style").exists())
        self.assertTrue((self.home / ".codex/skills/custom/SKILL.md").is_file())
        marker.write_text("personal\n")
        self.setup()
        self.assertTrue((self.home / ".codex/skills/bullet-style/SKILL.md").is_file())
        self.assertTrue((self.home / ".claude/skills/bullet-style/SKILL.md").is_file())

    def test_provided_skill_hands_over_to_companion_installer(self):
        marker = self.put(".dot-agent/state/machine-profile", "personal\n")
        self.setup("--runtime", "all")
        ours = (self.source / "skills/style/unslop/SKILL.md").read_text()
        self.assertEqual(ours, (self.home / ".claude/skills/unslop/SKILL.md").read_text())
        self.put(".dot-agent/state/work-ensure.sh",
                 'for r in codex claude; do d="$HOME/.$r/skills/unslop"\n'
                 '[ -e "$d" ] || { mkdir -p "$d"; echo "team unslop" > "$d/SKILL.md"; }; done\n')
        marker.write_text("work\n")
        self.setup()
        for runtime in ("codex", "claude"):
            self.assertEqual("team unslop\n",
                             (self.home / f".{runtime}/skills/unslop/SKILL.md").read_text())
        before = self.snapshot()
        self.setup()
        self.assertEqual(before, self.snapshot(), "Provided skills must stay untouched on repeat")

    def test_all_runtime_installs_claude_copies_and_keeps_owner_settings(self):
        manifest = json.loads((self.source / "scripts/fixtures/retired-runtime.json").read_text())
        settings = {"effortLevel": "high", "enabledPlugins": {"codex@openai-codex": True}}
        self.put(".claude/settings.json", json.dumps({
            **settings, "statusLine": manifest["claude_settings"]["statusLine"],
            "hooks": manifest["claude_settings"]["hooks"]}))
        self.put(".claude/skills/show-me/placeholder", "")
        (self.home / ".claude/skills/show-me/placeholder").unlink()
        (self.home / ".claude/skills/show-me/SKILL.md").symlink_to(
            self.source / "skills/learning/show-me/SKILL.md")
        self.put(".claude/skills/custom/SKILL.md", "owner's custom skill\n")
        self.put(".claude/CLAUDE.md", "# Machine-local\n\nkeep me\n")
        self.setup("--runtime", "all")
        lock = json.loads((self.source / "claude/model-lock.json").read_text())
        hooks = json.loads((self.source / "claude/hooks.json").read_text())
        env = {**lock["env"], "CLAUDE_CODE_PLUGIN_DIRS": "~/.dot-agent/claude/mods/mermaid-style"}
        self.assertEqual({**settings, **lock, "env": env, "hooks": hooks, "claudeMdExcludes": [CLOUD_RULES]},
                         json.loads((self.home / ".claude/settings.json").read_text()))
        instructions = self.home / ".claude/CLAUDE.md"
        self.assertFalse(instructions.is_symlink())
        self.assertEqual(f"@{self.source / 'state/generated/AGENTS.md'}\n\n# Machine-local\n\nkeep me\n",
                         instructions.read_text())
        self.assertEqual((self.source / "docs/harness-runtime-reference.md").read_bytes(),
                         (self.home / ".claude/docs/harness-runtime-reference.md").read_bytes())
        runner = "scheduled-tasks/gardening-hunter/SKILL.md"
        self.assertEqual((self.source / "claude" / runner).read_bytes(),
                         (self.home / ".claude" / runner).read_bytes())
        skill = self.home / ".claude/skills/grill-me/SKILL.md"
        self.assertFalse(skill.is_symlink())
        self.assertEqual((self.source / "skills/engineering/grill-me/SKILL.md").read_bytes(),
                         skill.read_bytes())
        self.assertEqual("owner's custom skill\n",
                         (self.home / ".claude/skills/custom/SKILL.md").read_text())
        self.assertEqual("all\n", (self.source / "state/runtime-scope").read_text())
        self.assertFalse((self.home / ".claude/skills/show-me/SKILL.md").is_symlink())
        before = self.snapshot()
        self.setup()
        self.setup("--check-instructions")
        self.assertEqual(before, self.snapshot(), "Repeat Claude install must leave bytes stable")
        drifted = self.home / ".claude/settings.json"
        drifted.write_text(json.dumps({**json.loads(drifted.read_text()), "claudeMdExcludes": []}))
        verify = subprocess.run([sys.executable, str(self.source / "scripts/verify-profile.py"), "--runtime", "all"],
                                env=self.env, cwd=self.source, text=True, capture_output=True, timeout=60)
        self.assertNotEqual(0, verify.returncode)
        self.assertIn("FAIL  claude settings skip the cloud rules copy", verify.stdout)
        drifted.write_text(json.dumps({**json.loads(drifted.read_text()), "model": "sonnet"}))
        result = self.setup("--check-instructions", success=False)
        self.assertIn("STALE managed target: .claude/settings.json", result.stdout)
        shutil.rmtree(self.source / "skills/learning/show-me")
        self.setup()
        self.assertFalse((self.home / ".claude/skills/show-me").exists())
        self.assertTrue(list((self.source / "state/backups/retirement").glob("*/.claude/skills/show-me")))

    def test_runtime_scope_is_saved_even_when_the_install_fails(self):
        self.put(".claude/settings.json", "{not json")
        self.setup("--runtime", "all", success=False)
        self.assertEqual("all\n", (self.source / "state/runtime-scope").read_text())

    def test_claude_model_lock_overrides_owner_model_and_keeps_other_keys(self):
        lock = json.loads((self.source / "claude/model-lock.json").read_text())
        target = self.put(".claude/settings.json", json.dumps({
            "model": "sonnet", "effortLevel": "max",
            "modelSettings": {"claude-opus-5-5": {"effortLevel": "medium", "autoCompactWindow": 200}},
            "env": {"OWNER_VAR": "1", "ANTHROPIC_DEFAULT_HAIKU_MODEL": "haiku",
                    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"},
            "enabledPlugins": {"my-plugin": True, "codex@openai-codex": True}}))
        target.chmod(0o644)
        self.retire("--runtime", "all")
        settings = json.loads(target.read_text())
        self.assertEqual("claude-opus-5-5", settings["model"])
        self.assertEqual(lock["availableModels"], settings["availableModels"])
        self.assertTrue(settings["enforceAvailableModels"])
        self.assertEqual("max", settings["effortLevel"])
        self.assertEqual("high", settings["modelSettings"]["claude-opus-5-5"]["effortLevel"])
        self.assertEqual(200, settings["modelSettings"]["claude-opus-5-5"]["autoCompactWindow"])
        mods = "~/.dot-agent/claude/mods/mermaid-style"
        self.assertEqual({"OWNER_VAR": "1", **lock["env"], "CLAUDE_CODE_PLUGIN_DIRS": mods}, settings["env"])
        self.assertEqual({"my-plugin": True, "codex@openai-codex": False, "engineering@inline": False,
                          "github@claude-plugins-official": False}, settings["enabledPlugins"])
        self.assertEqual(0o644, stat.S_IMODE(target.stat().st_mode))
        saved = list((self.source / "state/backups/retirement").glob("*/.claude/settings.json"))
        self.assertEqual(1, len(saved))
        self.assertEqual("sonnet", json.loads(saved[0].read_text())["model"])
        before = self.snapshot()
        self.retire("--runtime", "all")
        self.assertEqual(before, self.snapshot(), "Second run must be a no-op")

    def test_setup_loads_every_mod_and_keeps_owner_plugin_dirs(self):
        target = self.put(".claude/settings.json", json.dumps({"env": {"CLAUDE_CODE_PLUGIN_DIRS": "~/my-mods/x"}}))
        self.retire("--runtime", "all")
        dirs = json.loads(target.read_text())["env"]["CLAUDE_CODE_PLUGIN_DIRS"].split(os.pathsep)
        self.assertEqual(["~/my-mods/x", "~/.dot-agent/claude/mods/mermaid-style"], dirs)
        before = self.snapshot()
        self.retire("--runtime", "all")
        self.assertEqual(before, self.snapshot(), "Second run must be a no-op")

    def test_setup_skips_the_cloud_rules_copy_locally_and_keeps_owner_excludes(self):
        target = self.put(".claude/settings.json", json.dumps({"claudeMdExcludes": ["**/mine/CLAUDE.md"]}))
        self.retire("--runtime", "all")
        self.assertEqual(["**/mine/CLAUDE.md", CLOUD_RULES], json.loads(target.read_text())["claudeMdExcludes"])

    def test_claude_hooks_install_once_keep_owner_hooks_and_replace_old_managed_ones(self):
        owner = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo owner"}]}
        stale = {"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 ~/.dot-agent/claude/hooks/old.py"}]}
        target = self.put(".claude/settings.json", json.dumps({"hooks": {
            "PreToolUse": [owner, stale], "Stop": [owner]}}))
        self.retire("--runtime", "all")
        wanted = json.loads((self.source / "claude/hooks.json").read_text())
        hooks = json.loads(target.read_text())["hooks"]
        self.assertEqual({"PreToolUse": [owner, *wanted["PreToolUse"]], "Stop": [owner, *wanted["Stop"]]}, hooks)
        before = self.snapshot()
        self.retire("--runtime", "all")
        self.assertEqual(before, self.snapshot(), "Second run must be a no-op")
        self.put(".claude/settings.json", json.dumps({"hooks": {"PreToolUse": {"bad": 1}}}))
        result = subprocess.run([
            sys.executable, str(self.source / "scripts/retire-managed-runtime.py"),
            "--source", str(self.source), "--home", str(self.home),
            "--state", str(self.source / "state"), "--runtime", "all",
        ], cwd=self.source, env=self.env, text=True, capture_output=True, timeout=30)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("hooks.PreToolUse is not a list", result.stderr)

    def test_claude_model_lock_refuses_symlinked_settings(self):
        owned = {"model": "sonnet", "statusLine": {
            "type": "command", "command": "~/.claude/statusline-enhanced.sh", "padding": 0}}
        original = self.put("dotfiles/settings.json", json.dumps(owned))
        target = self.home / ".claude/settings.json"
        target.parent.mkdir(parents=True)
        target.symlink_to(original)
        result = subprocess.run([
            sys.executable, str(self.source / "scripts/retire-managed-runtime.py"),
            "--source", str(self.source), "--home", str(self.home),
            "--state", str(self.source / "state"), "--runtime", "all",
        ], cwd=self.source, env=self.env, text=True, capture_output=True, timeout=30)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("is a symlink", result.stderr)
        self.assertTrue(target.is_symlink())
        self.assertEqual(owned, json.loads(original.read_text()))

    def test_compliant_symlinked_claude_settings_is_read_not_replaced(self):
        lock = json.loads((self.source / "claude/model-lock.json").read_text())
        hooks = json.loads((self.source / "claude/hooks.json").read_text())
        env = {**lock["env"], "CLAUDE_CODE_PLUGIN_DIRS": "~/.dot-agent/claude/mods/mermaid-style"}
        original = self.put("dotfiles/settings.json", json.dumps({**lock, "env": env, "hooks": hooks,
                                                                  "claudeMdExcludes": [CLOUD_RULES],
                                                                  "theme": "dark"}))
        before = original.read_bytes()
        target = self.home / ".claude/settings.json"
        target.parent.mkdir(parents=True)
        target.symlink_to(original)
        self.retire("--runtime", "all")
        self.assertTrue(target.is_symlink())
        self.assertEqual(before, original.read_bytes())

    def test_codex_pinned_table_with_owner_keys_blocks(self):
        config = self.put(".codex/config.toml",
            '[features]\nmulti_agent_v2 = { expose_spawn_agent_model_overrides = true, max = 3 }\n')
        result = self.setup(success=False)
        self.assertIn("has owner keys", result.stdout + result.stderr)
        self.assertIn("expose_spawn_agent_model_overrides = true, max = 3", config.read_text())

    def test_claude_owner_content_blocks_instead_of_being_replaced(self):
        owner = self.put(".claude/skills/verify/SKILL.md", "owner's own verify skill\n")
        result = self.setup("--runtime", "all", success=False)
        self.assertIn("BLOCKED", result.stdout + result.stderr)
        self.assertEqual("owner's own verify skill\n", owner.read_text())
        self.assertFalse((self.home / ".codex/AGENTS.md").exists(), "Blocked before installing")
        owner.unlink()
        target = self.put("dotfiles/CLAUDE.md", "linked owner notes\n")
        (self.home / ".claude/CLAUDE.md").symlink_to(target)
        result = self.setup("--runtime", "all", success=False)
        self.assertIn("is a symlink", result.stdout + result.stderr)
        self.assertEqual("linked owner notes\n", target.read_text())


    def fake_launchctl(self, body=""):
        log = self.home / "launchctl.log"
        tool = self.put("fake-bin/launchctl", f'#!/bin/sh\necho "$@" >> "{log}"\n{body}')
        tool.chmod(0o755)
        self.env["PATH"] = str(tool.parent) + os.pathsep + self.env["PATH"]
        return log

    def put_launchagent(self, label, script):
        path = self.home / "Library/LaunchAgents" / f"{label}.plist"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            plistlib.dump({"Label": label, "ProgramArguments": [
                "/usr/bin/python3", str(self.home / script), "serve"]}, handle)
        return path

    def test_retired_launchagents_boot_out_and_move_on_exact_match_only(self):
        log = self.fake_launchctl()
        driver = self.put_launchagent(
            "me.dot-agent.daily-driver", ".dot-agent/skills/personal/daily-driver/scripts/daily_driver.py")
        atlas = self.put_launchagent(
            "me.dot-agent.atlas-memory-map", ".dot-agent/skills/personal/atlas/scripts/atlas.py")
        keep = self.put_launchagent(
            "me.dot-agent.other-service", ".dot-agent/skills/other/service/scripts/service.py")
        driver_bytes, atlas_bytes, keep_bytes = (p.read_bytes() for p in (driver, atlas, keep))
        result = self.setup("--check-instructions", success=False)
        self.assertIn("STALE managed target: Library/LaunchAgents/me.dot-agent.daily-driver.plist",
                      result.stdout)
        self.assertEqual([driver_bytes, atlas_bytes], [driver.read_bytes(), atlas.read_bytes()])
        self.assertFalse((self.source / "state/retired-launchagents").exists())
        self.assertFalse(log.exists())
        self.retire()
        uid = os.getuid()
        self.assertEqual([f"bootout gui/{uid}/me.dot-agent.daily-driver",
                          f"bootout gui/{uid}/me.dot-agent.atlas-memory-map"],
                         log.read_text().splitlines())
        folder = self.source / "state/retired-launchagents"
        self.assertEqual(0o700, stat.S_IMODE(folder.stat().st_mode))
        self.assertEqual(driver_bytes, (folder / driver.name).read_bytes())
        self.assertEqual(atlas_bytes, (folder / atlas.name).read_bytes())
        self.assertEqual(0o600, stat.S_IMODE((folder / driver.name).stat().st_mode))
        self.assertFalse(driver.exists() or atlas.exists())
        self.assertEqual(keep_bytes, keep.read_bytes())
        before = self.snapshot()
        self.retire()
        self.assertEqual(before, self.snapshot())

    def test_launchagent_is_kept_when_bootout_fails_and_job_is_still_loaded(self):
        label = "me.dot-agent.daily-driver"
        log = self.fake_launchctl('[ "$1" = print ] && exit 0\nexit 5\n')
        driver = self.put_launchagent(label, ".dot-agent/skills/personal/daily-driver/scripts/d.py")
        result = self.retire()
        self.assertIn("launchctl could not stop", result.stdout)
        self.assertTrue(driver.is_file())
        uid = os.getuid()
        self.assertEqual([f"bootout gui/{uid}/{label}", f"print gui/{uid}/{label}"],
                         log.read_text().splitlines())
        log.write_text("")
        self.fake_launchctl('[ "$1" = print ] && exit 113\nexit 3\n')
        self.retire()
        self.assertFalse(driver.exists())
        self.assertTrue((self.source / "state/retired-launchagents" / driver.name).is_file())
        receipt = next((self.source / "state/backups/retirement").glob("*/receipt.json"))
        self.assertEqual([str(self.source / "state/retired-launchagents" / driver.name)],
                         list(json.loads(receipt.read_text())["moved"].values()))

    def test_launchagent_with_another_program_is_preserved(self):
        log = self.fake_launchctl()
        other = self.put_launchagent("me.dot-agent.daily-driver", "elsewhere/daily_driver.py")
        result = self.retire()
        self.assertIn("Preserved unverified LaunchAgent", result.stdout)
        self.assertTrue(other.is_file())
        self.assertFalse(log.exists())

    def test_retired_speak_config_moves_only_when_unedited(self):
        old = "managed speak settings\n"
        fixture = self.source / "scripts/fixtures/retired-runtime.json"
        manifest = json.loads(fixture.read_text())
        manifest["retired_files"][".codex/speak.config.toml"] = hashlib.sha256(old.encode()).hexdigest()
        fixture.write_text(json.dumps(manifest))
        speak = self.put(".codex/speak.config.toml", "owner edit\n")
        result = self.retire()
        self.assertIn("Kept .codex/speak.config.toml", result.stdout)
        self.assertEqual("owner edit\n", speak.read_text())
        speak.write_text(old)
        self.retire()
        self.assertFalse(speak.exists())
        saved = list((self.source / "state/backups/retirement").glob("*/.codex/speak.config.toml"))
        self.assertEqual([old], [path.read_text() for path in saved])

    def test_generated_keymap_is_removed_only_when_exact_and_no_hooks_file_is_created(self):
        generated = ('\n[tui.keymap.global]\nopen_transcript = "ctrl-o"\n'
                     'open_external_editor = "ctrl-g"\n\n[tui.keymap.editor]\n'
                     'insert_newline = "ctrl-j"\n')
        config = self.put(".codex/config.toml", 'model = "gpt-6.1-sol"\ncustom = "keep"\n'
                          '\n[tui]\nanimations = false\n' + generated)
        self.setup()
        text = config.read_text()
        self.assertNotIn("tui.keymap", text)
        self.assertEqual({"animations": False}, strict_loads(text)["tui"])
        self.assertIn('custom = "keep"', text)
        self.assertFalse((self.home / ".codex/hooks.json").exists())
        edited = generated.replace('"ctrl-j"', '"ctrl-m"')
        config.write_text(config.read_text() + edited)
        self.setup()
        self.assertIn(edited, config.read_text())

if __name__ == "__main__":
    unittest.main()
