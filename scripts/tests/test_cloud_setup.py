import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETUP = ROOT / "scripts/cloud-setup.sh"
VERSION = (ROOT / "VERSION").read_text().strip()


class CloudSetupTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        self.claude = self.home / ".claude"

    def run_setup(self, *args, env=None):
        return subprocess.run(["bash", str(SETUP), *args], capture_output=True, text=True,
                              env={**os.environ, "HOME": str(self.home), **(env or {})})

    def test_setup_installs_user_level_skills_idempotently(self):
        first = self.run_setup()
        self.assertEqual(0, first.returncode, first.stdout)
        manifest = (self.claude / "dot-agent-cloud").read_text()
        self.assertTrue(manifest.startswith(f"version {VERSION}\n"))
        self.assertIn("skill verify\n", manifest)
        self.assertTrue((self.claude / "skills/verify/scripts/verdict.py").is_file())
        self.assertEqual(0, self.run_setup().returncode)
        self.assertEqual(manifest, (self.claude / "dot-agent-cloud").read_text())
        self.assertEqual(0, self.run_setup("--check").returncode)

    def test_setup_honors_claude_config_dir_and_an_explicit_home(self):
        config = self.home / "config"
        self.assertEqual(0, self.run_setup(env={"CLAUDE_CONFIG_DIR": str(config)}).returncode)
        self.assertTrue((config / "skills/verify/SKILL.md").is_file())
        explicit = self.home / "explicit"
        self.assertEqual(0, self.run_setup(str(explicit)).returncode)
        self.assertTrue((explicit / "skills/verify/SKILL.md").is_file())
        self.assertFalse(self.claude.exists())

    def test_check_fails_when_the_delivered_copy_is_missing_older_or_edited(self):
        self.assertIn("no dot-agent skills", self.run_setup("--check").stdout)
        self.run_setup()
        manifest = self.claude / "dot-agent-cloud"
        manifest.write_text(manifest.read_text().replace(f"version {VERSION}", "version 0.0.1"))
        old = self.run_setup("--check")
        self.assertEqual(1, old.returncode)
        self.assertIn(f"dot-agent 0.0.1, older than {VERSION}", old.stdout)
        self.run_setup()
        skill = self.claude / "skills/verify/SKILL.md"
        skill.write_text(skill.read_text() + "\nedited\n")
        edited = self.run_setup("--check")
        self.assertEqual(1, edited.returncode)
        self.assertIn("skill verify differs", edited.stdout)
        self.assertEqual(0, self.run_setup().returncode)

    def test_setup_never_overwrites_a_skill_it_did_not_install(self):
        own = self.claude / "skills/verify/SKILL.md"
        own.parent.mkdir(parents=True)
        own.write_text("someone else's verify\n")
        result = self.run_setup()
        self.assertEqual(1, result.returncode)
        self.assertIn("is not dot-agent's", result.stdout)
        self.assertEqual("someone else's verify\n", own.read_text())


if __name__ == "__main__":
    unittest.main()
