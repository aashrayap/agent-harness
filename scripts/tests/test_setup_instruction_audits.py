#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


FAKE_CODEX = r'''#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "exec" && "${2:-}" == "review" \
      && "${3:-}" == "--help" ]]; then
  exit 0
fi
[[ "${1:-}" == "exec" ]] || exit 2

output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-last-message)
      output="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
[[ -n "$output" ]] || exit 2
printf '{"ok":true,"probe":"codex-delegation"}' > "$output"
printf 'model: gpt-6.1-sol\nprovider: openai\nsession id: 019f0000-0000-7000-8000-000000000001\n' >&2
printf 'exec\n' >> "$FAKE_CODEX_LOG"
'''


class SetupInstructionAuditTests(unittest.TestCase):
    def run_audit_with_stale_manifest(
        self, runtime: str
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            scratch = Path(raw).resolve()
            home = scratch / "home"
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
            environment = dict(os.environ)
            environment["HOME"] = str(home)
            installed = subprocess.run(
                ["bash", str(checkout / "setup.sh"), "--runtime", "all"],
                cwd=checkout,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(
                0, installed.returncode, installed.stderr or installed.stdout
            )

            source_agents = checkout / "skills/engineering/grill-me/agents"
            installed_agents = home / f".{runtime}/skills/grill-me/agents"
            if installed_agents.is_symlink():
                installed_agents.unlink()
                shutil.copytree(source_agents, installed_agents)
            manifest = installed_agents / "openai.yaml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true",
                ),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    "python3",
                    str(checkout / "scripts/skill-instruction-audit.py"),
                    "--strict",
                ],
                cwd=checkout,
                env=environment,
                capture_output=True,
                text=True,
            )

    def test_instruction_audit_rejects_stale_codex_manifest(self) -> None:
        result = self.run_audit_with_stale_manifest("codex")

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(
            "installed agents/openai.yaml differs from source",
            result.stdout,
        )

    def run_setup(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as raw:
            scratch = Path(raw).resolve()
            home = scratch / "home"
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
            fake_bin = scratch / "bin"
            fake_bin.mkdir()
            fake = fake_bin / "codex"
            fake.write_text(FAKE_CODEX, encoding="utf-8")
            fake.chmod(0o755)
            log = scratch / "codex.log"
            codex_home = scratch / "codex-home"
            codex_home.mkdir()
            environment = dict(os.environ)
            environment.update({
                "CLAUDECODE": "",
                "CODEX_BIN": str(fake),
                "HOME": str(home),
                "CODEX_HOME": str(codex_home),
                "FAKE_CODEX_LOG": str(log),
                "PATH": f"{fake_bin}:{environment['PATH']}",
            })
            installed = subprocess.run(
                ["bash", str(checkout / "setup.sh")],
                cwd=checkout,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if installed.returncode != 0:
                self.fail(installed.stderr or installed.stdout)
            log.unlink(missing_ok=True)
            result = subprocess.run(
                ["bash", str(checkout / "setup.sh"), *arguments],
                cwd=checkout,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            calls = log.read_text(encoding="utf-8") if log.exists() else ""
            return result, calls

    def test_check_instructions_is_deterministic_by_default(self) -> None:
        result, calls = self.run_setup("--check-instructions")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", calls)

    def test_explicit_live_delegation_probe_runs_once(self) -> None:
        result, calls = self.run_setup(
            "--check-instructions", "--live-delegation-probe")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("exec\n", calls)


if __name__ == "__main__":
    unittest.main()
