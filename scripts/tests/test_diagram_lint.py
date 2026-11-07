from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/diagram-lint.py"
spec = importlib.util.spec_from_file_location("diagram_lint", SCRIPT)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

SMALL = """flowchart LR
  subgraph today["Working now"]
    pick["The owner picks one item"]:::done --> build(Build on a branch)
  end
  build -- checks pass --> gate{Merge gate}
  gate -->|high risk| yes[[the owner says yes]]
  class gate todo
  class yes problem
"""

README_BEFORE_2_15_0 = """flowchart TD
  subgraph outer["Outer loop: scheduled jobs propose, never act"]
    hunter["Scheduled hunter: slop, every 3 days"]
    miner["Miner: repeated corrections from past chats"]
  end
  subgraph middle["Middle loop: the awake Mac condenses"]
    morning["Morning summary on the Mac: one first action"]
  end
  subgraph inner["Inner loop: owner + one Chat on one item, the only loop where work changes"]
    mode["/owner-mode picks a playbook"]
    build["Build in a topic branch or worktree"]
    check["scripts/check: static checks in pre-commit, --tests in CI"]
    verify["/verify: checks, contract, live, review; verdict pinned to the commit"]
    pr["PR"]
    gate["Merge gate: low risk merges once green; high risk needs the owner's recorded yes"]
  end
  subgraph learning["Learning"]
    rule["A correction made twice becomes a CONSTRAINTS.tsv row at the strongest level that works"]
    proof["Trusted only once its proof fails on the past mistake"]
  end
  hunter -- findings --> morning
  miner -- proposed rows --> morning
  morning -- the owner picks one item --> mode
  mode --> build --> check --> verify --> pr --> gate
  gate --> rule --> proof
  proof -- holds every later pass --> mode
"""


def run(*args, stdin=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True, text=True)


class DiagramLintTests(unittest.TestCase):
    def found(self, source):
        return " | ".join(lint.problems(source)[0])

    def test_a_small_plain_state_colored_diagram_passes(self):
        self.assertEqual(([], 4), lint.problems(SMALL))

    def test_the_readme_loop_diagram_before_2_15_0_fails_on_size_and_words(self):
        found = self.found(README_BEFORE_2_15_0)
        self.assertIn("11 boxes (max 8)", found)
        self.assertIn("label has 14 words", found)
        self.assertIn("label has 15 words", found)

    def test_nine_boxes_fail_and_eight_pass(self):
        chain = lambda n: "flowchart LR\n  " + " --> ".join(f"n{i}" for i in range(n))
        self.assertEqual([], lint.problems(chain(8))[0])
        self.assertIn("9 boxes", self.found(chain(9)))

    def test_long_node_and_edge_labels_fail(self):
        long = "one two three four five six seven eight nine"
        for source in (f'flowchart LR\n  a["{long}"] --> b', f"flowchart LR\n  a -->|{long}| b",
                       f"flowchart LR\n  a -- {long} --> b", f"flowchart LR\n  subgraph g[\"{long}\"]\n  a\n  end",
                       f"sequenceDiagram\n  A->>B: {long}"):
            self.assertIn("label has 9 words", self.found(source), source)
        self.assertEqual([], lint.problems('flowchart LR\n  a["one<br/>two three"] --> b')[0])

    def test_names_that_start_with_a_keyword_still_count_as_boxes(self):
        self.assertEqual(([], 5), lint.problems("flowchart LR\n  endpoint --> styler\n  a --> b & c\n  end"))

    def test_hand_colors_directives_and_c4_fail(self):
        for line, expected in (("classDef hot fill:red", "classDef"), ("style a fill:red", "style"),
                               ("linkStyle 0 stroke:red", "linkStyle"), ('a["#e8f0fe"]', "#e8f0fe"),
                               ("class a hot", "class hot"), ("a:::hot --> b", "class hot")):
            self.assertIn(expected, self.found(f"flowchart LR\n  a --> b\n  {line}"), line)
        self.assertIn("init directive", self.found("%%{init: {'theme':'dark'}}%%\nflowchart LR\n  a --> b"))
        self.assertIn("front-matter config", self.found("---\nconfig:\n  theme: dark\n---\nflowchart LR\n  a"))
        self.assertIn("C4Context", self.found("C4Context\n  Person(a, \"The owner\")"))
        self.assertIn("rgb(", self.found("sequenceDiagram\n  rect rgb(191, 223, 255)\n  A->>B: asks\n  end"))

    def test_sequence_and_state_diagrams_count_their_parts(self):
        seq = "sequenceDiagram\n  participant A as the owner\n  A->>B: asks\n  B-->>C: forwards\n  Note over A: waits"
        self.assertEqual(([], 3), lint.problems(seq))
        states = "stateDiagram-v2\n  [*] --> idle\n  idle --> busy : starts\n  busy --> [*]\n  class busy done"
        self.assertEqual(([], 2), lint.problems(states))

    def test_cli_reads_source_stdin_and_markdown_fences_and_reports_json(self):
        result = run("--json", SMALL)
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual({"ok": True, "diagrams": [{"where": "source", "nodes": 4, "problems": []}]},
                         json.loads(result.stdout))
        piped = run("--json", "-", stdin=README_BEFORE_2_15_0)
        self.assertEqual(1, piped.returncode)
        self.assertFalse(json.loads(piped.stdout)["ok"])
        fences = lint.diagrams("# Title\n\n```mermaid\nflowchart LR\n  a --> b\n```\n", "x.md", True)
        self.assertEqual([("x.md:4", "flowchart LR\n  a --> b\n")], fences)
        self.assertEqual(2, run().returncode)

    def test_every_committed_diagram_passes(self):
        result = run("--repo")
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn("scripts/diagram-lint.py --repo", (ROOT / "scripts/check").read_text())


if __name__ == "__main__":
    unittest.main()
