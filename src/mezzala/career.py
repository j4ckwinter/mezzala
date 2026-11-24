import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import fmsave

from mezzala.players import PastPlayers, Snapshot
from mezzala.reader import UnreadableSave
from mezzala.store import FileStamp, SnapshotStore

CACHED_SNAPSHOTS = 2
MAX_HISTORY_SNAPSHOTS = 12


@dataclass(frozen=True)
class Current:
    snapshot: Snapshot
    snapshot_count: int
    notes: list[str]


def spread(dates: list[date], count: int) -> list[date]:
    if len(dates) <= count:
        return dates
    last = len(dates) - 1
    return sorted({dates[round(step * last / (count - 1))] for step in range(count)})


def file_stamp(path: Path) -> FileStamp:
    stat = path.stat()
    return FileStamp(stat.st_mtime_ns, stat.st_size)


class Career:
    def __init__(
        self,
        save_path: Path,
        store: SnapshotStore,
        read: Callable[[Path], Snapshot],
        stamp: Callable[[Path], FileStamp] = file_stamp,
    ) -> None:
        self.save_path = save_path
        self.name = save_path.stem
        self._store = store
        self._read = read
        self._stamp = stamp
        self._loaded: dict[int, Snapshot] = {}
        self._lock = threading.Lock()

    def _remember(self, stored: int, snapshot: Snapshot) -> Snapshot:
        self._loaded.pop(stored, None)
        self._loaded[stored] = snapshot
        while len(self._loaded) > CACHED_SNAPSHOTS:
            del self._loaded[next(iter(self._loaded))]
        return snapshot

    def _load(self, game_date: date) -> Snapshot:
        stored = self._store.snapshot_id(self.name, game_date)
        cached = self._loaded.get(stored)
        return self._remember(stored, cached or self._store.load(self.name, game_date))

    def _refresh(self, stamp: FileStamp) -> Snapshot:
        snapshot = self._read(self.save_path)
        self._store.put(self.name, snapshot, stamp)
        return self._remember(self._store.snapshot_id(self.name, snapshot.game_date), snapshot)

    def current(self) -> Current:
        with self._lock:
            return self._current()

    def _current(self) -> Current:
        notes: list[str] = []
        stamp = self._stamp(self.save_path)
        latest = self._store.latest_date(self.name)
        if latest is not None and self._store.latest_stamp(self.name) == stamp:
            snapshot = self._load(latest)
        else:
            try:
                snapshot = self._refresh(stamp)
            except (fmsave.FmsaveError, UnreadableSave) as error:
                if latest is None:
                    raise
                snapshot = self._load(latest)
                notes.append(f"Could not read the save ({error}); using the snapshot from {latest.isoformat()}.")
        return Current(snapshot, len(self._store.dates(self.name)), notes)

    def earlier_dates(self, current: Snapshot) -> list[date]:
        with self._lock:
            return self._earlier_dates(current)

    def _earlier_dates(self, current: Snapshot) -> list[date]:
        return [day for day in self._store.dates(self.name) if day < current.game_date]

    def baseline(self, current: Snapshot, since: date | None) -> Snapshot | None:
        with self._lock:
            dates = self._earlier_dates(current)
            if since is not None:
                dates = [day for day in dates if day <= since] or dates[:1]
            if not dates:
                return None
            return self._load(dates[-1] if since is not None else dates[0])

    def past_players(self, current: Snapshot, uids: set[int]) -> list[PastPlayers]:
        with self._lock:
            found: list[PastPlayers] = []
            for day in spread(self._earlier_dates(current), MAX_HISTORY_SNAPSHOTS):
                players = self._store.load(self.name, day).players
                found.append(PastPlayers(day, {p.uid: p for p in players if p.uid in uids}))
            return found
