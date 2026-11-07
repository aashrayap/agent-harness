from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/owner-mode-upstream.py"
SKILL = Path("skills/engineering/owner-mode")


class OwnerModeUpstream(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / SKILL, self.root / SKILL)

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--root", str(self.root)],
            capture_output=True, text=True, check=False)

    def test_the_shipped_manifest_passes(self) -> None:
        result = self.run_script("--check")
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn("cover 49 files", result.stdout)

    def test_an_unrecorded_playbook_fails(self) -> None:
        (self.root / SKILL / "playbooks/local.md").write_text("x\n", encoding="utf-8")
        (self.root / SKILL / "principles/fix-root-causes.md").unlink()
        nested = self.root / SKILL / "playbooks/nested"
        nested.mkdir()
        (nested / "SKILL.md").write_text("x\n", encoding="utf-8")
        result = self.run_script("--check")
        self.assertEqual(1, result.returncode)
        self.assertIn("unrecorded: playbooks/local.md", result.stdout)
        self.assertIn("missing: principles/fix-root-causes.md", result.stdout)
        self.assertIn("nested skill: playbooks/nested/SKILL.md", result.stdout)

    def test_compare_sorts_upstream_files_by_recorded_hash(self) -> None:
        upstream = self.root / SKILL / "UPSTREAM.md"
        text = upstream.read_text(encoding="utf-8")
        same, changed = b"same\n", b"changed\n"
        for name, data in (("feature", same), ("bug-fix", b"pinned\n")):
            text = re.sub(
                rf"(\| `pstack/skills/poteto-mode/playbooks/{name}\.md` \| `[0-9a-f]{{40}}` \| `)[0-9a-f]{{64}}",
                lambda m: m.group(1) + hashlib.sha256(data).hexdigest(), text)
        upstream.write_text(text, encoding="utf-8")
        port = self.root / "port"
        (port / "skills/poteto-mode/playbooks").mkdir(parents=True)
        (port / "skills/poteto-mode/playbooks/feature.md").write_bytes(same)
        (port / "skills/poteto-mode/playbooks/bug-fix.md").write_bytes(changed)
        (port / "skills/poteto-mode/playbooks/brand-new.md").write_bytes(same)
        result = self.run_script("--compare", str(port))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("unchanged: skills/poteto-mode/playbooks/feature.md", result.stdout)
        self.assertIn("changed: skills/poteto-mode/playbooks/bug-fix.md (ours: playbooks/bug-fix.md)", result.stdout)
        self.assertIn("+changed", result.stdout)
        self.assertIn("new there: skills/poteto-mode/playbooks/brand-new.md", result.stdout)
        self.assertIn("gone there: skills/principle-fix-root-causes/SKILL.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
