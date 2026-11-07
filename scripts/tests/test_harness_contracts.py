from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).parents[2]


class HarnessContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text()

    def normalized(self, relative):
        return " ".join(self.read(relative).lower().split())

    def test_one_working_record_and_source_boundaries(self):
        contract = self.normalized("docs/harness-runtime-reference.md")
        self.assertIn("reuse one working record", self.normalized("AGENTS.md"))
        self.assertIn("small tasks need no document", self.normalized("AGENTS.md"))
        for concept in ("~/.dot-agent", "machine-local",
                        "claude code conversations"):
            self.assertIn(concept, contract)
        self.assertIn("separate", contract)
        self.assertIn("harness update", contract)
        self.assertIn("work sync", contract)

    def test_parallel_plan_remains_distinct_from_visual_and_execution(self):
        text = self.normalized("skills/engineering/parallel-plan/SKILL.md")
        for concept in ("rendered inline diagram", "table", "model", "effort", "sequence",
                        "dependencies", "parent", "plan"):
            self.assertIn(concept, text)
        self.assertTrue((ROOT / "skills/learning/visual/SKILL.md").is_file())
        self.assertIn("disable-model-invocation: true",
                      self.read("skills/engineering/parallel-plan/SKILL.md"))

    def test_parallel_plan_names_lanes_in_plain_words_in_diagram_and_table(self):
        text = self.read("skills/engineering/parallel-plan/SKILL.md")
        normalized = " ".join(text.split())
        for concept in ("plain words", "diagram node", "table row", "Never a letter or code name"):
            self.assertIn(concept, normalized)
        outside_rule = re.sub(r"\(Lane A,[^)]*\)", "", normalized)
        self.assertNotRegex(outside_rule, r"\b(?:Lane|Track|Wave|Worker) [A-Z0-9]\b|\b[WL]\d\b")
        lanes = [line.split("|")[1].strip() for line in text.splitlines()
                 if line.startswith("| ") and not line.startswith("| Lane |")]
        self.assertTrue(lanes)
        for lane in lanes:
            self.assertGreaterEqual(len(lane.split()), 2, lane)

    def test_teach_phrase_echo_is_bounded_and_chat_native(self):
        teach = self.read("skills/learning/teach/SKILL.md")
        lesson = self.read("skills/learning/teach/references/PHRASE-ECHO.md")
        normalized_teach = " ".join(teach.split())
        normalized_lesson = " ".join(lesson.split())

        self.assertIn("PHRASE-ECHO.md", teach)
        self.assertIn("instead of creating a teaching workspace", normalized_teach)
        self.assertIn("explicit `$teach` mode", normalized_lesson)
        self.assertIn("removing duplicates and stopping at three", normalized_lesson)
        for review in ("phrase IDs identified as missed", "`S-1`", "`S-3`", "`S-7`"):
            self.assertIn(review, lesson)
        self.assertIn("sessions whose receipt says `new: none`", normalized_lesson)
        self.assertIn("before showing the target language", normalized_lesson)
        self.assertIn("one-message self-check", normalized_lesson)
        self.assertIn("add no new phrase", normalized_lesson)
        self.assertIn("at most one new phrase", normalized_lesson)
        self.assertIn("once while looking and once from memory", normalized_lesson)
        self.assertIn("missed {phrase IDs}", normalized_lesson)
        self.assertIn("actual phrase IDs", lesson)
        self.assertIn("emit one finalized line", normalized_lesson)
        self.assertIn("immediately following owner result together", normalized_lesson)
        self.assertIn("never infer success or failure", normalized_lesson)
        self.assertIn("warm-up as unscored", normalized_lesson)
        self.assertIn("first result uses `recalled 0/0`", normalized_lesson)
        self.assertIn("not verified mastery", normalized_lesson)
        self.assertIn("do not claim measured elapsed time", normalized_lesson)
        self.assertIn("missed calendar day creates no backlog", normalized_lesson)
        self.assertIn("Do not create `MISSION.md`", normalized_lesson)
        self.assertIn("only after the owner separately asks", normalized_lesson)
        self.assertIn("Receipt: session S", lesson)
        for requirement in (
            "standard target-language spelling", "Mark stress", "surface-form contrast",
            "real conversation", "spoken fallback", "compact receipts",
            "never claim to have evaluated",
        ):
            self.assertIn(requirement, lesson)

    def test_current_docs_never_assert_old_refresh_schedule_is_active(self):
        text = self.normalized("README.md")
        self.assertNotIn("the active 6 a.m.-plus-hourly", text)

    def test_no_file_says_every_merge_waits_for_owner(self):
        stale = re.compile(r"merging waits for the owner|merging a pr needs the owner|merge gate: the owner's yes"
                           r"|no hook checks merges|merges a pr\s+only after the owner", re.I)
        for relative in ("README.md", "docs/harness-runtime-reference.md",
                         "skills/engineering/owner-mode/SKILL.md",
                         "skills/engineering/owner-mode/playbooks/opening-a-pr.md",
                         "skills/engineering/verify/SKILL.md", "claude/hooks/no-push-to-main.py"):
            self.assertIsNone(stale.search(self.read(relative)), relative)

    def test_repository_markdown_links_resolve(self):
        for relative in ("README.md", "skills/README.md", "template/README.md",
                         "docs/harness-runtime-reference.md"):
            for target in re.findall(r"\]\(([^)]+)\)", self.read(relative)):
                if "://" in target or target.startswith("#"):
                    continue
                target = target.split("#", 1)[0]
                self.assertTrue((ROOT / relative).parent.joinpath(target).exists(),
                                f"{relative}: {target}")

    def test_work_sync_is_not_executable_update(self):
        self.assertIn("work sync and executable harness updates are separate operations",
                      self.normalized("AGENTS.md"))
        self.assertFalse((ROOT / "skills/personal/home").exists())
        self.assertIn("an open pr is not installed production",
                      self.normalized("docs/harness-runtime-reference.md"))


    def test_ci_installs_claude_twice_into_a_fresh_home_and_verifies(self):
        workflow = self.read(".github/workflows/verify-profiles.yml")
        job = workflow.split("  install-claude:\n", 1)[1].split("\n  install:\n", 1)[0]
        steps = [line.strip() for line in job.splitlines()]
        first = steps.index("./setup.sh --runtime claude")
        second = steps.index("./setup.sh")
        self.assertLess(first, second)
        self.assertIn('export HOME="$RUNNER_TEMP/home-claude"', steps[:first])
        self.assertIn('diff "$RUNNER_TEMP/first" "$RUNNER_TEMP/second"', steps[second:])
        self.assertIn("python3 scripts/verify-profile.py --runtime claude", steps[second:])

    def test_the_mermaid_widget_ties_every_color_to_a_theme_token(self):
        def problems(page):
            css = "".join(re.findall(r"<style>(.*?)</style>", page, re.S))
            found = [f"bare color {value}" for value in re.findall(
                r"(?:fill|stroke|color|background):\s*([^;}]+)", css) if not value.startswith("var(--")]
            for selector in ("#m .node rect", "#m .nodeLabel", "#m .edgeLabel", "#m .done rect",
                             "#m .todo rect", "#m .problem rect"):
                if selector not in css:
                    found.append(f"no theme rule for {selector}")
            if re.search(r"primaryColor|themeCSS|%%\{init", page):
                found.append("a Mermaid theme override")
            return found
        self.assertEqual([], problems(self.read("docs/diagrams/mermaid-widget.html")))
        before_a810b9f = ("<div id='m'></div><script type='module'>mermaid.initialize({theme:'base',"
                          "themeVariables:{primaryColor:'#e8f0fe',primaryTextColor:'#ffffff'}});</script>")
        self.assertTrue(problems(before_a810b9f))
        self.assertTrue(problems(self.read("docs/diagrams/mermaid-widget.html").replace(
            "fill:var(--surface-1,#f1efe8)", "fill:#f1efe8")))

    def test_scripts_check_runs_every_mod_test(self):
        check = self.read("scripts/check")
        self.assertIn("claude plugin test", check)
        self.assertIn("claude/mods/*/", check)
        self.assertIn("rule?.text.endsWith", self.read("claude/mods/mermaid-style/hooks/register.test.ts"))

    def test_the_mermaid_widget_alone_carries_the_legend_and_zoom(self):
        page = self.read("docs/diagrams/mermaid-widget.html")
        for piece in ("zoomAt", "id=\"legend\"", "done: 'working today'",
                      "todo: 'being built / planned'", "problem: 'broken or blocking'",
                      "m.querySelector('svg .' + k)"):
            self.assertIn(piece, page)
        mod = ROOT / "claude/mods/mermaid-style/hooks"
        self.assertEqual(["hooks.json", "register.test.ts", "register.ts"], sorted(p.name for p in mod.iterdir()))
        self.assertNotIn("import", self.read("claude/mods/mermaid-style/hooks/register.ts").split("\n", 1)[1])

    def test_agents_md_names_every_high_risk_category_the_gate_uses(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("verdict", ROOT / "skills/engineering/verify/scripts/verdict.py")
        verdict = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verdict)
        pause = self.normalized("AGENTS.md").split("## always pause", 1)[1].split("the owner approving", 1)[0]
        for label, _ in verdict.HIGH_RISK:
            self.assertIn(label.lower(), pause, label)

if __name__ == "__main__":
    unittest.main()
