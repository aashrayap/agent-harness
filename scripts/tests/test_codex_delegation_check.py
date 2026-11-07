#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts/codex-delegation-check.sh"
SESSION_ID = "019f0000-0000-7000-8000-000000000001"


FAKE_CODEX = r'''#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "exec" && "${2:-}" == "review" \
      && "${3:-}" == "--help" ]]; then
  exit 0
fi
[[ "${1:-}" == "exec" ]] || exit 2

output=""
requested_model=""
requested_effort=""
saw_ephemeral=0
sandbox=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      requested_model="$2"
      shift 2
      ;;
    --ephemeral)
      saw_ephemeral=1
      shift
      ;;
    --config)
      requested_effort="$2"
      shift 2
      ;;
    --sandbox)
      sandbox="$2"
      shift 2
      ;;
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
[[ "$requested_model" == "gpt-6.1-sol" ]] || { printf 'fake: wrong model flag\n' >&2; exit 3; }
[[ "$requested_effort" == "model_reasoning_effort=high" ]] || { printf 'fake: wrong effort config\n' >&2; exit 3; }
[[ "$saw_ephemeral" == 1 ]] || { printf 'fake: missing ephemeral flag\n' >&2; exit 3; }
[[ "$sandbox" == "read-only" ]] || { printf 'fake: wrong sandbox flag\n' >&2; exit 3; }

scenario="${FAKE_CODEX_SCENARIO:-success}"
model="gpt-6.1-sol"
provider="openai"
session="019f0000-0000-7000-8000-000000000001"
reply='{"ok":true,"probe":"codex-delegation"}'

case "$scenario" in
  substituted-model) model="gpt-5.4" ;;
  substituted-provider) provider="azure" ;;
  malformed-metadata) session="not-a-session" ;;
  mismatched-reply) reply='{"ok":false}' ;;
  persisted)
    mkdir -p "$CODEX_HOME/sessions"
    : > "$CODEX_HOME/sessions/probe-$session.jsonl"
    ;;
esac

printf '%s' "$reply" > "$output"
printf 'model: %s\nprovider: %s\nsession id: %s\n' "$model" "$provider" "$session" >&2
'''


class CodexDelegationCheckTests(unittest.TestCase):
    def run_probe(self, scenario: str, claudecode: str = "") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            scratch = Path(raw)
            fake_bin = scratch / "bin"
            fake_bin.mkdir()
            fake = fake_bin / "codex"
            fake.write_text(FAKE_CODEX)
            fake.chmod(0o755)
            codex_home = scratch / "codex-home"
            codex_home.mkdir()
            environment = dict(os.environ)
            environment.update({
                "CODEX_BIN": str(fake),
                "CODEX_HOME": str(codex_home),
                "FAKE_CODEX_SCENARIO": scenario,
                "CLAUDECODE": claudecode,
                "PATH": f"{fake_bin}:{environment['PATH']}",
            })
            return subprocess.run(
                ["bash", str(PROBE)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_exact_reply_and_identity_evidence_pass(self) -> None:
        result = self.run_probe("success")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("request model=gpt-6.1-sol effort=high provider=openai", result.stdout)
        self.assertIn("persistence=ephemeral", result.stdout)
        self.assertIn("response-side identity unavailable", result.stdout)

    def test_refuses_inside_claude_code(self) -> None:
        result = self.run_probe("success", claudecode="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not Claude Code", result.stderr)

    def test_model_substitution_fails(self) -> None:
        result = self.run_probe("substituted-model")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request model evidence missing or substituted", result.stderr)

    def test_provider_substitution_fails(self) -> None:
        result = self.run_probe("substituted-provider")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request provider evidence missing or substituted", result.stderr)

    def test_malformed_session_metadata_fails(self) -> None:
        result = self.run_probe("malformed-metadata")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request session evidence missing or malformed", result.stderr)

    def test_mismatched_reply_fails(self) -> None:
        result = self.run_probe("mismatched-reply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("probe reply was not the exact expected JSON", result.stderr)

    def test_persisted_session_fails(self) -> None:
        result = self.run_probe("persisted")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"ephemeral probe persisted session {SESSION_ID}", result.stderr)


if __name__ == "__main__":
    unittest.main()
