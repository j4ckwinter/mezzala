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
    save_path: Path
    career: str
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
        locate: Callable[[], Path],
        store: SnapshotStore,
        read: Callable[[Path], Snapshot],
        stamp: Callable[[Path], FileStamp] = file_stamp,
    ) -> None:
        self._locate = locate
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

    def _load(self, career: str, game_date: date) -> Snapshot:
        stored = self._store.snapshot_id(career, game_date)
        cached = self._loaded.get(stored)
        return self._remember(stored, cached or self._store.load(career, game_date))

    def _refresh(self, path: Path, career: str, stamp: FileStamp) -> Snapshot:
        snapshot = self._read(path)
        self._store.put(career, snapshot, stamp)
        return self._remember(self._store.snapshot_id(career, snapshot.game_date), snapshot)

    def current(self) -> Current:
        with self._lock:
            return self._current()

    def _current(self) -> Current:
        path = self._locate()
        career = str(path.resolve())
        notes: list[str] = []
        latest = self._store.latest_date(career)
        try:
            stamp = self._stamp(path)
            if latest is not None and self._store.latest_stamp(career) == stamp:
                snapshot = self._load(career, latest)
            else:
                snapshot = self._refresh(path, career, stamp)
        except (fmsave.FmsaveError, UnreadableSave, OSError) as error:
            if latest is None:
                raise
            snapshot = self._load(career, latest)
            notes.append(f"Could not read the save ({error}); using the snapshot from {latest.isoformat()}.")
        earlier = [day for day in self._store.dates(career) if day < snapshot.game_date]
        return Current(path, career, snapshot, len(earlier) + 1, notes)

    def earlier_dates(self, current: Current) -> list[date]:
        with self._lock:
            return self._earlier_dates(current)

    def _earlier_dates(self, current: Current) -> list[date]:
        return [day for day in self._store.dates(current.career) if day < current.snapshot.game_date]

    def baseline(self, current: Current, since: date | None) -> Snapshot | None:
        with self._lock:
            dates = self._earlier_dates(current)
            if since is not None:
                dates = [day for day in dates if day <= since] or dates[:1]
            if not dates:
                return None
            return self._load(current.career, dates[-1] if since is not None else dates[0])

    def past_players(self, current: Current, uids: set[int]) -> list[PastPlayers]:
        with self._lock:
            found: list[PastPlayers] = []
            for day in spread(self._earlier_dates(current), MAX_HISTORY_SNAPSHOTS):
                players = self._store.load(current.career, day).players
                found.append(PastPlayers(day, {p.uid: p for p in players if p.uid in uids}))
            return found
