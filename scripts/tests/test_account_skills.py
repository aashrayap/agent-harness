from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/account-skills.py"
spec = importlib.util.spec_from_file_location("account_skills", SCRIPT)
skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skills)


def run(*args):
    result = subprocess.run([sys.executable, str(SCRIPT), *args, "--json"], capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout)


class AccountSkillsTests(unittest.TestCase):
    def test_account_skill_frontmatter_keeps_only_allowed_fields_and_folds_the_argument_hint(self):
        text, report = skills.convert("demo", "---\nname: demo\ndescription: >\n  Does a thing: well.\n"
                                              "argument-hint: \"<topic>\"\r\ndisable-model-invocation: true\n---\n\nBody\n")
        fields, body = skills.split_frontmatter(text)
        self.assertEqual(["name", "description"], list(fields))
        self.assertEqual('"Does a thing: well. Arguments: topic"', fields["description"])
        self.assertEqual("\nBody\n", body)
        self.assertEqual(["argument-hint", "disable-model-invocation"], report["dropped"])
        self.assertTrue(report["argument_hint_folded"] and report["loses_manual_only"])
        self.assertEqual([], report["problems"])

    def test_account_skill_names_and_long_descriptions_are_flagged(self):
        self.assertTrue(skills.convert("demo", "---\nname: other\ndescription: x\n---\n")[1]["problems"])
        long = "x" * (skills.MAX_DESCRIPTION + 1)
        self.assertTrue(skills.convert("demo", f"---\nname: demo\ndescription: {long}\n---\n")[1]["problems"])
        self.assertTrue(skills.convert("claude-x", "---\nname: claude-x\ndescription: x\n---\n")[1]["problems"])
        self.assertTrue(skills.convert("demo", "---\nname: demo\ndescription: a <tag>\n---\n")[1]["problems"])
        near = "x" * (skills.MAX_DESCRIPTION - 5)
        text, report = skills.convert("demo", f"---\nname: demo\ndescription: {near}\nargument-hint: <a long hint>\n---\n")
        self.assertFalse(report["argument_hint_folded"])
        self.assertEqual([], report["problems"])

    def test_every_built_dot_agent_skill_uploads_and_mac_only_skills_are_skipped_with_a_reason(self):
        manifest, zips = skills.build()
        self.assertEqual(sorted(skills.SKIP), [skill["name"] for skill in manifest["skipped"]])
        self.assertTrue(all(skill["why"] for skill in manifest["skipped"]))
        self.assertEqual([], [p for skill in manifest["skills"] for p in skill["problems"]])
        for name, data in zips.items():
            with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
                handle.write(data)
                handle.flush()
                with zipfile.ZipFile(handle.name) as zipped:
                    self.assertTrue(all(entry.startswith(f"{name}/") for entry in zipped.namelist()), name)
                    fields, _ = skills.split_frontmatter(zipped.read(f"{name}/SKILL.md").decode())
            self.assertLessEqual(set(fields), set(skills.ALLOWED), name)
            self.assertEqual(json.dumps(name), fields["name"])
        self.assertEqual(zips, skills.build()[1])

    def test_check_says_when_the_uploaded_copies_fall_behind_dot_agent(self):
        with tempfile.TemporaryDirectory() as out:
            code, result = run("check", "--out", out)
            self.assertEqual(1, code)
            self.assertIn("nothing recorded as uploaded", result["behind"][0])
            self.assertEqual(1, run("record", "--out", out)[0])
            self.assertEqual(0, run("build", "--out", out)[0])
            self.assertEqual(0, run("record", "--out", out)[0])
            self.assertEqual((0, []), (run("check", "--out", out)[0], run("check", "--out", out)[1]["behind"]))
            uploaded = Path(out) / "uploaded.json"
            old = json.loads(uploaded.read_text())
            old["version"] = "0.0.1"
            uploaded.write_text(json.dumps(old))
            code, result = run("check", "--out", out)
            self.assertEqual((0, "0.0.1"), (code, result["uploaded_version"]))
            old["skills"][0]["sha256"] = "0" * 64
            uploaded.write_text(json.dumps(old))
            code, result = run("check", "--out", out)
            self.assertEqual(1, code)
            self.assertIn(f"{old['skills'][0]['name']} changed since it was uploaded", result["behind"])


if __name__ == "__main__":
    unittest.main()
