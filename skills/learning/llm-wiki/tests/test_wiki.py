import datetime
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("wiki", Path(__file__).parents[1] / "scripts/wiki.py")
wiki = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wiki)
TODAY = datetime.date(2026, 10, 18)


def page(kind, summary, sources="[]", updated="2026-10-18", status="current", body=""):
    return (
        f"---\ntitle: T\ntype: {kind}\nsummary: {summary}\nsources: {sources}\n"
        f"updated: {updated}\nconfidence: measured\nstatus: {status}\n---\n\n{body}\n"
    )


class WikiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "wiki"
        wiki.init(self.root, Path(self.temp.name) / "inbox")

    def write(self, folder, slug, text):
        (self.root / folder / f"{slug}.md").write_text(text, encoding="utf-8")

    def kinds(self):
        return {(f["kind"], f["page"]) for f in wiki.lint(self.root, TODAY, 30)["findings"]}

    def test_init_never_overwrites_the_schema(self):
        (self.root / "AGENTS.md").write_text("mine", encoding="utf-8")
        self.assertEqual(wiki.init(self.root, Path(self.temp.name) / "inbox"), [])
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), "mine")

    def test_a_clean_wiki_has_no_findings_once_indexed(self):
        self.write("sources", "report", page("source", "The report."))
        self.write("topics", "posting", page("topic", "How to post.", "[report]", body="See [[acme]]."))
        self.write("entities", "acme", page("entity", "A vendor.", "[report]"))
        wiki.build_index(self.root)
        self.assertEqual(self.kinds(), set())

    def test_index_lists_topics_first_and_flags_non_current_pages(self):
        self.write("sources", "old", page("source", "Old one.", status="stale"))
        self.write("topics", "posting", page("topic", "How to post.", "[old]"))
        text = wiki.build_index(self.root)
        self.assertLess(text.index("## Topics"), text.index("## Sources"))
        self.assertIn("- [[old]] Old one. (stale)", text)

    def test_lint_names_each_structural_problem(self):
        self.write("topics", "posting", page("topic", "How to post.", "[ghost]", body="[[missing]]"))
        self.write("topics", "bare", "no frontmatter\n")
        found = self.kinds()
        self.assertIn(("unknown-source", "topics/posting.md"), found)
        self.assertIn(("broken-link", "topics/posting.md"), found)
        self.assertIn(("not-in-index", "topics/posting.md"), found)
        self.assertIn(("no-frontmatter", "topics/bare.md"), found)
        self.assertEqual(wiki.main(["lint", str(self.root), "--today", "2026-10-18"]), 1)

    def test_stale_orphans_and_inbox_only_warn(self):
        self.write("topics", "posting", page("topic", "How to post.", updated="2026-08-01"))
        self.write("entities", "acme", page("entity", "A vendor."))
        (Path(self.temp.name) / "inbox" / "2026-10-18-dump").mkdir()
        wiki.build_index(self.root)
        found = self.kinds()
        self.assertIn(("stale", "topics/posting.md"), found)
        self.assertIn(("orphan", "entities/acme.md"), found)
        self.assertIn(("inbox-waiting", "inbox/2026-10-18-dump"), found)
        self.assertEqual(wiki.main(["lint", str(self.root), "--today", "2026-10-18"]), 0)

    def test_a_slug_reused_across_folders_is_reported(self):
        self.write("topics", "acme", page("topic", "Topic."))
        self.write("entities", "acme", page("entity", "Entity."))
        self.assertIn("duplicate-slug", {k for k, _ in self.kinds()})

    def test_lint_refuses_a_folder_that_is_not_a_wiki(self):
        self.assertEqual(wiki.main(["lint", str(Path(self.temp.name) / "nowhere")]), 2)

    def test_a_summary_with_a_hash_survives_and_a_block_list_is_reported(self):
        self.write("topics", "rank", page("topic", "Ranks #1 for posting.", sources="\n  - report"))
        wiki.build_index(self.root)
        self.assertIn("Ranks #1 for posting.", (self.root / "index.md").read_text(encoding="utf-8"))
        self.assertIn(("bad-sources", "topics/rank.md"), self.kinds())

    def test_an_index_naming_a_deleted_page_is_out_of_date(self):
        self.write("topics", "gone", page("topic", "Gone."))
        wiki.build_index(self.root)
        (self.root / "topics" / "gone.md").unlink()
        self.assertIn(("index-out-of-date", "index.md"), self.kinds())


    def test_an_index_with_an_old_summary_is_out_of_date(self):
        self.write("topics", "posting", page("topic", "How to post."))
        wiki.build_index(self.root)
        self.write("topics", "posting", page("topic", "How to post, revised.", status="stale"))
        self.assertIn(("index-out-of-date", "index.md"), self.kinds())
        self.assertEqual(wiki.main(["lint", str(self.root), "--today", "2026-10-18"]), 1)


    def test_a_list_in_a_single_value_field_is_reported_not_a_crash(self):
        self.write("topics", "posting", page("topic", "How to post.").replace("confidence: measured", "confidence: [measured]"))
        wiki.build_index(self.root)
        self.assertIn(("list-field", "topics/posting.md"), self.kinds())


if __name__ == "__main__":
    unittest.main()
