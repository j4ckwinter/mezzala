import json
import sqlite3
import zlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from mezzala.players import ATTRIBUTE_NAMES, POSITION_CODES, Budget, Player, Snapshot

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career TEXT NOT NULL,
    game_date TEXT NOT NULL,
    file_mtime_ns INTEGER NOT NULL,
    file_size INTEGER NOT NULL,
    club_uid INTEGER NOT NULL,
    club_name TEXT NOT NULL,
    club_reputation INTEGER NOT NULL,
    budget TEXT NOT NULL,
    players BLOB NOT NULL,
    UNIQUE (career, game_date)
)
"""


@dataclass(frozen=True)
class FileStamp:
    mtime_ns: int
    size: int


def optional_date(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def optional_text(day: date | None) -> str | None:
    return day.isoformat() if day else None


def encode_player(player: Player) -> list[Any]:
    return [
        player.uid, player.name, player.age, optional_text(player.birth_date), player.club_uid, player.club_name,
        [player.position_ratings[code] for code in POSITION_CODES], player.current_ability,
        player.potential_ability, player.value, player.wage, optional_text(player.contract_end), player.on_loan,
        player.loan_parent_club_uid, optional_text(player.loan_end),
        [player.attributes[name] for name in ATTRIBUTE_NAMES], player.reputation, player.professionalism,
        player.ambition,
    ]  # fmt: skip


def decode_player(row: list[Any]) -> Player:
    (uid, name, age, birth_date, club_uid, club_name, ratings, current, potential, value, wage, contract_end,
     on_loan, loan_parent, loan_end, attributes, reputation, professionalism, ambition) = row  # fmt: skip
    return Player(
        uid=uid,
        name=name,
        age=age,
        birth_date=optional_date(birth_date),
        club_uid=club_uid,
        club_name=club_name,
        position_ratings=dict(zip(POSITION_CODES, ratings, strict=True)),
        current_ability=current,
        potential_ability=potential,
        value=value,
        wage=wage,
        contract_end=optional_date(contract_end),
        on_loan=on_loan,
        loan_parent_club_uid=loan_parent,
        loan_end=optional_date(loan_end),
        attributes=dict(zip(ATTRIBUTE_NAMES, attributes, strict=True)),
        reputation=reputation,
        professionalism=professionalism,
        ambition=ambition,
    )


def encode_players(players: tuple[Player, ...]) -> bytes:
    return zlib.compress(json.dumps([encode_player(p) for p in players], separators=(",", ":")).encode())


def decode_players(blob: bytes) -> tuple[Player, ...]:
    return tuple(decode_player(row) for row in json.loads(zlib.decompress(blob)))


class SnapshotStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def latest_stamp(self, career: str) -> FileStamp | None:
        row = self._db.execute(
            "SELECT file_mtime_ns, file_size FROM snapshots WHERE career = ? ORDER BY id DESC LIMIT 1", (career,)
        ).fetchone()
        return FileStamp(row[0], row[1]) if row else None

    def latest_date(self, career: str) -> date | None:
        row = self._db.execute(
            "SELECT game_date FROM snapshots WHERE career = ? ORDER BY id DESC LIMIT 1", (career,)
        ).fetchone()
        return date.fromisoformat(row[0]) if row else None

    def put(self, career: str, snapshot: Snapshot, stamp: FileStamp) -> None:
        budget = snapshot.budget
        with self._db:
            self._db.execute(
                "DELETE FROM snapshots WHERE career = ? AND game_date = ?", (career, snapshot.game_date.isoformat())
            )
            self._db.execute(
                "INSERT INTO snapshots (career, game_date, file_mtime_ns, file_size, club_uid, club_name, "
                "club_reputation, budget, players) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    career, snapshot.game_date.isoformat(), stamp.mtime_ns, stamp.size, snapshot.club_uid,
                    snapshot.club_name,
                    snapshot.club_reputation,
                    json.dumps([budget.transfer_remaining, budget.wage_budget_weekly, budget.wage_payroll_weekly]),
                    encode_players(snapshot.players),
                ),
            )  # fmt: skip

    def snapshot_id(self, career: str, game_date: date) -> int:
        row = self._db.execute(
            "SELECT id FROM snapshots WHERE career = ? AND game_date = ?", (career, game_date.isoformat())
        ).fetchone()
        if row is None:
            raise KeyError(f"No snapshot of {career} on {game_date.isoformat()}")
        return row[0]

    def dates(self, career: str) -> list[date]:
        rows = self._db.execute("SELECT game_date FROM snapshots WHERE career = ? ORDER BY game_date", (career,))
        return [date.fromisoformat(row[0]) for row in rows]

    def load(self, career: str, game_date: date) -> Snapshot:
        row = self._db.execute(
            "SELECT club_uid, club_name, club_reputation, budget, players FROM snapshots "
            "WHERE career = ? AND game_date = ?",
            (career, game_date.isoformat()),
        ).fetchone()
        if row is None:
            raise KeyError(f"No snapshot of {career} on {game_date.isoformat()}")
        club_uid, club_name, reputation, budget, players = row
        return Snapshot(
            game_date, club_uid, club_name, reputation, Budget(*json.loads(budget)), decode_players(players)
        )
