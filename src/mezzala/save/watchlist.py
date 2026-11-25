import sqlite3
import threading
from datetime import date
from pathlib import Path

from mezzala.core.players import WatchedPlayer

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    career TEXT NOT NULL,
    uid INTEGER NOT NULL,
    birth_date TEXT,
    name TEXT NOT NULL,
    added_on TEXT NOT NULL,
    value INTEGER,
    current_ability INTEGER NOT NULL,
    club_name TEXT,
    note TEXT NOT NULL,
    PRIMARY KEY (career, uid)
)
"""


class WatchlistStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(SCHEMA)
        self._lock = threading.Lock()

    def add(self, career: str, watched: WatchedPlayer) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO watchlist (career, uid, birth_date, name, added_on, value, current_ability, club_name, "
                "note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (career, uid) DO UPDATE SET note = excluded.note",
                (
                    career, watched.uid, watched.birth_date.isoformat() if watched.birth_date else None,
                    watched.name, watched.added_on.isoformat(), watched.value, watched.current_ability,
                    watched.club_name, watched.note,
                ),
            )  # fmt: skip

    def remove(self, career: str, uid: int) -> bool:
        with self._lock, self._db:
            removed = self._db.execute("DELETE FROM watchlist WHERE career = ? AND uid = ?", (career, uid))
            return removed.rowcount > 0

    def entries(self, career: str) -> list[WatchedPlayer]:
        with self._lock:
            rows = self._db.execute(
                "SELECT uid, birth_date, name, added_on, value, current_ability, club_name, note FROM watchlist "
                "WHERE career = ? ORDER BY added_on, name",
                (career,),
            ).fetchall()
        return [
            WatchedPlayer(uid, date.fromisoformat(born) if born else None, name, date.fromisoformat(added), value,
                          ability, club, note)
            for uid, born, name, added, value, ability, club, note in rows
        ]  # fmt: skip
