#!/usr/bin/env python3
from __future__ import annotations

import runpy
import tempfile
import unittest
import contextlib
import io
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
AUDITOR = runpy.run_path(
    str(ROOT / "scripts" / "repo-instruction-audit.py")
)
FILE_STATUS = AUDITOR["file_status"]


class RepoInstructionAuditTests(unittest.TestCase):
    def test_flags_multiline_peer_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            agents = Path(raw) / "AGENTS.md"
            agents.write_text(
                "The native Claude desktop app and native Codex are\n"
                "peer runtimes.\n",
                encoding="utf-8",
            )

            self.assertEqual("legacy-runtime", FILE_STATUS(agents))

    def test_names_alone_do_not_prove_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            agents = Path(raw) / "AGENTS.md"
            agents.write_text(
                "Install the native Claude desktop app and native Codex.\n",
                encoding="utf-8",
            )

            self.assertEqual("unverified", FILE_STATUS(agents))

    def test_recognizes_current_declarations_without_global_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            agents = Path(raw) / "AGENTS.md"
            agents.write_text("Claude Code and Codex are both primary\nruntimes.",
                              encoding="utf-8")
            self.assertEqual("ok", FILE_STATUS(agents))
            for stale in ("Native Codex is the supported runtime.",
                          "Codex is the primary runtime."):
                with self.subTest(stale=stale):
                    agents.write_text(stale, encoding="utf-8")
                    self.assertEqual("unverified", FILE_STATUS(agents))

    def test_known_legacy_wording_is_not_cleared_by_current_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            agents = Path(raw) / "AGENTS.md"
            for legacy in (
                "Native Claude desktop app and native Codex as peers",
                "Claude Code and Codex are peer runtimes",
            ):
                with self.subTest(legacy=legacy):
                    agents.write_text("Claude Code and Codex are both primary runtimes.\n" + legacy,
                                      encoding="utf-8")
                    status = AUDITOR["inspect_repo"](Path(raw), ["fixture"])
                    self.assertEqual("legacy-runtime", status.agents)
                    self.assertEqual(["WARN"], [item.severity for item in status.findings])
                    self.assertIn("owner review", status.findings[0].message)

    def test_missing_or_domain_only_instructions_are_information_not_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            for content in (None, "Preserve project data. Use the existing tests."):
                with self.subTest(content=content):
                    if content is not None:
                        (repo / "AGENTS.md").write_text(content, encoding="utf-8")
                    status = AUDITOR["inspect_repo"](repo, ["fixture"])
                    self.assertEqual(["INFO"], [item.severity for item in status.findings])
                    self.assertIn("inheritance not verified", status.findings[0].message)
                    self.assertNotIn("CLAUDE.md", status.findings[0].message)

    def test_harness_source_requires_current_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            for content in (None, "Preserve project data."):
                with self.subTest(content=content):
                    if content is not None:
                        (repo / "AGENTS.md").write_text(content, encoding="utf-8")
                    status = AUDITOR["inspect_repo"](repo, ["dot-agent"], require_runtime=True)
                    self.assertEqual(["WARN"], [item.severity for item in status.findings])

    def test_historical_claude_is_not_an_active_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            (repo / "AGENTS.md").write_text("Claude Code and Codex are both primary runtimes.")
            (repo / "CLAUDE.md").write_text("Claude Code and Codex are peer runtimes.")
            status = AUDITOR["inspect_repo"](repo, ["fixture"])
            self.assertEqual([], status.findings)

    def test_skips_exact_temporary_roots_and_descendants_only(self) -> None:
        for path in ("/tmp", "/private/tmp", "/tmp/project", "/private/tmp/project"):
            with self.subTest(path=path):
                self.assertTrue(AUDITOR["should_skip"](Path(path)))
        for path in ("/tmp-project", "/private/tmp-project", "/example/tmp"):
            with self.subTest(path=path):
                self.assertFalse(AUDITOR["should_skip"](Path(path)))

    def test_strict_cli_fails_warnings_not_unverified_inheritance(self) -> None:
        for severity, expected in (("INFO", 0), ("WARN", 1)):
            with self.subTest(severity=severity):
                finding = AUDITOR["RepoFinding"](severity, "/fixture", "fixture")
                repo = AUDITOR["RepoStatus"]("/fixture", [], "unverified", "missing", [finding])
                result = AUDITOR["AuditResult"](checked_repos=[repo])
                with mock.patch.dict(AUDITOR["main"].__globals__, {"audit": lambda **kwargs: result}), \
                     mock.patch("sys.argv", ["repo-instruction-audit.py", "--strict"]), \
                     contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(expected, AUDITOR["main"]())
                self.assertIn("do not verify effective instruction loading", output.getvalue())

    def test_source_mode_remains_strict_with_no_inspected_source(self) -> None:
        with mock.patch.dict(AUDITOR["main"].__globals__, {"audit": lambda **kwargs: AUDITOR["AuditResult"]()}), \
             mock.patch("sys.argv", ["repo-instruction-audit.py", "--strict", "--dot-agent-only"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, AUDITOR["main"]())


if __name__ == "__main__":
    unittest.main()
