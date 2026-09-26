"""Enforce Dependencies.md and Contracts G1 on the source itself."""

import ast
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "resonance_journal"
NETWORK = {"socket", "http", "urllib", "ssl", "smtplib", "ftplib", "asyncio", "requests"}
STDLIB_OK = {
    "__future__", "argparse", "contextlib", "dataclasses", "datetime", "enum", "json", "os",
    "pathlib", "re", "shlex", "shutil", "sqlite3", "subprocess", "sys", "tempfile", "typing",
}
# module -> package-internal modules it may import
ALLOWED = {
    "model": set(),
    "store": {"model"},
    "service": {"model"},
    "export": {"model"},
    "cli": {"model", "service", "store", "export", "__init__"},
    "__main__": {"cli"},
    "__init__": set(),
}


def imports(path: Path) -> tuple[set[str], set[str]]:
    """Return (internal module names, top-level external module names)."""
    internal, external = set(), set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                if node.module:
                    internal.add(node.module.split(".")[0])
                else:
                    internal.update("__init__" if a.name == "__version__" else a.name for a in node.names)
            else:
                external.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            external.update(a.name.split(".")[0] for a in node.names)
    return internal, external


class BoundaryTest(unittest.TestCase):
    def test_every_module_is_classified(self):
        self.assertEqual({p.stem for p in PKG.glob("*.py")}, set(ALLOWED))

    def test_internal_import_directions(self):
        for path in PKG.glob("*.py"):
            internal, _ = imports(path)
            self.assertLessEqual(internal, ALLOWED[path.stem], f"{path.name} imports {internal}")

    def test_no_network_and_stdlib_only(self):  # G1, D-002
        for path in PKG.glob("*.py"):
            _, external = imports(path)
            self.assertFalse(external & NETWORK, f"{path.name} imports network module")
            self.assertLessEqual(external, STDLIB_OK, f"{path.name} imports {external - STDLIB_OK}")

    def test_only_store_speaks_sql(self):
        for path in PKG.glob("*.py"):
            if path.stem == "store":
                continue
            _, external = imports(path)
            self.assertNotIn("sqlite3", external, path.name)

    def test_cli_only_opens_and_closes_the_store(self):
        tree = ast.parse((PKG / "cli.py").read_text(encoding="utf-8"))
        uses = {
            n.attr for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in ("store", "Store")
        }
        self.assertLessEqual(uses, {"open", "close"})


if __name__ == "__main__":
    unittest.main()
