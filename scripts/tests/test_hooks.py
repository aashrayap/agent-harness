from pathlib import Path
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "claude/hooks/no-push-to-main.py"
spec = importlib.util.spec_from_file_location("no_push_to_main", HOOK)
push_hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(push_hook)
GATE = ROOT / "claude/hooks/merge-gate.py"
gate_spec = importlib.util.spec_from_file_location("merge_gate", GATE)
merge_gate = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(merge_gate)


def load_hook(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / f"claude/hooks/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


send_hook = load_hook("ask-before-send")
outcome_hook = load_hook("outcome-line")


def bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class PushToMainHookTests(unittest.TestCase):
    def denied(self, event):
        decision = push_hook.decide(event)
        return bool(decision) and decision["hookSpecificOutput"]["permissionDecision"] == "deny"

    def repo_on(self, raw, branch):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        for args in (["init", "-q", "-b", branch], ["commit", "-q", "--allow-empty", "-m", "x"]):
            subprocess.run(["git", "-C", raw, *args], check=True, env=env)

    def test_a_push_that_lands_on_the_checked_out_main_is_denied(self):
        with tempfile.TemporaryDirectory() as raw:
            self.repo_on(raw, "main")
            for command in ("git push", "git push origin", "git push origin HEAD", "git push origin @", "git push -f",
                            "git push --force origin HEAD", "git push 2>&1", "git push origin >log", "git push -u origin",
                            "git push 2>&1 | tail -3", "git push origin 2>&1 | grep x", "true; git push 2>&1",
                            "git push\ngh pr view", "git push origin +main", "git push origin +refs/heads/main",
                            "sudo git push", "FOO=1 git push", "git push origin \\\n  HEAD",
                            "git push --tags origin HEAD", "git push origin HEAD --tags"):
                self.assertTrue(self.denied(dict(bash(command), cwd=raw)), command)
            os.mkdir(Path(raw, "sub"))
            for command in ("cd sub && git push 2>&1", "cd sub && git push origin 2>&1 | tail -3", "cd sub\ngit push"):
                self.assertTrue(self.denied(dict(bash(command), cwd=raw)), command)
            for command in ("git push origin feature", "git push origin HEAD:feature", "git push origin --tags",
                            "git push --tags", "git push --dry-run", "git push -n origin HEAD", "echo git push",
                            "man git push", "git push origin --delete old", "git log -1 'a\nb'; git push origin x"):
                self.assertFalse(self.denied(dict(bash(command), cwd=raw)), command)
        with tempfile.TemporaryDirectory() as raw:
            self.repo_on(raw, "feature")
            for command in ("git push", "git push -u origin HEAD", "git push origin", "git push origin HEAD\ngit log --all",
                            "echo git push --all"):
                self.assertFalse(self.denied(dict(bash(command), cwd=raw)), command)
            for command in ("git push --all origin", "git push --mirror origin", "git push --branches origin"):
                self.assertTrue(self.denied(dict(bash(command), cwd=raw)), command)

    def test_the_terminal_panel_reaches_the_push_guard(self):
        event = {"tool_name": "mcp__terminal__run_in_terminal", "tool_input": {"command": "git push origin main"}}
        self.assertTrue(self.denied(event))

    def test_every_way_to_push_to_main_is_denied(self):
        for command in ("git push origin main", "git push origin feat/x:main",
                        "git push origin HEAD:refs/heads/master", "git -C /repo push origin main",
                        "git push -u origin main", "git push --force origin master",
                        "cd x && git push origin main", "bash -c 'git push origin main'",
                        "echo $(git push origin main)", "x=`git push origin main`",
                        "git push origin \\\n  main", "bash <<'EOF'\ngit push origin main\nEOF",
                        "cat <<EOF | bash\ngit push origin main\nEOF", "sudo git push origin main",
                        "true; git push origin main", "ssh host 'git push origin main'",
                        "git push origin main 2>&1", "git push origin main >log 2>&1",
                        "git push origin HEAD:main &>log | tail -2", "git push origin '>' main",
                        "git push origin \">\" main", "git push origin \\> main",
                        "bash -c \"git push origin '>' main\"", "git push origin \"main\">\"log\"",
                        "git push origin 'main'>'log'", "git push origin \"main\"&&\"true\"",
                        "git push origin \"main\"&\"true\"", "git push origin \"main\"<\"/dev/null\"",
                        "bash -c 'git push origin \"main\">\"x\"'", "echo $(git push origin \"main\">\"x\")",
                        "bash <<'EOF'\ngit push origin \"main\">\"log\"\nEOF", "git push origin >x main",
                        "git push origin 1>&2 main", "git push origin <<< x main", "git push origin main>x",
                        "echo $'\\'>x'; git push origin main", "git -c a.b=$'\\'>x' push origin main",
                        "echo #'\n'>x'; git push origin main", "echo \"$(printf \"'\")\" '>x'; git push origin main",
                        "echo \"`printf \"'\"`\" '>x'; git push origin main"):
            self.assertTrue(self.denied(bash(command)), command)

    def test_merges_reads_and_topic_pushes_pass(self):
        for command in ("gh pr merge 291 --squash --delete-branch", "gh pr merge 12",
                        "gh api -X PUT repos/a/b/pulls/3/merge", "git push origin feat/constraints",
                        "git push -u origin agent/main-fix", "git merge origin/main", "git pull --ff-only",
                        "echo 'git push origin main'", "git commit -m 'never git push origin main'",
                        "cat > notes.md <<EOF\ngit push origin main\nEOF", "gh pr view 1", ""):
            self.assertFalse(self.denied(bash(command)), command)
        for event in ({"tool_name": "mcp__github__merge_pull_request", "tool_input": {"pull_number": 1}},
                      {"tool_name": "Bash", "tool_input": []}, {"tool_name": "Edit"}, {}):
            self.assertFalse(self.denied(event), event)

    def test_a_force_push_to_a_branch_not_checked_out_here_is_denied(self):
        with tempfile.TemporaryDirectory() as repo:
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                       GIT_COMMITTER_EMAIL="t@t")
            for args in (["init", "-q", "-b", "mine"], ["commit", "-q", "--allow-empty", "-m", "x"]):
                subprocess.run(["git", "-C", repo, *args], check=True, env=env)
            event = lambda command: dict(bash(command), cwd=repo)
            for command in ("git push --force origin other-chat-branch", "git push -f origin other-chat-branch",
                            "git push -f origin other-chat-branch 2>&1", "git push -f origin 327 >log",
                            "git push -f origin 1 > x", "echo 1>&2; git push -f origin 1 > x",
                            "git push -f origin 1 > x 1>&2", "git push -f origin 7 > x | cat 7>/dev/null",
                            "git push -f origin 2 >x 2>&1", "git push -f origin 3>x other",
                            "git push -f origin other${y:+:mine>x}",
                            "git push -f origin ${HOME:+other}${y:+:mine>x}",
                            "git push -f origin other${y:+:HEAD>x}",
                            "git push --force-with-lease origin other${y:+:mine >x} 2>&1 | tail -2",
                            "git push origin +other${y:+:mine>x}",
                            "git push -f origin mine <<<E\ngit push -f origin other\nE",
                            "git push --force-with-lease origin mine 2>&1 <<<E | tail -2\ngit push -f origin other\nE",
                            "git push -f origin mine <<E-1\nx\nE-1\ngit push -f origin other",
                            "git push -f origin mine 2>&1 <<E.1\nx\nE.1\ngit push -f origin other",
                            "cd >x; git push -f origin mine", "cd 2>/dev/null; git push -f origin mine",
                            "git push -f origin 327>log", "git push -f origin mine>>|x other",
                            "git push -f origin mine &>|x other", "git push -f origin <->",
                            "touch 327; git push -f origin <->", "git push -f origin <1-999>",
                            "git push -f origin mine<->", "git push -f origin HEAD:mine<->",
                            "xargs git push -f origin <refs", "xargs -n1 git push -f origin <refs >log 2>&1",
                            "env xargs git push -f origin <refs", "xargs git -C . push -f origin <refs",
                            "cd >x && git push -f origin mine", "pushd >x; git push -f origin mine",
                            "git push --force-with-lease origin mine:other-chat-branch",
                            "git push origin +other-chat-branch", f"git -C {repo} push -uf origin other"):
                decision = push_hook.decide(event(command))
                self.assertIn("Force-pushing", decision["hookSpecificOutput"]["permissionDecisionReason"], command)
            for command in ("git push --force-with-lease origin mine 2>&1 | tail -2",
                            "git push --force-with-lease origin HEAD:mine >log 2>&1", "git push -f origin mine &>log",
                            "git push -f origin mine <input", "git push -f origin mine 2>>errors",
                            "git push -f origin mine >| log",
                            "git push --force-with-lease origin mine", "git push -f", "git push -u origin mine",
                            "git push origin other-chat-branch", "git push --force-with-lease origin HEAD"):
                self.assertIsNone(push_hook.decide(event(command)), command)

    def test_the_script_prints_a_deny_that_names_main_and_ignores_bad_input(self):
        run = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(bash("git push origin main")),
                             capture_output=True, text=True, check=True)
        output = json.loads(run.stdout)["hookSpecificOutput"]
        self.assertEqual(("PreToolUse", "deny"), (output["hookEventName"], output["permissionDecision"]))
        self.assertIn("main", output["permissionDecisionReason"])
        for stdin in ("not json", json.dumps(bash("ls")), "[]"):
            run = subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True,
                                 text=True)
            self.assertEqual((0, ""), (run.returncode, run.stdout), stdin)

    def test_the_settings_fragment_runs_this_script_and_fails_open_when_it_is_missing(self):
        groups = json.loads((ROOT / "claude/hooks.json").read_text())["PreToolUse"][:1]
        commands = [hook["command"] for group in groups for hook in group["hooks"]]
        self.assertEqual(2, len(commands))
        self.assertIn("$HOME/.dot-agent/claude/hooks/no-push-to-main.py", commands[0])
        self.assertIn("$HOME/.dot-agent/claude/hooks/merge-gate.py", commands[1])
        with tempfile.TemporaryDirectory() as home:
            run = subprocess.run(["sh", "-c", commands[0]], input=json.dumps(bash("git push origin main")),
                                 capture_output=True, text=True, env=dict(os.environ, HOME=home))
            self.assertEqual((0, ""), (run.returncode, run.stdout))
            hooks = Path(home, ".dot-agent/claude/hooks")
            hooks.mkdir(parents=True)
            (hooks / "no-push-to-main.py").write_text(HOOK.read_text())
            run = subprocess.run(["sh", "-c", commands[0]], input=json.dumps(bash("git push origin main")),
                                 capture_output=True, text=True, env=dict(os.environ, HOME=home))
            self.assertEqual("deny", json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"])


class SendAndOutcomeHookTests(unittest.TestCase):
    def test_every_send_as_owner_asks_first(self):
        settings = json.loads((ROOT / "claude/hooks.json").read_text())
        matcher = re.compile(settings["PreToolUse"][1]["matcher"])
        for tool in ("mcp__0a1b2c3d-0000__send_message", "mcp__mail__reply", "mcp__mail__forward",
                     "mcp__ae4b74f9__create_event", "mcp__cal__respond_to_event", "mcp__drive__share_file",
                     "mcp__slack__post_message"):
            self.assertTrue(matcher.fullmatch(tool), tool)
            self.assertEqual("ask", send_hook.decide({"tool_name": tool})["hookSpecificOutput"]["permissionDecision"])
        for tool in ("mcp__mail__search_threads", "mcp__mail__create_draft", "mcp__cal__list_events", "Bash",
                     "mcp__ccd_session_mgmt__send_message"):
            self.assertIsNone(send_hook.decide({"tool_name": tool}), tool)
            self.assertIsNone(matcher.fullmatch(tool) if tool.startswith("mcp__ccd_") else None, tool)

    def transcript(self, *assistant, prompt="fix the gate"):
        lines = [{"type": "user", "message": {"content": prompt}}]
        for item in assistant:
            if isinstance(item, str):
                content = [{"type": "text", "text": item}]
            else:
                content = [{"type": "tool_use", "name": item[0], "input": item[1]}]
            lines.append({"type": "assistant", "message": {"content": content}})
            if not isinstance(item, str):
                lines.append({"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}})
        return [json.dumps(line) for line in lines]

    def decide(self, lines, **event):
        return outcome_hook.decide({"transcript_path": "t.jsonl", **event}, read=lambda path: lines)

    def test_a_turn_that_changed_files_must_end_with_one_outcome_line(self):
        stalled_2026_10_15 = self.transcript(("Edit", {"file_path": "a.py"}), "Done with the first part; next I will wire the CLI.")
        self.assertEqual("block", self.decide(stalled_2026_10_15)["decision"])
        shipped = self.transcript(("Bash", {"command": "git commit -m x && git push -u origin t"}),
                                  "Done: a.py. Not done: none.\nresult: the gate denies API merges")
        self.assertIsNone(self.decide(shipped))
        two = self.transcript(("Write", {"file_path": "a"}), "result: a\nfailed: b")
        self.assertIn("Found 2", self.decide(two)["reason"])
        self.assertIsNone(self.decide(stalled_2026_10_15, stop_hook_active=True))
        self.assertIsNone(self.decide(self.transcript(("Read", {"file_path": "a"}), "It says x.")))
        later = stalled_2026_10_15 + self.transcript("Short answer.", prompt="what is x?")
        self.assertIsNone(self.decide(later))
        self.assertIsNone(outcome_hook.decide({"transcript_path": "/nonexistent/t.jsonl"}))
        structured = self.transcript(("Edit", {"file_path": "a.py"}), ("StructuredOutput", {"summary": "x"}))
        self.assertIsNone(self.decide(structured[:-1]))


class MergeGateTests(unittest.TestCase):
    SHA = "a" * 40

    def fake_gh(self, checks, files=(("modified", "README.md"),)):
        calls = []

        def gh(args, cwd):
            calls.append(args)
            if args[:2] == ["pr", "view"]:
                return {"headRefOid": self.SHA, "number": 7, "changedFiles": len(files),
                        "url": "https://github.com/a/b/pull/7"}, ""
            if args[:1] == ["api"]:
                return [[{"status": status, "filename": name, **(extra[0] if extra else {})} for status, name, *extra in files]], ""
            return checks, ""
        return gh, calls

    def deny(self, command, checks, verdict_problem=""):
        gh, calls = self.fake_gh(checks)
        decision = merge_gate.decide(bash(command), gh=gh, gate=lambda sha, high=(): verdict_problem)
        return (decision["hookSpecificOutput"]["permissionDecisionReason"] if decision else None), calls

    def test_a_merge_with_red_checks_or_no_pass_verdict_is_denied(self):
        green = [{"name": "lint", "bucket": "pass"}, {"name": "docs", "bucket": "skipping"}]
        reason, calls = self.deny("gh pr merge 7 --squash -R a/b", [{"name": "lint", "bucket": "fail"}])
        self.assertIn("lint fail", reason)
        self.assertEqual(["pr", "view", "7", "--repo", "a/b", "--json", "headRefOid,number,url,changedFiles"], calls[0])
        self.assertIn("pending", self.deny("gh pr merge 7", [{"name": "x", "bucket": "pending"}])[0])
        self.assertIn("no checks", self.deny("gh pr merge 7", [])[0])
        reason, _ = self.deny("gh pr merge 7", green, "the verdict for aaaa is BLOCKED")
        self.assertIn("BLOCKED", reason)
        self.assertIn("only skipped", self.deny("gh pr merge 7", [{"name": "x", "bucket": "skipping"}])[0])
        for command in ("cd x && gh pr merge --auto 7", "bash -c 'gh pr merge 7'", "gh pr merge"):
            self.assertIn("lint fail", self.deny(command, [{"name": "lint", "bucket": "fail"}])[0], command)

    def test_arming_auto_merge_and_a_terminal_merge_reach_the_gate(self):
        arm = {"tool_name": "mcp__ccd_pr__set_auto_merge", "tool_input": {"enabled": True, "url": "https://github.com/a/b/pull/7"}}
        self.assertIn("auto-merge", merge_gate.decide(arm)["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIsNone(merge_gate.decide({**arm, "tool_input": {"enabled": False}}))
        gh, _ = self.fake_gh([{"name": "lint", "bucket": "fail"}])
        typed = {"tool_name": "mcp__terminal__run_in_terminal", "tool_input": {"command": "gh pr merge 7"}}
        self.assertIn("lint fail", merge_gate.decide(typed, gh=gh, gate=lambda sha, high=(): "")["hookSpecificOutput"]["permissionDecisionReason"])
        hooks = json.loads((ROOT / "claude/hooks.json").read_text())["PreToolUse"]
        for tool in ("mcp__terminal__run_in_terminal", "mcp__ccd_pr__set_auto_merge"):
            matched = [c["command"] for h in hooks if re.fullmatch(h["matcher"], tool) for c in h["hooks"]]
            self.assertTrue(any("merge-gate" in c for c in matched) and any("no-push" in c for c in matched), tool)

    def test_a_merge_with_green_checks_and_a_pass_verdict_passes(self):
        green = [{"name": "lint", "bucket": "pass"}]
        self.assertIsNone(self.deny(f"gh pr merge 7 --squash --delete-branch --match-head-commit {self.SHA}",
                                    green)[0])
        self.assertIsNone(self.deny(f"gh pr merge 7 --match-head-commit={self.SHA}", green)[0])

    def test_a_merge_not_pinned_to_the_checked_head_is_denied(self):
        green = [{"name": "lint", "bucket": "pass"}]
        self.assertIn(f"add --match-head-commit {self.SHA}", self.deny("gh pr merge 7 --squash", green)[0])
        reason = self.deny("gh pr merge 7 --match-head-commit " + "b" * 40, green)[0]
        self.assertIn("is not #7's head", reason)

    def test_a_missing_helper_denies_merges_instead_of_passing_them(self):
        with tempfile.TemporaryDirectory() as hooks:
            Path(hooks, "merge-gate.py").write_text(GATE.read_text())
            run = subprocess.run([sys.executable, str(Path(hooks, "merge-gate.py"))],
                                 input=json.dumps(bash("gh pr merge 7")), capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual("deny", json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"])

    def test_other_commands_never_call_gh(self):
        for command in ("gh pr view 7", "gh pr checks 7", "git merge origin/main",
                        "git commit -m 'gh pr merge 7'", "echo 'gh pr merge'", ""):
            reason, calls = self.deny(command, [])
            self.assertEqual((None, []), (reason, calls), command)

    def test_an_api_or_mcp_merge_is_denied_without_calling_gh(self):
        for command in ("gh api -X PUT repos/a/b/pulls/3/merge",
                        "gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: \"x\"}) { clientMutationId } }'",
                        "curl -X PUT -H 'Authorization: token t' https://api.github.com/repos/a/b/pulls/3/merge",
                        "gh api graphql -f query='mutation { enablePullRequestAutoMerge(input: {}) { clientMutationId } }'",
                        "cd /r && bash -c 'gh api -X PUT repos/a/b/pulls/3/merge'",
                        "gh api -X PUT repos/a/b/pulls/$N/merge", 'gh api -X PUT "repos/a/b/pulls/${PR}/merge"',
                        "gh -R a/b api -X PUT repos/a/b/pulls/3/merge"):
            reason, calls = self.deny(command, [])
            self.assertIn("REST or GraphQL API", reason or "", command)
            self.assertEqual([], calls, command)
        decision = merge_gate.decide({"tool_name": "mcp__github__merge_pull_request", "tool_input": {"pull_number": 3}})
        self.assertEqual("deny", decision["hookSpecificOutput"]["permissionDecision"])
        for command in ("gh api repos/a/b/pulls/3", "curl https://example.com",
                        "git commit -m 'gate pulls/3/merge'"):
            self.assertEqual((None, []), self.deny(command, []), command)

    def test_the_merge_runs_where_a_preceding_cd_points(self):
        seen = []
        merge_gate.decide(bash("cd /tmp/other && gh pr merge 7"),
                          gh=lambda args, cwd: (seen.append(cwd), (None, "x"))[1], gate=lambda sha, high=(): "")
        self.assertEqual(["/tmp/other"], seen)

    def test_an_unparsable_merge_or_a_crash_fails_closed(self):
        reason, calls = self.deny("gh pr merge 7 'unclosed", [])
        self.assertIn("could not parse", reason)
        run = subprocess.run([sys.executable, str(GATE)], input=json.dumps(
            {"tool_name": "Bash", "cwd": 5, "tool_input": {"command": "gh pr merge 7"}}),
            capture_output=True, text=True, env=dict(os.environ, PATH=""))
        self.assertEqual("deny", json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"])

    def test_an_unreadable_pr_fails_closed(self):
        decision = merge_gate.decide(bash("gh pr merge 7"), gh=lambda args, cwd: (None, "not found"),
                                     gate=lambda sha, high=(): "")
        self.assertIn("could not read the PR", decision["hookSpecificOutput"]["permissionDecisionReason"])

    def write_verdict(self, state, **extra):
        verdicts = Path(state, "verdicts")
        verdicts.mkdir(exist_ok=True)
        layers = {name: {"status": "PASS", "evidence": "x"} for name in ("checks", "contract", "live", "review")}
        entry = {"sha": self.SHA, "claim": "c", "layers": layers, "findings": [], "verdict": "PASS",
                 "limits": [], **extra}
        (verdicts / f"{self.SHA}.json").write_text(json.dumps(entry))

    def real_problems(self, files=(("modified", "README.md"),), checks=None):
        gh, _ = self.fake_gh(checks or [{"name": "lint", "bucket": "pass"}], files)
        return merge_gate.problems(["7"], self.SHA, None, gh)

    def use_state(self):
        state = tempfile.mkdtemp()
        os.environ["DOT_AGENT_STATE_HOME"] = state
        self.addCleanup(os.environ.pop, "DOT_AGENT_STATE_HOME", None)
        return state

    def test_the_real_gate_reads_recorded_verdicts(self):
        state = self.use_state()
        self.assertIn("no verdict recorded", self.real_problems()[0])
        self.write_verdict(state)
        self.assertEqual([], self.real_problems())

    def test_an_open_blocking_finding_denies_the_merge(self):
        state = self.use_state()
        finding = {"severity": "BLOCKING", "kind": "lost-data", "where": "a.py:3", "summary": "drops rows",
                   "outcome": "open", "reason": ""}
        layers = {name: {"status": "PASS", "evidence": "x"} for name in ("checks", "contract", "live", "review")}
        self.write_verdict(state, findings=[finding], verdict="BLOCKED", layers=layers)
        self.assertIn("open BLOCKING finding", self.real_problems()[0])

    def test_a_high_risk_merge_needs_owner_recorded_approval(self):
        state = self.use_state()
        self.write_verdict(state)
        for files in ((("modified", "AGENTS.md"),), (("modified", "claude/hooks/merge-gate.py"),),
                      (("removed", "docs/old.md"),), (("modified", "CONSTRAINTS.tsv"),),
                      (("renamed", "docs/old-gate.py", {"previous_filename": "claude/hooks/merge-gate.py"}),)):
            problems = self.real_problems(files)
            self.assertEqual(1, len(problems), files)
            self.assertIn("is high risk", problems[0])
            self.assertIn("verdict.py approve", problems[0])
        self.write_verdict(state, approved={"words": "The owner: yes, merge 7", "at": "now"})
        self.assertEqual([], self.real_problems((("modified", "AGENTS.md"),)))

    def test_unread_changed_files_deny_the_merge_even_when_approved(self):
        state = self.use_state()
        self.write_verdict(state)

        def gh(args, cwd):
            if args[:2] == ["pr", "view"]:
                return {"headRefOid": self.SHA, "number": 7, "changedFiles": 2,
                        "url": "https://github.com/a/b/pull/7"}, ""
            if args[:1] == ["api"]:
                return [[{"status": "modified", "filename": "README.md"}]], ""
            return [{"name": "lint", "bucket": "pass"}], ""
        self.assertIn("could not be read", merge_gate.problems(["7"], self.SHA, None, gh)[0])
        self.write_verdict(state, approved={"words": "The owner: yes", "at": "now"})
        self.assertIn("could not be read", " ".join(merge_gate.problems(["7"], self.SHA, None, gh)))

    def test_a_file_replaced_by_a_link_is_listed_twice_but_counted_once(self):
        self.use_state()

        def gh(args, cwd):
            if args[:2] == ["pr", "view"]:
                return {"headRefOid": self.SHA, "number": 7, "changedFiles": 2,
                        "url": "https://github.com/a/b/pull/7"}, ""
            if args[:1] == ["api"]:
                return [[{"status": "removed", "filename": "scripts/lint.py"},
                         {"status": "added", "filename": "scripts/lint.py"},
                         {"status": "modified", "filename": "README.md"}]], ""
            return [{"name": "lint", "bucket": "pass"}], ""
        self.assertNotIn("could not be read", " ".join(merge_gate.problems(["7"], self.SHA, None, gh)))


class PreCommitGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.hooksPath", str(ROOT / ".githooks"))
        check = self.repo / "scripts/check"
        check.parent.mkdir()
        check.write_text("#!/usr/bin/env bash\necho stub-check\n")
        check.chmod(0o755)
        self.git("add", ".")

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              text=True, env=env)

    def test_commits_on_main_or_master_are_refused(self):
        for branch in ("main", "master"):
            self.git("checkout", "-q", "-B", branch)
            run = self.git("commit", "-qm", "x")
            self.assertNotEqual(0, run.returncode, branch)
            self.assertIn(f"refusing to commit on {branch}", run.stderr)

    def test_a_topic_branch_runs_the_check_and_commits(self):
        self.git("checkout", "-q", "-b", "agent/topic")
        run = self.git("commit", "-qm", "x")
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertIn("stub-check", run.stdout + run.stderr)



if __name__ == "__main__":
    unittest.main()
