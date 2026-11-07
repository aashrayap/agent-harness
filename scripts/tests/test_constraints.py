from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_constraints", ROOT / "scripts/check-constraints.py")
constraints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(constraints)
HEADER = "id\trule\tlevel\tenforcer\tproof\tnotes\n"


def row(*fields):
    return "\t".join(fields).rstrip("\t") + "\n"


class ConstraintsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.put("AGENTS.md", "- merging\n  any PR;\n")
        self.put("tool.py", "LIMIT = 3\n\ndef guard():\n    pass\n")
        self.put("tests/test_tool.py", "def test_guard_refuses():\n    pass\n")
        self.put("hook.sh", "refuse_main\n")

    def put(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def check(self, *rows):
        self.put("CONSTRAINTS.tsv", HEADER + "".join(rows))
        return constraints.problems(self.root)

    def good(self):
        return (row("pause-merge", "merging any PR;", "prose", "AGENTS.md", "", ""),
                row("cap", "At most 3", "impossible", "tool.py::LIMIT", "test_guard_refuses", ""),
                row("guard", "Guard", "test", "tests/test_tool.py::test_guard_refuses",
                    "fails without guard", ""),
                row("fn", "Guard fn", "check", "tool.py::guard", "a past miss", ""),
                row("main", "No main", "hook", "hook.sh::refuse_main", "a commit on main", ""),
                row("mem", "Remember", "memory", "some-memory.md", "", ""))

    def test_a_valid_table_passes_and_the_repo_table_passes(self):
        self.assertEqual([], self.check(*self.good()))
        self.assertEqual([], constraints.problems())

    def test_a_reworded_prose_rule_fails(self):
        self.put("AGENTS.md", "- merging PRs freely\n")
        self.assertEqual(["CONSTRAINTS.tsv:2: AGENTS.md no longer says: merging any PR;"],
                         self.check(self.good()[0]))

    def test_a_missing_enforcer_or_name_fails(self):
        found = self.check(row("a", "x", "check", "gone.py", "p", ""),
                           row("b", "x", "check", "tool.py::missing", "p", ""),
                           row("c", "x", "hook", "hook.sh::refuse", "p", ""),
                           row("d", "x", "check", "../outside.py", "p", ""),
                           row("e", "x", "check", "/etc/hosts", "p", ""))
        self.assertEqual(["CONSTRAINTS.tsv:2: enforcer 'gone.py' is not a file in the repo",
                          "CONSTRAINTS.tsv:3: tool.py has no 'missing'",
                          "CONSTRAINTS.tsv:4: hook.sh has no 'refuse'",
                          "CONSTRAINTS.tsv:5: enforcer '../outside.py' is not a file in the repo",
                          "CONSTRAINTS.tsv:6: enforcer '/etc/hosts' is not a file in the repo"],
                         found)

    def test_duplicate_ids_bad_levels_and_short_rows_fail(self):
        good = self.good()
        found = self.check(good[0], good[0], row("x", "y", "lint", "AGENTS.md", "p", ""),
                           "z\tonly three\tprose\n", row("Bad_Id", "y", "check", "tool.py", "p", ""))
        self.assertEqual(["CONSTRAINTS.tsv:3: duplicate id 'pause-merge' (first on line 2)",
                          "CONSTRAINTS.tsv:4: level 'lint' must be one of impossible, check, test,"
                          " hook, prose, memory",
                          "CONSTRAINTS.tsv:5: needs 4 to 6 tab-separated fields (proof and notes"
                          " may be left off), has 3",
                          "CONSTRAINTS.tsv:6: id 'Bad_Id' must be lowercase-kebab"], found)
        self.put("CONSTRAINTS.tsv", "file\tphrase\n")
        self.assertEqual(1, len(constraints.problems(self.root)))

    def test_rows_above_prose_need_proof_and_named_tests_must_exist(self):
        found = self.check(row("a", "x", "check", "tool.py", "", ""),
                           row("b", "x", "test", "tool.py", "test_never_written fails", ""))
        self.assertEqual(["CONSTRAINTS.tsv:2: a check row needs proof: the past mistake or test"
                          " that shows the enforcer fails without the fix",
                          "CONSTRAINTS.tsv:3: proof names test_never_written, which no test file"
                          " defines"], found)


if __name__ == "__main__":
    unittest.main()
