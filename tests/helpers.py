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
from resonance_journal.service import Journal
from resonance_journal.store import Store


class FakeClock:
    """Deterministic clock: each call advances one minute."""

    def __init__(self) -> None:
        self.minute = 0

    def __call__(self) -> str:
        self.minute += 1
        h, m = divmod(self.minute, 60)
        return f"2026-01-01T{h:02d}:{m:02d}:00Z"


def memory_journal() -> tuple[Journal, Store, FakeClock]:
    store = Store.open(":memory:")
    clock = FakeClock()
    return Journal(store, clock=clock), store, clock
