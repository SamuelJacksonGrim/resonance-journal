# Resonance Journal
# Copyright (C) 2026 Samuel Jackson Grim
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# A commercial license is also available: see LICENSING.md.
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from resonance_journal.export import MARKER, export_entries, slugify
from resonance_journal.model import EntryDraft, ExportError, ExportFormat, SearchQuery, Visibility
from tests.helpers import memory_journal

NOW = "2026-02-02T00:00:00Z"


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.j, self.store, _ = memory_journal()
        self.a = self.j.create(EntryDraft("Rivers & roads", "line 1\n\n  indented — ünïcode\n", ("nature",)))
        self.b = self.j.create(EntryDraft('Quote "this"', "no trailing newline"))
        self.j.link(self.b.id, self.a.id, "echo")
        self.j.archive(self.a.id)
        self.entries = self.j.search(SearchQuery(visibility=Visibility.ALL))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_json_is_lossless(self):  # G4
        out = export_entries(self.entries, ExportFormat.JSON, self.root / "j.json", NOW)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["format"], "resonance-journal/v1")
        by_id = {e["id"]: e for e in doc["entries"]}
        for entry in self.entries:
            got = by_id[entry.id]
            self.assertEqual(got["title"], entry.title)
            self.assertEqual(got["body"], entry.body)
            self.assertEqual(tuple(got["tags"]), entry.tags)
            self.assertEqual(got["archived_at"], entry.archived_at)
            self.assertEqual(got["updated_at"], entry.updated_at)
        self.assertEqual(by_id[self.b.id]["links"], [{"target_id": self.a.id, "note": "echo"}])

    def test_markdown_layout_and_verbatim_body(self):
        out = export_entries(self.entries, ExportFormat.MARKDOWN, self.root / "md", NOW)
        names = sorted(p.name for p in out.iterdir())
        self.assertEqual(names, [MARKER, "0001-rivers-roads.md", "0002-quote-this.md", "index.md"])
        text = (out / "0001-rivers-roads.md").read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n---\n\n" + self.j.get(self.a.id).body))
        self.assertIn('title: "Quote \\"this\\""', (out / "0002-quote-this.md").read_text(encoding="utf-8"))
        self.assertIn(f"links: [{self.a.id}]", (out / "0002-quote-this.md").read_text(encoding="utf-8"))
        self.assertIn("*(archived)*", (out / "index.md").read_text(encoding="utf-8"))

    @unittest.skipIf(os.name != "posix", "POSIX permissions")
    def test_private_permissions(self):  # C-P2
        md = export_entries(self.entries, ExportFormat.MARKDOWN, self.root / "md", NOW)
        js = export_entries(self.entries, ExportFormat.JSON, self.root / "j.json", NOW)
        self.assertEqual(stat.S_IMODE(md.stat().st_mode), 0o700)
        for f in [js, *md.iterdir()]:
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600, f)

    def test_never_overwrites_without_force(self):
        target = self.root / "j.json"
        target.write_text("precious")
        with self.assertRaises(ExportError):
            export_entries(self.entries, ExportFormat.JSON, target, NOW)
        self.assertEqual(target.read_text(), "precious")
        export_entries(self.entries, ExportFormat.JSON, target, NOW, force=True)
        self.assertIn("resonance-journal/v1", target.read_text())

    def test_force_only_replaces_previous_markdown_export(self):
        precious = self.root / "Documents"
        precious.mkdir()
        (precious / "thesis.txt").write_text("years of work")
        with self.assertRaisesRegex(ExportError, "not a Resonance Journal export"):
            export_entries(self.entries, ExportFormat.MARKDOWN, precious, NOW, force=True)
        self.assertEqual((precious / "thesis.txt").read_text(), "years of work")

        out = self.root / "md"
        export_entries(self.entries, ExportFormat.MARKDOWN, out, NOW)
        (out / "stale.md").write_text("old")
        export_entries(self.entries[:1], ExportFormat.MARKDOWN, out, NOW, force=True)
        self.assertEqual(len(list(out.glob("0*.md"))), 1)
        self.assertFalse((out / "stale.md").exists())
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith(".")], [])

    def test_missing_parent_and_failed_write_leave_nothing(self):
        with self.assertRaises(ExportError):
            export_entries(self.entries, ExportFormat.JSON, self.root / "nope" / "j.json", NOW)
        with self.assertRaises(ExportError):
            export_entries(self.entries, ExportFormat.JSON, self.root, NOW, force=True)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_slugify(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")
        self.assertEqual(slugify("日本語"), "entry")
        self.assertLessEqual(len(slugify("x" * 100)), 40)


if __name__ == "__main__":
    unittest.main()
