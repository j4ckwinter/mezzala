from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import fmsave

from mezzala.players import Snapshot
from mezzala.reader import UnreadableSave
from mezzala.store import FileStamp, SnapshotStore


@dataclass(frozen=True)
class Current:
    snapshot: Snapshot
    snapshot_count: int
    notes: list[str]


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
        self._loaded: dict[date, Snapshot] = {}

    def _load(self, game_date: date) -> Snapshot:
        if game_date not in self._loaded:
            self._loaded[game_date] = self._store.load(self.name, game_date)
        return self._loaded[game_date]

    def _refresh(self, stamp: FileStamp) -> Snapshot:
        snapshot = self._read(self.save_path)
        self._store.put(self.name, snapshot, stamp)
        self._loaded[snapshot.game_date] = snapshot
        return snapshot

    def current(self) -> Current:
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
        return [day for day in self._store.dates(self.name) if day < current.game_date]

    def baseline(self, current: Snapshot, since: date | None) -> Snapshot | None:
        dates = self.earlier_dates(current)
        if since is not None:
            dates = [day for day in dates if day <= since] or dates[:1]
        if not dates:
            return None
        return self._load(dates[-1] if since is not None else dates[0])

    def history(self, current: Snapshot) -> list[Snapshot]:
        return [self._load(day) for day in self.earlier_dates(current)]
