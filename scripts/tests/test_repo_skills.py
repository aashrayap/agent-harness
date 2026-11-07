import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/build-repo-skills.sh"


class RepoSkillsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.target = self.tmp / "skills"
        self.assertEqual(0, self.build().returncode)

    def build(self, *args):
        env = {**os.environ, "REPO_SKILLS_TARGET": str(self.target)}
        return subprocess.run(["bash", str(BUILDER), *args], env=env, capture_output=True, text=True)

    def assert_stale(self):
        result = self.build("--check")
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("run scripts/build-repo-skills.sh", result.stdout)

    def test_fresh_build_passes_the_check(self):
        self.assertEqual(0, self.build("--check").returncode)

    def test_every_source_skill_is_built_without_codex_metadata(self):
        sources = {p.parent.name for p in (ROOT / "skills").glob("*/*/SKILL.md")}
        self.assertEqual(sources, {p.parent.name for p in self.target.glob("*/SKILL.md")})
        self.assertEqual([], list(self.target.rglob("openai.yaml")))
        self.assertTrue((self.target / "verify/scripts/verdict.py").is_file())

    def test_edited_copy_fails_the_check(self):
        skill = self.target / "verify/SKILL.md"
        skill.write_text(skill.read_text() + "\nstale line\n")
        self.assert_stale()

    def test_missing_skill_fails_the_check(self):
        shutil.rmtree(self.target / "verify")
        self.assert_stale()

    def test_extra_file_fails_the_check(self):
        (self.target / "verify/extra.md").write_text("not from source\n")
        self.assert_stale()

    def test_bytecode_cache_is_not_drift(self):
        cache = self.target / "verify/scripts/__pycache__"
        cache.mkdir()
        (cache / "verdict.cpython-313.pyc").write_bytes(b"compiled")
        self.assertEqual(0, self.build("--check").returncode)


    def test_lost_executable_bit_fails_the_check(self):
        executables = [p for p in self.target.rglob("*") if p.is_file() and os.access(p, os.X_OK)]
        self.assertTrue(executables)
        executables[0].chmod(0o644)
        self.assert_stale()

    def test_rebuild_refuses_to_wipe_uncommitted_edits_in_the_copy(self):
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        subprocess.run(["git", "-C", str(self.tmp), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.tmp), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "copy"], check=True)
        skill = self.target / "verify/SKILL.md"
        skill.write_text(skill.read_text() + "\nedited by hand\n")
        result = self.build()
        self.assertEqual(1, result.returncode)
        self.assertIn("uncommitted changes", result.stdout)
        self.assertIn("edited by hand", skill.read_text())


if __name__ == "__main__":
    unittest.main()
