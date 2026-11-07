from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SkillContracts(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def assert_packaged_provenance(
        self, skill_root: str, upstream_name: str, source_hash: str,
        folder: str = "references",
    ) -> None:
        references = ROOT / skill_root / folder
        provenance = (references / upstream_name).read_text(encoding="utf-8")
        license_text = (references / "LICENSE-MIT.md").read_text(encoding="utf-8")
        self.assertRegex(provenance, r"[0-9a-f]{40}")
        self.assertGreaterEqual(len(re.findall(r"[0-9a-f]{64}", provenance)), 2)
        self.assertIn(source_hash, provenance)
        self.assertIn(
            "bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e",
            provenance,
        )
        self.assertIn("Local changes", provenance)
        self.assertIn("Permission is hereby granted", license_text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', license_text)

    def test_unslop_preserves_authoritative_output_contracts(self) -> None:
        text = self.read("skills/style/unslop/SKILL.md")
        normalized = " ".join(text.split()).lower()
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("human-facing prose", normalized)
        self.assertIn("explicit style and output contracts win", normalized)
        for protected in (
            "bullet-style", "visual", "templates",
            "quotations", "facts", "numbers", "links", "code",
            "source-locked text",
        ):
            self.assertIn(protected, normalized)
        self.assertIn("required outer contract", normalized)
        self.assertIn("stop and report the conflict", normalized)
        self.assert_packaged_provenance(
            "skills/style/unslop", "UPSTREAM.md",
            "181883e539caec8258ec9129e3ba5f133409144a2cbf2aa361158ab94cfc3441",
        )

    def test_ui_claims_need_before_and_after_screenshots(self) -> None:
        skill = " ".join(self.read("skills/engineering/verify/SKILL.md").split())
        template = self.read("template/VERIFY.md")
        self.assertIn("screenshots the current version first", skill)
        self.assertIn("A UI claim without an after screenshot is BLOCKED, not PASS", skill)
        self.assertIn("screenshot the current view first", template)
        self.assertIn("show the owner the after screenshot", template)

    def test_overview_page_starts_from_the_white_template(self) -> None:
        guide = self.read("skills/learning/visual/references/overview-page.md")
        page = self.read("skills/learning/visual/assets/overview-page.html")
        self.assertIn("assets/overview-page.html", guide)
        self.assertIn("max-width:880px", page)
        self.assertIn("--bg:#FFFFFF", page)
        self.assertIn("classDef default fill:#FFFFFF,stroke:#182420,color:#182420", page)
        self.assertIn("<title>", page)
        self.assertIn('name="claude:viewport-fit-sides"', page)
        self.assertIn("max(16px,env(safe-area-inset-left,0px))", page)
        self.assertNotIn("<script src", page)
        self.assertIn("minmax(min(360px,100%),1fr)", page)
        for selector in (".node rect", ".nodeLabel", ".cluster rect", ".edgePath path", ".edgeLabel"):
            self.assertIn("pre.mermaid " + selector, page)

    def test_blast_radius_is_a_verify_mode_not_a_duplicate_skill(self) -> None:
        self.assertFalse(any(ROOT.glob("skills/*/blast-radius/SKILL.md")))
        verify = self.read("skills/engineering/verify/SKILL.md")
        procedure = self.read("skills/engineering/verify/references/blast-radius.md")
        self.assertIn("references/blast-radius.md", verify)
        self.assertIn("Blast Radius", procedure)
        for concept in (
            "changed path", "dependency", "consumer", "configuration",
            "migration", "rollback", "verification matrix",
        ):
            self.assertIn(concept, procedure.lower())
        self.assert_packaged_provenance(
            "skills/engineering/verify", "UPSTREAM-BLAST-RADIUS.md",
            "b060df3ca85803eabbce9fab53f5cc024ca8d784bdde5513c1c1a784947523f8",
        )

    def test_arena_is_an_explicit_bounded_candidate_tournament(self) -> None:
        text = self.read("skills/engineering/arena/SKILL.md")
        normalized = " ".join(text.split()).lower()
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("expensive", normalized)
        self.assertIn("candidate tournament", normalized)
        self.assertIn("isolated", normalized)
        self.assertIn("concurrent writers", normalized)
        self.assertIn("parent reconciliation", normalized)
        self.assertIn("central model/effort policy", normalized)
        self.assertIn("real verification", normalized)
        self.assertIn("stopping conditions", normalized)
        self.assertIn("`$arena`", text)
        self.assertIn("`/arena`", text)
        self.assertIn("per-lane time or cost limit", normalized)
        self.assertIn("monitors every lane", normalized)
        self.assertIn("interrupt a lane", normalized)
        self.assertIn("return blocked", normalized)
        self.assertIn("do not synthesize", normalized)
        self.assertIn("one solution owner", normalized)
        for boundary in ("parallel-plan", "`verify`", "ordinary implementation"):
            self.assertIn(boundary, normalized)
        self.assert_packaged_provenance(
            "skills/engineering/arena", "UPSTREAM.md",
            "a2241e8500a44d9c16bd3260c8c70e28c4bb8a857c33061d42b267057e6f7093",
        )

    def test_deeper_asks_four_questions_and_never_runs_the_rewrite(self) -> None:
        text = self.read("skills/engineering/deeper/SKILL.md")
        normalized = " ".join(text.split()).lower()
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("`/deeper`", text)
        for question in ("missing practice", "raw material",
                         "methods and tools", "outside proof"):
            self.assertIn(question, normalized)
        self.assertIn("do not run the rewritten prompt", normalized)

    def test_show_me_is_explicit_portable_and_bounded(self) -> None:
        text = self.read("skills/learning/show-me/SKILL.md")
        normalized = " ".join(text.split()).lower()
        provenance = self.read("skills/learning/show-me/references/UPSTREAM.md")
        license_text = self.read(
            "skills/learning/show-me/references/LICENSE-MIT.md"
        )
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("`$show-me`", text)
        self.assertIn("`/show-me`", text)
        self.assertIn("smallest view", normalized)
        self.assertIn("use `explain`", normalized)
        self.assertIn("use `visual`", normalized)
        self.assertIn("suggest the exact `$visual` invocation", normalized)
        self.assertIn("do not create an html or durable artifact", normalized)
        self.assertNotIn("write one focused", normalized)
        self.assertNotIn("Bash(open", text)
        self.assertIn("3c2629142c5d437428269b1b722b08c0b87f574d", provenance)
        self.assertIn(
            "bea6da70a58096730b9aeb0bae293ddf4726103a98efc9ce13c481619942a810",
            provenance,
        )
        self.assertIn(
            "5f13c18ea00ea5c1384f41745feeca774079164f7f59a92e4ac0899ad217b26f",
            provenance,
        )
        self.assertIn("Local changes", provenance)
        self.assertIn("Permission is hereby granted", license_text)

    def test_pstack_adaptations_carry_provenance_and_installed_playbooks(self) -> None:
        self.assert_packaged_provenance(
            "skills/engineering/owner-mode", "UPSTREAM.md",
            "c5e6b605f46e5d9fbab31afa7a99d3d50680f2180d1fdfae3a924901bc52d99a", folder=".")
        self.assert_packaged_provenance(
            "skills/engineering/deslop", "UPSTREAM.md",
            "c0fd0383008da45fc78cfac17b9007d62c42f87ad1c8d5c2fb658b1fd01f7c82")
        root = ROOT / "skills/engineering/owner-mode"
        upstream = self.read("skills/engineering/owner-mode/UPSTREAM.md")
        self.assertIn("99743e9c151c8537cbbf1f98bb38f34ef3368453", upstream)
        self.assertIn("5a8b33f83cb62d8cfd5819d6e45447a932b49084", upstream)
        self.assertEqual(["SKILL.md"], [p.name for p in root.rglob("SKILL.md")])
        self.assertFalse((root / "references").exists())
        shipped = sorted(p.name for p in (root / "playbooks").glob("*.md"))
        principles = sorted(p.name for p in (root / "principles").glob("*.md"))
        self.assertEqual(23, len(shipped))
        self.assertEqual(24, len(principles))
        mode = self.read("skills/engineering/owner-mode/SKILL.md")
        self.assertEqual(shipped, sorted(set(re.findall(r"\]\(playbooks/([a-z-]+\.md)[)#]", mode))))
        self.assertEqual(principles, sorted(set(re.findall(r"\]\(principles/([a-z-]+\.md)\)", mode))))
        for path in [root / "SKILL.md", root / "UPSTREAM.md", *root.glob("playbooks/*.md"), *root.glob("principles/*.md")]:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)#:]+\.md)(?:#[^)]*)?\)", text):
                self.assertTrue((path.parent / target).is_file(), f"{path.relative_to(root)} -> {target}")
            cursor_only = re.compile(r"cursor-team-kit|control-ui|control-cli|grok-|poteto-agent|AskQuestion|agent-transcripts|"
                                     r"origin pr|watch-pr|setup-pstack|show-me-your-work|\*\*(how|why|swarm|ketchup|interrogate|architect)\*\*")
            if path.name != "UPSTREAM.md":
                self.assertIsNone(cursor_only.search(text), path.relative_to(root))

    def test_owner_mode_starts_itself_on_repo_work(self) -> None:
        root = "skills/engineering/owner-mode"
        text = self.read(f"{root}/SKILL.md")
        frontmatter = text.split("---\n", 2)[1]
        description = re.search(r"^description: (.+)$", frontmatter, re.M).group(1)
        self.assertNotIn("disable-model-invocation", frontmatter)
        self.assertIn("allow_implicit_invocation: true", self.read(f"{root}/agents/openai.yaml"))
        for trigger in ("repo work", "across files", "shared signature", "design choice",
                        "unknown cause", "small tasks", "chats that change no repo"):
            self.assertIn(trigger, description)
        body = " ".join(text.split())
        self.assertIn("Reading by path also opens explicit-only skills", body)
        triggers = body.split("## Triggers", 1)[1].split("## Principles", 1)[0]
        routed = re.findall(r"→ `([a-z-]+)`", triggers)
        self.assertIn("parallel-plan", routed)
        for name in routed:
            self.assertEqual(1, len(list(ROOT.glob(f"skills/*/{name}/SKILL.md"))), name)
        self.assertIn("copy its steps verbatim into a visible checklist", body)
        self.assertIn("Tick each step as it finishes", body)

    def test_owner_mode_adapter_keeps_merges_and_deletes_with_owner(self) -> None:
        def read(name: str) -> str:
            return " ".join(self.read(f"skills/engineering/owner-mode/{name}").split())
        mode = read("SKILL.md")
        opening = read("playbooks/opening-a-pr.md")
        self.assertIn("Merging a high-risk PR, arming auto-merge and landing anything the gate denies wait for the owner", mode)
        self.assertIn("Every helper runs on `claude-opus-5-5`", mode)
        self.assertIn("`Risk: low` or `Risk: high (<reasons>)`", opening)
        self.assertIn("`verdict.py check --claim` shows it", opening)
        self.assertIn("or any uncommitted file, waits for the owner", read("playbooks/worktree-cleanup.md"))
        self.assertIn("`verdict.py approve` in a separate command before the merge", read("playbooks/shipping.md"))

    def test_catalogs_route_every_added_skill_and_mode(self) -> None:
        mode = self.read("skills/engineering/owner-mode/SKILL.md").lower()
        root_readme = self.read("README.md").lower()
        for name in ("unslop", "arena", "show-me"):
            self.assertIn(name, mode)
            self.assertIn(name, root_readme)
        authoring = self.read("skills/README.md").lower()
        self.assertIn("third-party licenses/hashes", authoring)

    def test_setup_installs_exact_runtime_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw).resolve() / "home"
            checkout = home / ".dot-agent"
            shutil.copytree(
                ROOT,
                checkout,
                ignore=shutil.ignore_patterns(
                    ".git", "state", "__pycache__", "*.pyc"
                ),
            )
            subprocess.run(
                ["git", "init", "--quiet", str(checkout)],
                check=True,
                capture_output=True,
                text=True,
            )
            environment = dict(os.environ)
            environment["HOME"] = str(home)
            result = subprocess.run(
                ["bash", str(checkout / "setup.sh"), "--runtime", "all"],
                cwd=checkout,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)

            source_roots = {
                "unslop": checkout / "skills/style/unslop",
                "arena": checkout / "skills/engineering/arena",
                "verify": checkout / "skills/engineering/verify",
                "owner-mode": checkout / "skills/engineering/owner-mode",
                "deslop": checkout / "skills/engineering/deslop",
            }
            for name, source_root in source_roots.items():
                source_files = [source_root / "SKILL.md", *source_root.glob("*.md")]
                for folder in ("references", "playbooks", "principles"):
                    source_files.extend(
                        path for path in (source_root / folder).rglob("*")
                        if path.is_file()
                    )
                for source in source_files:
                    relative = source.relative_to(source_root)
                    for runtime in (".codex", ".claude"):
                        installed = home / runtime / "skills" / name / relative
                        self.assertEqual(
                            source.read_bytes(), installed.read_bytes(),
                            f"{runtime}/skills/{name}/{relative}",
                        )


if __name__ == "__main__":
    unittest.main()
