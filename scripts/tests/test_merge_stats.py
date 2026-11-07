from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("merge_stats", ROOT / "scripts/merge-stats.py")
merge_stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge_stats)
PASSED = {name: {"status": "PASS", "evidence": "x"} for name in ("checks", "contract", "live", "review")}


class MergeStatsTest(unittest.TestCase):
    def test_merges_count_as_auto_owner_or_outside_from_the_verdict_log(self):
        with tempfile.TemporaryDirectory() as raw, mock.patch.dict(os.environ, {"DOT_AGENT_STATE_HOME": raw}):
            verdicts = Path(raw, "verdicts")
            verdicts.mkdir()

            def write(sha, **entry):
                (verdicts / f"{sha * 40}.json").write_text(json.dumps(
                    {"sha": sha * 40, "layers": PASSED, "findings": [], "verdict": "PASS", "limits": [], **entry}))
            write("a")
            write("b", approved={"words": "yes", "at": "now"})
            write("c", layers={**PASSED, "live": {"status": "BLOCKED", "evidence": "x"}}, verdict="BLOCKED")
            write("e")
            entry = json.loads((verdicts / f"{'e' * 40}.json").read_text())
            del entry["findings"]
            (verdicts / f"{'e' * 40}.json").write_text(json.dumps(entry))
            write("f", layers={**PASSED, "review": {"status": "SKIP", "evidence": "x"}})
            prs = [{"number": n, "headRefOid": sha * 40}
                   for n, sha in ((1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e"), (6, "f"))]
            self.assertEqual({"auto": [1], "owner": [2], "outside": [3, 4, 5, 6]}, merge_stats.tally(prs))


if __name__ == "__main__":
    unittest.main()
