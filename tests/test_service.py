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
import unittest

from resonance_journal.model import (
    EntryDraft,
    NotFoundError,
    SearchQuery,
    StorageError,
    ValidationError,
    Visibility,
)
from tests.helpers import memory_journal


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.j, self.store, self.clock = memory_journal()

    def tearDown(self):
        self.store.close()

    def new(self, title="T", body="", tags=()):
        return self.j.create(EntryDraft(title, body, tuple(tags)))

    # create / view
    def test_create_sets_fields_and_normalizes_tags(self):
        e = self.new("  Dawn ", "birds", ["Morning", "#morning", "Birds"])
        self.assertEqual((e.title, e.body, e.tags), ("Dawn", "birds", ("birds", "morning")))
        self.assertEqual(e.created_at, e.updated_at)
        self.assertFalse(e.archived)
        self.assertEqual(self.j.get(e.id), e)

    def test_create_with_bad_tag_writes_nothing(self):
        with self.assertRaises(ValidationError):
            self.new("x", tags=["ok", "not ok"])
        self.assertEqual(self.j.search(SearchQuery(visibility=Visibility.ALL)), [])

    def test_get_unknown(self):
        with self.assertRaises(NotFoundError):
            self.j.get(99)

    # edit
    def test_edit_changes_and_bumps_updated_at(self):
        e = self.new("a", "b")
        e2 = self.j.edit(e.id, body="c")
        self.assertEqual((e2.title, e2.body), ("a", "c"))
        self.assertGreater(e2.updated_at, e.updated_at)
        self.assertEqual(e2.created_at, e.created_at)

    def test_noop_edit_keeps_updated_at(self):
        e = self.new("a", "b")
        self.assertEqual(self.j.edit(e.id, title="a", body="b").updated_at, e.updated_at)

    def test_edit_requires_a_field_and_valid_title(self):
        e = self.new()
        with self.assertRaises(ValidationError):
            self.j.edit(e.id)
        with self.assertRaises(ValidationError):
            self.j.edit(e.id, title="")
        with self.assertRaises(NotFoundError):
            self.j.edit(42, body="x")

    # tags
    def test_tag_add_remove_and_noop(self):
        e = self.new(tags=["a"])
        e2 = self.j.tag(e.id, add=["B"], remove=["a"])
        self.assertEqual(e2.tags, ("b",))
        self.assertGreater(e2.updated_at, e.updated_at)
        e3 = self.j.tag(e.id, add=["b"], remove=["zzz"])
        self.assertEqual(e3.updated_at, e2.updated_at)

    def test_tag_rejects_whole_command_on_one_bad_token(self):
        e = self.new(tags=["a"])
        with self.assertRaises(ValidationError):
            self.j.tag(e.id, add=["good", "bad tag"])
        self.assertEqual(self.j.get(e.id).tags, ("a",))

    def test_tag_add_and_remove_same_is_rejected(self):
        e = self.new()
        with self.assertRaises(ValidationError):
            self.j.tag(e.id, add=["x"], remove=["X"])

    def test_unused_tags_disappear_from_counts(self):
        a, b = self.new(tags=["x", "y"]), self.new(tags=["x"])
        self.j.tag(a.id, remove=["y"])
        self.assertEqual(self.j.tags(), [("x", 2)])

    # links
    def test_link_shows_on_both_sides_and_upserts_note(self):
        a, b = self.new("A"), self.new("B")
        self.j.link(a.id, b.id, "first")
        self.j.link(a.id, b.id, "second")
        a2, b2 = self.j.get(a.id), self.j.get(b.id)
        self.assertEqual([(l.target_id, l.note, l.other_title) for l in a2.links], [(b.id, "second", "B")])
        self.assertEqual([(l.source_id, l.other_title) for l in b2.backlinks], [(a.id, "A")])
        self.assertEqual(a2.updated_at, a.updated_at)

    def test_link_rules(self):
        a = self.new()
        with self.assertRaises(ValidationError):
            self.j.link(a.id, a.id)
        with self.assertRaises(NotFoundError):
            self.j.link(a.id, 99)
        with self.assertRaises(ValidationError):
            self.j.link(a.id, 99, "two\nlines")

    def test_unlink_is_idempotent(self):
        a, b = self.new(), self.new()
        self.j.link(a.id, b.id)
        self.j.unlink(a.id, b.id)
        self.j.unlink(a.id, b.id)
        self.assertEqual(self.j.get(a.id).links, ())

    # archive
    def test_archive_hides_but_keeps_everything(self):
        a, b = self.new("A", tags=["t"]), self.new("B")
        self.j.link(b.id, a.id)
        archived = self.j.archive(a.id)
        self.assertTrue(archived.archived)
        self.assertEqual(archived.updated_at, a.updated_at)
        self.assertEqual([e.id for e in self.j.search(SearchQuery())], [b.id])
        self.assertEqual([e.id for e in self.j.search(SearchQuery(visibility=Visibility.ARCHIVED))], [a.id])
        self.assertEqual(len(self.j.search(SearchQuery(visibility=Visibility.ALL))), 2)
        self.assertTrue(self.j.get(b.id).links[0].other_archived)
        self.assertEqual(self.j.tags(), [])
        self.assertEqual(self.j.tags(Visibility.ALL), [("t", 1)])
        again = self.j.archive(a.id)
        self.assertEqual(again.archived_at, archived.archived_at)
        restored = self.j.unarchive(a.id)
        self.assertFalse(restored.archived)
        self.assertEqual(len(self.j.get(b.id).links), 1)

    # search
    def test_search_all_terms_case_insensitive_literal(self):
        a = self.new("River walk", "cold water, 100% alive", ["nature"])
        b = self.new("Office", "snake_case refactor", ["work"])
        c = self.new("Été", "chaleur")
        ids = lambda *terms, **kw: [e.id for e in self.j.search(SearchQuery(terms=terms, **kw))]
        self.assertEqual(ids("RIVER"), [a.id])
        self.assertEqual(ids("river", "alive"), [a.id])
        self.assertEqual(ids("river", "office"), [])
        self.assertEqual(ids("100%"), [a.id])
        self.assertEqual(ids("%"), [a.id])
        self.assertEqual(ids("e_c"), [b.id])
        self.assertEqual(ids("_"), [b.id])
        self.assertEqual(ids("été".upper()), [c.id])
        self.assertEqual(ids("natur"), [a.id])  # tag text matches too
        self.assertEqual(ids(tags=("#Work",)), [b.id])
        self.assertEqual(ids(), [c.id, b.id, a.id])  # newest first
        self.assertEqual(ids(limit=1), [c.id])
        with self.assertRaises(ValidationError):
            self.j.search(SearchQuery(limit=0))

    # atomicity (G2)
    def test_failure_inside_transaction_rolls_back(self):
        a = self.new("A", tags=["keep"])
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.store.update_entry(a.id, "changed", "changed", "2099-01-01T00:00:00Z")
                self.store.add_tags(a.id, ["lost"])
                raise RuntimeError("boom")
        self.assertEqual(self.j.get(a.id), a)

    def test_store_integrity_backstops_service(self):
        a = self.new()
        with self.assertRaises(StorageError):
            self.store.upsert_link(a.id, a.id, "", "2026-01-01T00:00:00Z")
        with self.assertRaises(StorageError):
            self.store.upsert_link(a.id, 99, "", "2026-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
