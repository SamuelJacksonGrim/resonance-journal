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
