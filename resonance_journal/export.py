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
"""Render entries to Markdown or JSON and write them safely.

The only module that writes journal content outside the DB. It renders what it
is given and never queries. See Contracts G4, C-P2, and D-006.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

from .model import Entry, ExportError, ExportFormat, Timestamp

JSON_FORMAT_ID = "resonance-journal/v1"
MARKER = ".resonance-export"


def export_entries(
    entries: Sequence[Entry],
    fmt: ExportFormat,
    out: Path,
    now: Timestamp,
    force: bool = False,
) -> Path:
    out = Path(out)
    if not out.parent.is_dir():
        raise ExportError(f"parent directory {out.parent} does not exist")
    try:
        if fmt is ExportFormat.JSON:
            return _export_json(entries, out, now, force)
        return _export_markdown(entries, out, force)
    except OSError as exc:
        raise ExportError(f"cannot write export to {out}: {exc.strerror or exc}") from exc


# --- JSON -------------------------------------------------------------------

def entry_to_dict(entry: Entry) -> dict:
    return {
        "id": entry.id,
        "title": entry.title,
        "body": entry.body,
        "tags": list(entry.tags),
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "archived_at": entry.archived_at,
        "links": [{"target_id": l.target_id, "note": l.note} for l in entry.links],
    }


def _export_json(entries: Sequence[Entry], out: Path, now: Timestamp, force: bool) -> Path:
    if out.exists():
        if out.is_dir():
            raise ExportError(f"{out} is a directory; JSON export writes a single file")
        if not force:
            raise ExportError(f"{out} already exists (use --force to replace it)")
    doc = {
        "format": JSON_FORMAT_ID,
        "exported_at": now,
        "entries": [entry_to_dict(e) for e in entries],
    }
    fd, tmp = tempfile.mkstemp(prefix=f".{out.name}.", suffix=".tmp", dir=out.parent)  # 0600
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, out)
    except BaseException:
        _silent_unlink(tmp)
        raise
    return out


# --- Markdown ---------------------------------------------------------------

def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].rstrip("-")
    return slug or "entry"


def entry_filename(entry: Entry) -> str:
    return f"{entry.id:04d}-{slugify(entry.title)}.md"


def entry_to_markdown(entry: Entry) -> str:
    front = [
        "---",
        f"id: {entry.id}",
        f"title: {json.dumps(entry.title, ensure_ascii=False)}",
        f"tags: [{', '.join(entry.tags)}]",
        f"created_at: {entry.created_at}",
        f"updated_at: {entry.updated_at}",
        f"archived_at: {entry.archived_at or 'null'}",
        f"links: [{', '.join(str(l.target_id) for l in entry.links)}]",
        "---",
        "",
    ]
    return "\n".join(front) + "\n" + entry.body


def index_markdown(entries: Sequence[Entry]) -> str:
    lines = ["# Resonance Journal export", ""]
    for e in entries:
        tags = " ".join(f"`#{t}`" for t in e.tags)
        flag = " *(archived)*" if e.archived else ""
        lines.append(f"- [{e.title}]({entry_filename(e)}) — {e.created_at[:10]}{flag} {tags}".rstrip())
    return "\n".join(lines) + "\n"


def _export_markdown(entries: Sequence[Entry], out: Path, force: bool) -> Path:
    if out.exists():
        if not force:
            raise ExportError(f"{out} already exists (use --force to replace a previous export)")
        if not (out.is_dir() and (out / MARKER).is_file()):
            raise ExportError(f"refusing to replace {out}: it is not a Resonance Journal export")
    tmp = Path(tempfile.mkdtemp(prefix=f".{out.name}.", suffix=".tmp", dir=out.parent))  # 0700
    try:
        _write_private(tmp / MARKER, "")
        _write_private(tmp / "index.md", index_markdown(entries))
        for entry in entries:
            _write_private(tmp / entry_filename(entry), entry_to_markdown(entry))
        if out.exists():
            old = Path(tempfile.mkdtemp(prefix=f".{out.name}.", suffix=".old", dir=out.parent))
            os.rmdir(old)
            os.rename(out, old)
            try:
                os.rename(tmp, out)
            except OSError:
                os.rename(old, out)  # put the previous export back
                raise
            shutil.rmtree(old)
        else:
            os.rename(tmp, out)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return out


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _silent_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
