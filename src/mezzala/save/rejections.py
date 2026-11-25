import sqlite3
import threading
from datetime import date
from pathlib import Path

from mezzala.core.players import RejectedPlayer

SCHEMA = """
CREATE TABLE IF NOT EXISTS rejected (
    career TEXT NOT NULL,
    uid INTEGER NOT NULL,
    birth_date TEXT,
    name TEXT NOT NULL,
    added_on TEXT NOT NULL,
    note TEXT NOT NULL,
    PRIMARY KEY (career, uid)
)
"""


class RejectionStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(SCHEMA)
        self._lock = threading.Lock()

    def add(self, career: str, rejected: RejectedPlayer) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO rejected (career, uid, birth_date, name, added_on, note) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (career, uid) DO UPDATE SET note = excluded.note",
                (
                    career, rejected.uid, rejected.birth_date.isoformat() if rejected.birth_date else None,
                    rejected.name, rejected.added_on.isoformat(), rejected.note,
                ),
            )  # fmt: skip

    def remove(self, career: str, uid: int) -> bool:
        with self._lock, self._db:
            return self._db.execute("DELETE FROM rejected WHERE career = ? AND uid = ?", (career, uid)).rowcount > 0

    def entries(self, career: str) -> list[RejectedPlayer]:
        with self._lock:
            rows = self._db.execute(
                "SELECT uid, birth_date, name, added_on, note FROM rejected WHERE career = ? ORDER BY added_on, name",
                (career,),
            ).fetchall()
        return [
            RejectedPlayer(uid, date.fromisoformat(born) if born else None, name, date.fromisoformat(added), note)
            for uid, born, name, added, note in rows
        ]
