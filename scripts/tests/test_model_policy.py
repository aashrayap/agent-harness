from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from toml_edit import strict_loads
ALLOWED = {"claude-opus-5-5", "claude-sonnet-5-5", "gpt-6-astra", "gpt-6.1-sol"}
MODEL_ID = re.compile(r"gpt-\d[\w.\-]*|claude-(?:opus|sonnet|haiku|fable)[\w.\-]*")
CLAUDE_LOCK = {
    "model": "claude-opus-5-5",
    "modelSettings": {"claude-opus-5-5": {"effortLevel": "high"}},
    "availableModels": ["claude-opus-5-5", "claude-sonnet-5-5"],
    "enforceAvailableModels": True,
    "env": {
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5-5",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5-5",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-sonnet-5-5",
        "CLAUDE_CODE_SUBAGENT_MODEL": "claude-opus-5-5",
    },
    "enabledPlugins": {"codex@openai-codex": False, "engineering@inline": False,
                       "github@claude-plugins-official": False},
}


def active_files() -> list[Path]:
    files = [ROOT / name for name in (
        "AGENTS.md", "README.md", "GLOSSARY.md", "docs/harness-runtime-reference.md",
        "claude/model-lock.json")]
    files += sorted((ROOT / "codex").glob("*.toml"))
    skills = ROOT / "skills"
    files += [path for pattern in ("**/SKILL.md", "**/agents/*.yaml")
              for path in sorted(skills.glob(pattern))
              if "upstream" not in path.relative_to(skills).parts]
    return [path for path in files if path.is_file()]


class ModelPolicyTests(unittest.TestCase):
    def test_codex_config_pins_parent_and_subagents(self):
        text = (ROOT / "codex/config.toml").read_text()
        config = strict_loads(text)
        self.assertEqual(("gpt-6.1-sol", "high"),
                         (config["model"], config["model_reasoning_effort"]))
        self.assertEqual({"default_subagent_model": "gpt-6.1-sol",
                          "default_subagent_reasoning_effort": "medium"}, config["agents"])
        self.assertEqual({"expose_spawn_agent_model_overrides": False},
                         config["features"]["multi_agent_v2"])
        self.assertNotIn("ultra", text)

    def test_the_lock_check_allows_owner_keys_at_any_depth_and_fails_drift(self) -> None:
        spec = importlib.util.spec_from_file_location("verify_profile", ROOT / "scripts/verify-profile.py")
        profile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profile)
        lock = {"model": "m", "modelSettings": {"claude-opus-5-5": {"effortLevel": "high"}}}
        owner = {"model": "m", "other": 1, "modelSettings": {"claude-opus-5-5": {"effortLevel": "high", "autoCompactWindow": 200}}}
        self.assertTrue(profile.locked_in(lock, owner))
        self.assertFalse(profile.locked_in(lock, {"model": "m", "modelSettings": {"claude-opus-5-5": {"effortLevel": "medium"}}}))
        self.assertFalse(profile.locked_in(lock, {"model": "m", "modelSettings": "high"}))
        self.assertFalse(profile.locked_in(lock, {"model": "m"}))

    def test_effort_is_set_per_model_not_at_the_top_level(self) -> None:
        lock = json.loads((ROOT / "claude/model-lock.json").read_text())
        self.assertNotIn("effortLevel", lock)
        self.assertEqual("high", lock["modelSettings"]["claude-opus-5-5"]["effortLevel"])

    def test_claude_model_lock_is_exact(self):
        self.assertEqual(CLAUDE_LOCK, json.loads((ROOT / "claude/model-lock.json").read_text()))

    def test_active_instructions_name_only_allowed_models(self):
        files = active_files()
        self.assertGreater(len(files), 10)
        stray = sorted({f"{path.relative_to(ROOT)}: {match}"
                        for path in files
                        for match in MODEL_ID.findall(path.read_text())
                        if match.rstrip(".-") not in ALLOWED})
        self.assertEqual([], stray)


if __name__ == "__main__":
    unittest.main()
