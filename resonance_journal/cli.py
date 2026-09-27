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
"""Command-line front end: parse, gather text, call the service, render.

Holds no domain rules and no SQL. Exit codes: 0 ok, 1 JournalError, 2 usage.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Sequence, TextIO

from . import __version__
from .export import export_entries
from .model import (
    Entry,
    EntryDraft,
    ExportFormat,
    JournalError,
    SearchQuery,
    ValidationError,
    Visibility,
    utcnow,
)
from .service import Journal
from .store import Store

TextSource = Callable[[str], str]


def default_db_path() -> Path:
    env = os.environ.get("RESONANCE_JOURNAL_DB")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "resonance-journal" / "journal.db"


def edit_in_editor(initial: str) -> str:
    """TextSource backed by $VISUAL / $EDITOR / vi. Contracts C-P3."""
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    fd, path = tempfile.mkstemp(prefix="rj-", suffix=".md")  # created 0600
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(initial)
        result = subprocess.run([*shlex.split(editor), path])
        if result.returncode != 0:
            raise ValidationError(f"aborted: editor exited with status {result.returncode}")
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def split_title_body(text: str) -> tuple[str, str]:
    """Editor buffer format: first line is the title, then a blank line, then the body."""
    if not text.strip():
        raise ValidationError("aborted: empty entry")
    lines = text.strip("\n").split("\n")
    title = lines[0].lstrip("# ").strip()
    body = "\n".join(lines[1:]).strip("\n")
    return title, (body + "\n" if body else "")


# --- rendering --------------------------------------------------------------

def _mark(entry: Entry) -> str:
    return " [archived]" if entry.archived else ""


def render_line(entry: Entry) -> str:
    tags = " ".join(f"#{t}" for t in entry.tags)
    return f"{entry.id:>4}  {entry.created_at[:10]}  {entry.title}{_mark(entry)}" + (f"  {tags}" if tags else "")


def render_entry(entry: Entry) -> str:
    out = [
        f"#{entry.id}  {entry.title}{_mark(entry)}",
        f"created {entry.created_at}   updated {entry.updated_at}"
        + (f"   archived {entry.archived_at}" if entry.archived else ""),
    ]
    if entry.tags:
        out.append("tags: " + " ".join(f"#{t}" for t in entry.tags))
    out += ["", entry.body.rstrip("\n") if entry.body else "(no body)"]
    for label, links, attr in (("links", entry.links, "target_id"), ("backlinks", entry.backlinks, "source_id")):
        if links:
            out += ["", f"{label}:"]
            for link in links:
                note = f" — {link.note}" if link.note else ""
                gone = " [archived]" if link.other_archived else ""
                out.append(f"  {'→' if label == 'links' else '←'} {getattr(link, attr)}  {link.other_title}{gone}{note}")
    return "\n".join(out)


# --- argument parsing -------------------------------------------------------

def _entry_id(text: str) -> int:
    try:
        value = int(text.lstrip("#"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an entry id: {text!r}")
    if value < 1:
        raise argparse.ArgumentTypeError(f"not an entry id: {text!r}")
    return value


def _positive(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def _add_visibility(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group()
    g.add_argument("--archived", dest="visibility", action="store_const", const=Visibility.ARCHIVED,
                   help="only archived entries")
    g.add_argument("--all", dest="visibility", action="store_const", const=Visibility.ALL,
                   help="active and archived entries")
    p.set_defaults(visibility=Visibility.ACTIVE)


def _add_body(p: argparse.ArgumentParser) -> None:
    g = p.add_mutually_exclusive_group()
    g.add_argument("--body", help="entry text")
    g.add_argument("--body-file", metavar="PATH", help="read entry text from PATH ('-' for stdin)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rj", description="Resonance Journal: a local-first journal.")
    parser.add_argument("--db", type=Path, help="journal file (default: $RESONANCE_JOURNAL_DB or "
                        "$XDG_DATA_HOME/resonance-journal/journal.db)")
    parser.add_argument("--version", action="version", version=f"rj {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p = sub.add_parser("new", help="create an entry")
    p.add_argument("title", nargs="?", help="title (omit to write title and body in $EDITOR)")
    _add_body(p)
    p.add_argument("-t", "--tag", action="append", default=[], help="tag (repeatable)")

    p = sub.add_parser("edit", help="edit an entry's title and/or body")
    p.add_argument("id", type=_entry_id)
    p.add_argument("--title")
    _add_body(p)

    p = sub.add_parser("show", help="view one entry with its links and backlinks")
    p.add_argument("id", type=_entry_id)

    p = sub.add_parser("list", help="list entries, newest first")
    _add_visibility(p)
    p.add_argument("-n", "--limit", type=_positive)

    p = sub.add_parser("search", help="find entries containing every term")
    p.add_argument("terms", nargs="*")
    p.add_argument("-t", "--tag", action="append", default=[], help="require tag (repeatable)")
    _add_visibility(p)
    p.add_argument("-n", "--limit", type=_positive)

    p = sub.add_parser("tag", help="add tags to an entry")
    p.add_argument("id", type=_entry_id)
    p.add_argument("tags", nargs="+", metavar="TAG")
    p = sub.add_parser("untag", help="remove tags from an entry")
    p.add_argument("id", type=_entry_id)
    p.add_argument("tags", nargs="+", metavar="TAG")

    p = sub.add_parser("tags", help="list tags with entry counts")
    _add_visibility(p)

    p = sub.add_parser("link", help="link entry A to entry B")
    p.add_argument("source", type=_entry_id)
    p.add_argument("target", type=_entry_id)
    p.add_argument("--note", default="", help="why they resonate")

    p = sub.add_parser("unlink", help="remove the link from A to B")
    p.add_argument("source", type=_entry_id)
    p.add_argument("target", type=_entry_id)

    p = sub.add_parser("archive", help="hide an entry from list/search/export (reversible)")
    p.add_argument("id", type=_entry_id)
    p = sub.add_parser("unarchive", help="restore an archived entry")
    p.add_argument("id", type=_entry_id)

    p = sub.add_parser("export", help="export entries to Markdown files or JSON")
    p.add_argument("--format", choices=[f.value for f in ExportFormat], default="md")
    p.add_argument("--out", type=Path, required=True, help="target directory (md) or file (json)")
    p.add_argument("-t", "--tag", action="append", default=[], help="only entries with tag")
    p.add_argument("--force", action="store_true", help="replace an existing export")
    _add_visibility(p)
    return parser


# --- handlers ---------------------------------------------------------------

def _read_body(args: argparse.Namespace, stdin: TextIO) -> str | None:
    if args.body is not None:
        return args.body
    if args.body_file == "-":
        return stdin.read()
    if args.body_file:
        try:
            return Path(args.body_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValidationError(f"cannot read {args.body_file}: {exc.strerror}") from exc
    return None


def run(args: argparse.Namespace, journal: Journal, out: TextIO, stdin: TextIO, editor: TextSource) -> None:
    cmd = args.command
    if cmd == "new":
        body = _read_body(args, stdin)
        title = args.title
        if title is None:
            title, body = split_title_body(editor(""))
        elif body is None:
            if stdin.isatty():
                title, body = split_title_body(editor(title + "\n\n"))
            else:
                body = stdin.read()
        entry = journal.create(EntryDraft(title=title, body=body, tags=tuple(args.tag)))
        print(f"created #{entry.id}", file=out)
    elif cmd == "edit":
        body = _read_body(args, stdin)
        if args.title is None and body is None:
            current = journal.get(args.id)
            title, body = split_title_body(editor(f"{current.title}\n\n{current.body}"))
            entry = journal.edit(args.id, title=title, body=body)
        else:
            entry = journal.edit(args.id, title=args.title, body=body)
        print(f"saved #{entry.id} (updated {entry.updated_at})", file=out)
    elif cmd == "show":
        print(render_entry(journal.get(args.id)), file=out)
    elif cmd in ("list", "search"):
        query = SearchQuery(
            terms=tuple(getattr(args, "terms", ())),
            tags=tuple(getattr(args, "tag", ())),
            visibility=args.visibility,
            limit=args.limit,
        )
        entries = journal.search(query)
        for entry in entries:
            print(render_line(entry), file=out)
        if not entries:
            print("no entries", file=out)
    elif cmd in ("tag", "untag"):
        if cmd == "tag":
            entry = journal.tag(args.id, add=args.tags)
        else:
            entry = journal.tag(args.id, remove=args.tags)
        print(f"#{entry.id} tags: " + (" ".join(f"#{t}" for t in entry.tags) or "(none)"), file=out)
    elif cmd == "tags":
        counts = journal.tags(args.visibility)
        for name, n in counts:
            print(f"{n:>4}  #{name}", file=out)
        if not counts:
            print("no tags", file=out)
    elif cmd == "link":
        journal.link(args.source, args.target, args.note)
        print(f"linked #{args.source} → #{args.target}", file=out)
    elif cmd == "unlink":
        journal.unlink(args.source, args.target)
        print(f"unlinked #{args.source} → #{args.target}", file=out)
    elif cmd == "archive":
        journal.archive(args.id)
        print(f"archived #{args.id}", file=out)
    elif cmd == "unarchive":
        journal.unarchive(args.id)
        print(f"unarchived #{args.id}", file=out)
    elif cmd == "export":
        entries = journal.search(SearchQuery(tags=tuple(args.tag), visibility=args.visibility))
        path = export_entries(entries, ExportFormat(args.format), args.out, now=utcnow(), force=args.force)
        print(f"exported {len(entries)} entries to {path}", file=out)


def main(
    argv: Sequence[str] | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
    stdin: TextIO | None = None,
    editor: TextSource = edit_in_editor,
) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    stdin = stdin or sys.stdin
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse: --help/--version exit 0, usage errors exit 2
        return int(exc.code or 0)
    store = None
    try:
        store = Store.open(args.db or default_db_path())
        run(args, Journal(store), out, stdin, editor)
        return 0
    except JournalError as exc:
        print(f"error: {exc}", file=err)  # C-P4: messages name ids/paths, never content
        return 1
    finally:
        if store is not None:
            store.close()
