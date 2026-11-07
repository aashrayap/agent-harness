#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RetiredProxyCleanupTests(unittest.TestCase):
    def test_setup_removes_runtime_but_preserves_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw).resolve() / "home"
            checkout = home / ".dot-agent"
            shutil.copytree(
                ROOT,
                checkout,
                ignore=shutil.ignore_patterns(
                    ".git", "state", "__pycache__", "*.pyc"),
            )
            subprocess.run(
                ["git", "init", "--quiet", str(checkout)],
                check=True,
                capture_output=True,
                text=True,
            )

            generated = checkout / "state/generated/docs/peer-runtime-proxy.md"
            generated.parent.mkdir(parents=True)
            generated.write_text("retired generated doc\n", encoding="utf-8")

            local_bin = home / ".local/bin"
            local_bin.mkdir(parents=True)
            binary = local_bin / "cli-proxy-api"
            binary.write_text("retired binary\n", encoding="utf-8")
            launcher = local_bin / "claude-gpt"
            control = local_bin / "cliproxyctl"
            launcher.symlink_to(checkout / "claude/claude-gpt")
            control.symlink_to(checkout / "proxy/cliproxyctl")

            claude_doc = home / ".claude/docs/peer-runtime-proxy.md"
            claude_doc.parent.mkdir(parents=True)
            claude_doc.symlink_to(generated)
            custom_target = home / "keep-custom-proxy-doc.md"
            custom_target.write_text("owner managed\n", encoding="utf-8")
            codex_doc = home / ".codex/docs/peer-runtime-proxy.md"
            codex_doc.parent.mkdir(parents=True)
            codex_doc.symlink_to(custom_target)

            auth = home / ".config/cli-proxy-api/auth/token.json"
            auth.parent.mkdir(parents=True)
            auth.write_text("secret\n", encoding="utf-8")
            session = home / ".claude-gpt/session.json"
            session.parent.mkdir()
            session.write_text("session\n", encoding="utf-8")
            plist = home / "Library/LaunchAgents/me.dot-agent.cliproxyapi.plist"
            plist.parent.mkdir(parents=True)
            plist.write_text("retired service\n", encoding="utf-8")

            environment = dict(os.environ)
            environment["HOME"] = str(home)
            environment["DOT_AGENT_LAUNCHCTL"] = "/usr/bin/true"
            result = subprocess.run(
                ["bash", str(checkout / "setup.sh")],
                cwd=checkout,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )

            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            self.assertFalse(launcher.exists() or launcher.is_symlink())
            self.assertFalse(control.exists() or control.is_symlink())
            self.assertTrue(binary.exists())
            self.assertTrue(plist.exists())
            self.assertFalse(claude_doc.exists() or claude_doc.is_symlink())
            self.assertTrue(generated.exists())
            self.assertTrue(codex_doc.is_symlink())
            self.assertEqual(custom_target, codex_doc.resolve())
            self.assertEqual("secret\n", auth.read_text(encoding="utf-8"))
            self.assertEqual("session\n", session.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
