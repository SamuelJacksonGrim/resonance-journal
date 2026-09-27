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
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from resonance_journal import cli


class TTYInput(io.StringIO):
    def isatty(self):
        return True


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "journal.db"
        self.editor_calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def rj(self, *argv, stdin="", editor_result=None):
        out, err = io.StringIO(), io.StringIO()

        def editor(initial):
            self.editor_calls.append(initial)
            if editor_result is None:
                raise AssertionError("editor should not be opened")
            return editor_result

        stream = stdin if isinstance(stdin, io.StringIO) else io.StringIO(stdin)
        code = cli.main(["--db", str(self.db), *argv], out=out, err=err, stdin=stream, editor=editor)
        return code, out.getvalue(), err.getvalue()

    def ok(self, *argv, **kw):
        code, out, err = self.rj(*argv, **kw)
        self.assertEqual(code, 0, err)
        return out

    def test_full_main_path(self):
        self.assertIn("created #1", self.ok("new", "Tide", "--body", "The tide came in.", "-t", "Sea"))
        self.assertIn("created #2", self.ok("new", "Moon", "--body-file", "-", stdin="pulls the tide\n"))
        self.ok("edit", "2", "--title", "Moon pull")
        self.ok("tag", "2", "sea", "#Night")
        self.ok("untag", "2", "night")
        self.ok("link", "2", "1", "--note", "same water")
        show = self.ok("show", "1")
        self.assertIn("← 2  Moon pull — same water", show)
        self.assertIn("#sea", show)
        self.assertIn("→ 1  Tide", self.ok("show", "#2"))
        self.assertEqual(len(self.ok("search", "TIDE").splitlines()), 2)
        self.assertEqual(len(self.ok("search", "--tag", "sea", "pulls").splitlines()), 1)
        self.assertIn("2  #sea", self.ok("tags"))
        self.ok("archive", "1")
        self.assertNotIn("Tide", self.ok("list"))
        self.assertIn("[archived]", self.ok("list", "--archived"))
        self.assertIn("[archived]", self.ok("show", "2"))  # backlink target marked
        out = self.root / "export.json"
        self.assertIn("exported 2 entries", self.ok("export", "--all", "--format", "json", "--out", str(out)))
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual({e["title"] for e in doc["entries"]}, {"Tide", "Moon pull"})
        self.assertIn("exported 1 entries", self.ok("export", "--out", str(self.root / "md")))
        self.ok("unarchive", "1")
        self.ok("unlink", "2", "1")
        self.assertNotIn("links:", self.ok("show", "2"))

    def test_new_body_from_file_and_piped_stdin(self):
        body = self.root / "body.txt"
        body.write_text("from a file\n", encoding="utf-8")
        self.ok("new", "F", "--body-file", str(body))
        self.ok("new", "P", stdin="piped\n")
        self.assertIn("from a file", self.ok("show", "1"))
        self.assertIn("piped", self.ok("show", "2"))

    def test_editor_paths(self):
        self.ok("new", stdin=TTYInput(), editor_result="Written in editor\n\nbody text\n")
        self.assertIn("Written in editor", self.ok("show", "1"))
        self.ok("edit", "1", editor_result="Renamed\n\nnew body\n")
        self.assertEqual(self.editor_calls[-1], "Written in editor\n\nbody text\n")
        shown = self.ok("show", "1")
        self.assertIn("Renamed", shown)
        self.assertIn("new body", shown)

    def test_empty_editor_buffer_aborts_without_writing(self):  # G3
        self.ok("new", "Keep", "--body", "original")
        code, _, err = self.rj("edit", "1", editor_result="   \n")
        self.assertEqual(code, 1)
        self.assertIn("aborted", err)
        self.assertIn("original", self.ok("show", "1"))

    def test_errors_exit_1_and_do_not_leak_content(self):  # C-P4
        self.ok("new", "Secret", "--body", "my private thought")
        for argv in (["show", "9"], ["link", "1", "1"], ["tag", "1", "bad tag"], ["new", "   "],
                     ["edit", "1", "--title", "a\nb"]):
            code, out, err = self.rj(*argv)
            self.assertEqual(code, 1, argv)
            self.assertTrue(err.startswith("error: "), err)
            self.assertNotIn("private thought", err + out)

    def test_usage_errors_exit_2(self):
        stderr, sys.stderr = sys.stderr, io.StringIO()
        try:
            self.assertEqual(self.rj("show", "abc")[0], 2)
            self.assertEqual(self.rj("frobnicate")[0], 2)
            self.assertEqual(self.rj("list", "--all", "--archived")[0], 2)
        finally:
            sys.stderr = stderr

    def test_export_refuses_existing_target(self):
        self.ok("new", "x")
        target = self.root / "out.json"
        target.write_text("keep me")
        code, _, err = self.rj("export", "--format", "json", "--out", str(target))
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(), "keep me")

    def test_default_db_path_env(self):
        old = dict(os.environ)
        try:
            os.environ["RESONANCE_JOURNAL_DB"] = str(self.root / "env.db")
            self.assertEqual(cli.default_db_path(), self.root / "env.db")
            del os.environ["RESONANCE_JOURNAL_DB"]
            os.environ["XDG_DATA_HOME"] = str(self.root / "xdg")
            self.assertEqual(cli.default_db_path(), self.root / "xdg" / "resonance-journal" / "journal.db")
        finally:
            os.environ.clear()
            os.environ.update(old)

    @unittest.skipIf(os.name != "posix", "needs a POSIX shell editor")
    def test_real_editor_temp_file_is_private_and_deleted(self):  # C-P3
        seen = self.root / "seen"
        script = self.root / "fake-editor.py"
        script.write_text(
            "import os, stat, sys\n"
            "p = sys.argv[1]\n"
            f"open({str(seen)!r}, 'w').write(p + ' ' + oct(stat.S_IMODE(os.stat(p).st_mode)))\n"
            "open(p, 'a').write('added line\\n')\n"
        )
        old = os.environ.get("VISUAL")
        os.environ["VISUAL"] = f"{sys.executable} {script}"
        try:
            text = cli.edit_in_editor("Title\n\n")
        finally:
            if old is None:
                os.environ.pop("VISUAL", None)
            else:
                os.environ["VISUAL"] = old
        self.assertEqual(text, "Title\n\nadded line\n")
        path, mode = seen.read_text().split()
        self.assertEqual(mode, "0o600")
        self.assertFalse(Path(path).exists())


class SplitTitleBodyTest(unittest.TestCase):
    def test_split(self):
        self.assertEqual(cli.split_title_body("# Title\n\nline\n"), ("Title", "line\n"))
        self.assertEqual(cli.split_title_body("Only title\n"), ("Only title", ""))


if __name__ == "__main__":
    unittest.main()
