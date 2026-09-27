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
"""Journal use cases. The single authority on domain rules.

The store is injected (JournalStore protocol); this module never imports
store.py. See architecture/Contracts.md, authority table.
"""

from __future__ import annotations

from typing import Iterable

from .model import (
    Clock,
    Entry,
    EntryDraft,
    EntryId,
    JournalStore,
    NotFoundError,
    SearchQuery,
    Tag,
    ValidationError,
    Visibility,
    normalize_tags,
    utcnow,
    validate_title,
)


class Journal:
    def __init__(self, store: JournalStore, clock: Clock = utcnow) -> None:
        self._store = store
        self._clock = clock

    def get(self, entry_id: EntryId) -> Entry:
        entry = self._store.get_entry(entry_id)
        if entry is None:
            raise NotFoundError(f"no entry with id {entry_id}")
        return entry

    def create(self, draft: EntryDraft) -> Entry:
        title = validate_title(draft.title)
        tags = normalize_tags(draft.tags)
        now = self._clock()
        with self._store.transaction():
            entry_id = self._store.insert_entry(title, draft.body, now)
            self._store.add_tags(entry_id, tags)
        return self.get(entry_id)

    def edit(self, entry_id: EntryId, title: str | None = None, body: str | None = None) -> Entry:
        if title is None and body is None:
            raise ValidationError("nothing to edit: give a new title and/or body")
        with self._store.transaction():
            current = self.get(entry_id)
            new_title = validate_title(title) if title is not None else current.title
            new_body = body if body is not None else current.body
            # "updated_at moves only on real change" (Contracts).
            if (new_title, new_body) != (current.title, current.body):
                self._store.update_entry(entry_id, new_title, new_body, self._clock())
        return self.get(entry_id)

    def tag(self, entry_id: EntryId, add: Iterable[str] = (), remove: Iterable[str] = ()) -> Entry:
        # Normalize everything before writing anything: one bad token rejects all.
        to_add = set(normalize_tags(add))
        to_remove = set(normalize_tags(remove))
        overlap = to_add & to_remove
        if overlap:
            raise ValidationError(f"tag both added and removed: {', '.join(sorted(overlap))}")
        with self._store.transaction():
            current = set(self.get(entry_id).tags)
            new = (current | to_add) - to_remove
            if new != current:
                self._store.add_tags(entry_id, sorted(to_add - current))
                self._store.remove_tags(entry_id, sorted(to_remove & current))
                self._store.touch(entry_id, self._clock())
        return self.get(entry_id)

    def link(self, src: EntryId, dst: EntryId, note: str = "") -> Entry:
        if src == dst:
            raise ValidationError("an entry cannot link to itself")
        note = note.strip()
        if "\n" in note:
            raise ValidationError("link note must be a single line")
        with self._store.transaction():
            self.get(src)
            self.get(dst)
            self._store.upsert_link(src, dst, note, self._clock())
        return self.get(src)

    def unlink(self, src: EntryId, dst: EntryId) -> Entry:
        with self._store.transaction():
            self.get(src)
            self.get(dst)
            self._store.delete_link(src, dst)
        return self.get(src)

    def archive(self, entry_id: EntryId) -> Entry:
        with self._store.transaction():
            if not self.get(entry_id).archived:
                self._store.set_archived(entry_id, self._clock())
        return self.get(entry_id)

    def unarchive(self, entry_id: EntryId) -> Entry:
        with self._store.transaction():
            if self.get(entry_id).archived:
                self._store.set_archived(entry_id, None)
        return self.get(entry_id)

    def search(self, query: SearchQuery) -> list[Entry]:
        if query.limit is not None and query.limit < 1:
            raise ValidationError("limit must be at least 1")
        terms = tuple(t.strip() for t in query.terms if t.strip())
        normalized = SearchQuery(
            terms=terms,
            tags=normalize_tags(query.tags),
            visibility=query.visibility,
            limit=query.limit,
        )
        return self._store.find_entries(normalized)

    def tags(self, visibility: Visibility = Visibility.ACTIVE) -> list[tuple[Tag, int]]:
        return self._store.tag_counts(visibility)
