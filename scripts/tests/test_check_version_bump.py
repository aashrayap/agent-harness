from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CheckVersionBumpTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / "scripts").mkdir()
        shutil.copy(ROOT / "scripts/check-version-bump.py", self.repo / "scripts")
        self.git("init", "--quiet", "-b", "main")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet",
                 "--allow-empty", "-m", "base")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def base(self, version):
        (self.repo / "VERSION").write_text(f"{version}\n")
        self.git("add", "VERSION")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "v")

    def check(self, version, release=True):
        (self.repo / "VERSION").write_text(f"{version}\n")
        (self.repo / "RELEASES.md").write_text(
            f"# Releases\n\n## {version} — 2026-10-12\nNew: x\nSetup: none\n" if release else "")
        return subprocess.run([sys.executable, str(self.repo / "scripts/check-version-bump.py"), "main"],
                              capture_output=True, text=True)

    def test_first_version_passes_without_base(self):
        self.assertEqual(0, self.check("1.0.0").returncode)

    def test_higher_version_passes(self):
        self.base("1.0.0")
        self.assertEqual(0, self.check("1.0.1").returncode)

    def test_equal_or_lower_version_fails(self):
        self.base("1.2.0")
        self.assertNotEqual(0, self.check("1.2.0").returncode)
        self.assertNotEqual(0, self.check("1.1.9").returncode)

    def test_a_bump_without_a_release_entry_fails(self):
        self.base("1.0.0")
        result = self.check("1.0.1", release=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("RELEASES.md", result.stdout)
        (self.repo / "RELEASES.md").write_text("## 1.0.10 — 2026-10-12\n")
        (self.repo / "VERSION").write_text("1.0.1\n")
        self.assertNotEqual(0, subprocess.run(
            [sys.executable, str(self.repo / "scripts/check-version-bump.py"), "main"],
            capture_output=True, text=True).returncode)

    def test_a_version_already_released_on_the_base_fails(self):
        self.base("1.0.0")
        (self.repo / "RELEASES.md").write_text("## 1.0.1 — 2026-10-12\nNew: x\nSetup: none\n")
        self.git("add", "RELEASES.md")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "r")
        result = self.check("1.0.1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("already taken by RELEASES.md on main", result.stdout)
        self.assertEqual(0, self.check("1.0.2").returncode)

    def test_a_version_already_on_origin_main_fails_even_against_another_base(self):
        self.base("1.0.0")
        self.git("checkout", "--quiet", "-b", "stacked")
        self.base("1.0.1")
        self.git("update-ref", "refs/remotes/origin/main", "stacked")
        self.git("checkout", "--quiet", "main")
        result = self.check("1.0.1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("above 1.0.1", result.stdout)

    def test_a_duplicate_release_entry_fails(self):
        self.base("1.0.0")
        (self.repo / "VERSION").write_text("1.0.1\n")
        entry = "## 1.0.1 — 2026-10-12\nNew: x\nSetup: none\n"
        (self.repo / "RELEASES.md").write_text(entry + entry)
        result = subprocess.run([sys.executable, str(self.repo / "scripts/check-version-bump.py"), "main"],
                                capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("more than one", result.stdout)

    def test_invalid_version_fails(self):
        self.assertNotEqual(0, self.check("v1").returncode)


if __name__ == "__main__":
    unittest.main()
