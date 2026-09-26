import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from resonance_journal.model import StorageError
from resonance_journal.store import SCHEMA_VERSION, Store


class StoreFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @unittest.skipIf(os.name != "posix", "POSIX permissions")
    def test_creates_private_dir_and_file(self):  # C-P1
        path = self.root / "nested" / "journal.db"
        Store.open(path).close()
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode) & 0o077, 0)

    def test_schema_version_and_reopen_keeps_data(self):  # I5
        path = self.root / "j.db"
        s = Store.open(path)
        entry_id = s.insert_entry("t", "b", "2026-01-01T00:00:00Z")
        s.close()
        s = Store.open(path)
        self.assertEqual(s.get_entry(entry_id).title, "t")
        self.assertEqual(s._conn.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
        s.close()

    def test_refuses_newer_schema(self):
        path = self.root / "future.db"
        conn = sqlite3.connect(path)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
        conn.close()
        with self.assertRaisesRegex(StorageError, "newer than this program"):
            Store.open(path)

    def test_refuses_non_database_file(self):
        path = self.root / "notes.txt"
        path.write_text("not a database " * 100)
        with self.assertRaises(StorageError):
            Store.open(path)

    def test_second_writer_gets_storage_error_not_raw_sqlite(self):
        path = self.root / "busy.db"
        first, second = Store.open(path), Store.open(path)
        second._conn.execute("PRAGMA busy_timeout = 50")
        try:
            with first.transaction():
                with self.assertRaises(StorageError):
                    with second.transaction():
                        pass
        finally:
            first.close()
            second.close()


if __name__ == "__main__":
    unittest.main()
