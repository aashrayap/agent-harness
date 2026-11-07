#!/usr/bin/env python3
from __future__ import annotations

import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts import toml_compat


class TomlCompatTests(unittest.TestCase):
    def assert_read_only_audit(self, name, *arguments) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            scripts = root / "scripts"
            scripts.mkdir()
            source_scripts = Path(__file__).resolve().parents[1]
            for filename in (name, "toml_compat.py"):
                shutil.copyfile(source_scripts / filename, scripts / filename)
            config = 'model = "gpt-6-astra"\n'
            for directory in (root / "codex", root / "runtime"):
                directory.mkdir()
                (directory / "config.toml").write_text(config)
            before = {str(path.relative_to(root)): path.read_bytes()
                      for path in root.rglob("*") if path.is_file()}
            env = os.environ.copy()
            for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX",
                        "DOT_AGENT_STATE_HOME"):
                env.pop(key, None)
            env.update({"HOME": str(root), "DOT_AGENT_HOME": str(root),
                        "CODEX_HOME": str(root / "runtime")})
            runner = (
                "import runpy,sys\n"
                "sys.modules['tomllib'] = None\n"
                "sys.modules['tomli'] = None\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "sys.argv = sys.argv[2:]\n"
                "runpy.run_path(sys.argv[0], run_name='__main__')\n"
            )
            result = subprocess.run(
                [sys.executable, "-S", "-c", runner, str(scripts),
                 str(scripts / name), *arguments],
                env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            after = {str(path.relative_to(root)): path.read_bytes()
                     for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_read_only_settings_audit_does_not_cache_compatibility_import(self) -> None:
        self.assert_read_only_audit("settings-drift-audit.py")

    def test_read_only_repo_audit_does_not_cache_compatibility_import(self) -> None:
        self.assert_read_only_audit("repo-instruction-audit.py", "--help")

    def test_basic_string_escapes_are_decoded(self) -> None:
        config = toml_compat.load(io.BytesIO(
            b'[mcp_servers.example]\n'
            b'command = "sh"\n'
            b'args = ["-c", "exec \\"$HOME/.local/bin/tool\\""]\n'
        ))
        self.assertEqual(config["mcp_servers"]["example"], {
            "command": "sh",
            "args": ["-c", 'exec "$HOME/.local/bin/tool"'],
        })

    def test_array_scalars_keep_their_types(self) -> None:
        config = toml_compat.load(io.BytesIO(b'values = ["one", 2, true]\n'))
        self.assertEqual(config["values"], ["one", 2, True])


if __name__ == "__main__":
    unittest.main()
