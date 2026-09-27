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

from resonance_journal.model import ValidationError, normalize_tag, normalize_tags, validate_title


class NormalizeTagTest(unittest.TestCase):
    def test_case_hash_and_whitespace_collapse_to_one_tag(self):
        self.assertEqual({normalize_tag(t) for t in ["Work", "work", "#work", " WORK "]}, {"work"})

    def test_allowed_shapes(self):
        for tag in ["a", "2026", "deep-work", "people/sam", "snake_case", "x" * 40]:
            self.assertEqual(normalize_tag(tag), tag)

    def test_rejected_shapes(self):
        for bad in ["", "#", "two words", "-lead", "_lead", "x" * 41, "émoji", "a.b"]:
            with self.assertRaises(ValidationError, msg=bad):
                normalize_tag(bad)

    def test_normalize_tags_dedupes_and_sorts(self):
        self.assertEqual(normalize_tags(["b", "A", "#a"]), ("a", "b"))


class ValidateTitleTest(unittest.TestCase):
    def test_trims(self):
        self.assertEqual(validate_title("  Hello  "), "Hello")

    def test_rejects_empty_multiline_and_long(self):
        for bad in ["", "   ", "a\nb", "x" * 201]:
            with self.assertRaises(ValidationError):
                validate_title(bad)

    def test_accepts_200(self):
        self.assertEqual(len(validate_title("x" * 200)), 200)


if __name__ == "__main__":
    unittest.main()
