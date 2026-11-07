import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PIN = "9c9f36ccd3995266cd675468af71639c8dde1ec5"


class PlanningSkillContracts(unittest.TestCase):
    def run_manifest_validator(
        self,
        skill_text: str,
        manifest_text: str | None,
        *,
        runtime_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            scripts = root / "scripts"
            skill = root / "skills/engineering/example"
            scripts.mkdir(parents=True)
            skill.mkdir(parents=True)
            shutil.copyfile(
                ROOT / "scripts/validate-skill-manifests.py",
                scripts / "validate-skill-manifests.py",
            )
            (skill / "SKILL.md").write_text(skill_text, encoding="utf-8")
            if runtime_text is not None:
                runtime = skill / "codex"
                runtime.mkdir()
                (runtime / "SKILL.md").write_text(runtime_text, encoding="utf-8")
            if manifest_text is not None:
                agents = skill / "agents"
                agents.mkdir()
                (agents / "openai.yaml").write_text(
                    manifest_text, encoding="utf-8"
                )
            return subprocess.run(
                ["python3", str(scripts / "validate-skill-manifests.py")],
                cwd=root,
                capture_output=True,
                text=True,
            )

    def test_manifest_validator_rejects_noncanonical_boolean_scalar(self):
        result = self.run_manifest_validator(
            "---\nname: example\ndescription: Example skill.\n---\n",
            'policy:\n  allow_implicit_invocation: "true"\n',
        )

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("agents/openai.yaml must match the canonical schema", result.stdout)

    def test_manifest_validator_accepts_canonical_whole_document(self):
        result = self.run_manifest_validator(
            "---\nname: example\ndescription: Example skill.\n---\n",
            "interface:\n"
            '  display_name: "Example"\n'
            '  short_description: "Example skill for testing"\n'
            '  default_prompt: "Use $example."\n'
            "policy:\n"
            "  allow_implicit_invocation: true\n",
        )

        self.assertEqual(0, result.returncode, result.stdout)

    def test_manifest_validator_rejects_runtime_invocation_policy_mismatch(self):
        result = self.run_manifest_validator(
            "---\nname: example\ndescription: Example skill.\n"
            "disable-model-invocation: true\n---\n",
            "policy:\n  allow_implicit_invocation: false\n",
            runtime_text=(
                "---\nname: example\ndescription: Runtime example.\n---\n"
            ),
        )

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(
            "codex/SKILL.md invocation policy must match root SKILL.md",
            result.stdout,
        )

    def test_manifest_validator_rejects_invalid_interface_contracts(self):
        skill = "---\nname: example\ndescription: Example skill.\n---\n"
        policy = "policy:\n  allow_implicit_invocation: true\n"
        invalid = (
            "interface:\n"
            '  display_name: "Example"\n'
            '  short_description: "x"\n'
            + policy,
            "interface:\n"
            '  display_name: "Example"\n'
            '  short_description: "Example skill for testing"\n'
            '  default_prompt: "Use this example skill."\n'
            + policy,
            "interface:\n"
            '  display_name: "Example"\n'
            '  short_description: "Example skill for testing"\n'
            '  default_prompt: "Use $example-wrong."\n'
            + policy,
            "interface:\n"
            '  display_name: "Example"\n'
            '  short_description: "Example skill for testing"\n'
            '  default_prompt: "Use $example2."\n'
            + policy,
            "interface:\n"
            '  display_name: "Example"\n'
            '  short_description: "Example skill for testing"\n'
            '  default_prompt: "Use $example_wrong."\n'
            + policy,
        )
        for manifest in invalid:
            with self.subTest(manifest=manifest):
                result = self.run_manifest_validator(skill, manifest)
                self.assertEqual(1, result.returncode, result.stdout)
                self.assertIn(
                    "agents/openai.yaml must match the canonical schema",
                    result.stdout,
                )

    def test_manifest_validator_rejects_ambiguous_source_invocation_policy(self):
        declarations = (
            "disable-model-invocation: true\ndisable-model-invocation: false",
            "disable-model-invocation: false",
            'disable-model-invocation: "true"',
            '"disable-model-invocation": true',
            "disable-model-invocation : true",
            "  disable-model-invocation: true",
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                result = self.run_manifest_validator(
                    "---\n"
                    "name: example\n"
                    "description: Example skill.\n"
                    f"{declaration}\n"
                    "---\n",
                    "policy:\n  allow_implicit_invocation: false\n",
                )

                self.assertEqual(1, result.returncode, result.stdout)
                self.assertIn(
                    "SKILL.md invocation policy must be canonical",
                    result.stdout,
                )

    def test_all_active_skills_have_the_approved_openai_policy_matrix(self):
        policies: list[bool] = []
        for skill_md in sorted((ROOT / "skills").glob("*/*/SKILL.md")):
            manifest = skill_md.parent / "agents/openai.yaml"
            match = re.fullmatch(
                r"(?:interface:\n"
                r'  display_name: "(?:[^"\\]|\\.)*"\n'
                r'  short_description: "(?:[^"\\]|\\.)*"\n'
                r'(?:  default_prompt: "(?:[^"\\]|\\.)*"\n)?'
                r")?policy:\n"
                r"  allow_implicit_invocation: (true|false)\n",
                manifest.read_text(encoding="utf-8"),
            )
            self.assertIsNotNone(match, str(manifest.relative_to(ROOT)))
            implicit = match.group(1) == "true"
            explicit = "disable-model-invocation: true" in re.match(
                r"^---\n(.*?)\n---\n",
                skill_md.read_text(encoding="utf-8"),
                flags=re.DOTALL,
            ).group(1).splitlines()
            self.assertEqual(not explicit, implicit, skill_md.parent.name)
            policies.append(implicit)

        self.assertTrue(policies)

    def test_manifest_validator_requires_openai_manifest(self):
        result = self.run_manifest_validator(
            "---\nname: example\ndescription: Example skill.\n---\n",
            None,
        )

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("agents/openai.yaml is required", result.stdout)

    def test_manifest_validator_rejects_noncanonical_whole_documents(self):
        skill = "---\nname: example\ndescription: Example skill.\n---\n"
        canonical = "policy:\n  allow_implicit_invocation: true\n"
        invalid = {
            "nested": "policy:\n  child:\n    allow_implicit_invocation: true\n",
            "cross-section": "policy:\n  other: true\nother:\n  allow_implicit_invocation: true\n",
            "duplicate-value": canonical + "  allow_implicit_invocation: true\n",
            "duplicate-policy": canonical + "policy:\n  allow_implicit_invocation: true\n",
            "multiline": "policy:\n  allow_implicit_invocation:\n    true\n",
            "quoted-boolean": 'policy:\n  allow_implicit_invocation: "true"\n',
            "uppercase-boolean": "policy:\n  allow_implicit_invocation: True\n",
            "numeric-boolean": "policy:\n  allow_implicit_invocation: 1\n",
            "null-boolean": "policy:\n  allow_implicit_invocation: null\n",
            "cross-runtime-mismatch": "policy:\n  allow_implicit_invocation: false\n",
            "quoted-policy-key": '"policy":\n  allow_implicit_invocation: true\n',
            "spaced-policy-key": "policy :\n  allow_implicit_invocation: true\n",
            "quoted-value-key": 'policy:\n  "allow_implicit_invocation": true\n',
            "spaced-value-key": "policy:\n  allow_implicit_invocation : true\n",
            "first-document-marker": "---\n" + canonical,
            "second-document": canonical + "---\n" + canonical,
            "document-end": canonical + "...\n",
            "flow-mapping": "policy: {allow_implicit_invocation: true}\n",
            "collection": "policy:\n  allow_implicit_invocation: [true]\n",
            "unknown-top-level": canonical + "unknown: true\n",
            "unknown-policy-child": canonical + "  unknown: true\n",
            "trailing-comment": canonical + "# comment\n",
            "trailing-blank-line": canonical + "\n",
            "missing-final-newline": canonical.rstrip("\n"),
            "crlf": canonical.replace("\n", "\r\n"),
            "malformed-interface-scalar": (
                'interface:\n  display_name: "unterminated\n'
                '  short_description: "Example"\n' + canonical
            ),
            "interface-collection": (
                "interface:\n  display_name: [Example]\n"
                '  short_description: "Example"\n' + canonical
            ),
            "invalid-unicode-scalar": (
                'interface:\n  display_name: "\\ud800"\n'
                '  short_description: "Example"\n' + canonical
            ),
            "unknown-interface-key": (
                'interface:\n  display_name: "Example"\n'
                '  short_description: "Example"\n'
                '  icon: "icon.png"\n' + canonical
            ),
        }

        for name, manifest in invalid.items():
            with self.subTest(name=name):
                result = self.run_manifest_validator(skill, manifest)
                self.assertEqual(1, result.returncode, result.stdout)
                self.assertIn(
                    "agents/openai.yaml must match the canonical schema",
                    result.stdout,
                )

    def test_third_party_payloads_have_pinned_provenance_and_license(self):
        agent_hashes = {
            "grill-me": "1411d7df7d99b7e621a1ff8283c8133cc2464be63d064e52d8ce169c6800ee9b",
            "prototype": "5af65e43ab41a350436697b81e27b7f848d36782043b73c322bb2c9fa9cc55dc",
        }
        for name in ("grill-me", "prototype"):
            reference = ROOT / "skills/engineering" / name / "references" / \
                "UPSTREAM.md"
            text = reference.read_text()
            self.assertIn(PIN, text, name)
            self.assertRegex(text, r"[0-9a-f]{64}", name)
            self.assertIn(
                "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5",
                text, name)
            if name in agent_hashes:
                self.assertIn(agent_hashes[name], text, name)
                self.assertTrue((reference.parents[1] / "agents/openai.yaml").is_file())
            self.assertIn("Local changes", text.replace("This adaptation", "Local changes"), name)
            if "complete upstream license" in text:
                license_text = (reference.parent / "LICENSE-MIT.md").read_text()
            else:
                license_text = text
            self.assertIn("Permission is hereby granted", license_text, name)
            self.assertIn("THE SOFTWARE IS PROVIDED \"AS IS\"", license_text, name)

    def test_agents_metadata_is_a_supported_runtime_payload(self):
        setup = (ROOT / "scripts/lib/install-skills.sh").read_text()
        audit = (ROOT / "scripts/skill-instruction-audit.py").read_text()
        verifier = (ROOT / "scripts/verify-profile.py").read_text()
        self.assertIn("scripts assets references shared agents", setup)
        self.assertIn('"shared", "agents"', audit)
        self.assertIn('"shared", "agents"', verifier)

    def test_grill_me_stays_explicit_and_interview_only(self):
        skill = (ROOT / "skills/engineering/grill-me/SKILL.md").read_text()
        metadata = (ROOT / "skills/engineering/grill-me/agents/openai.yaml").read_text()
        self.assertIn("disable-model-invocation: true", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("interview-only request never implements the plan", skill)
        self.assertNotIn("Never implement the plan before", skill)

        active = [
            path.parent.name
            for path in (ROOT / "skills").glob("*/*/SKILL.md")
            if "grill" in path.parent.name
        ]
        self.assertEqual(["grill-me"], active)


if __name__ == "__main__":
    unittest.main()
