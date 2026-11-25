import json
import sqlite3
import zlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from mezzala.core.players import (
    ATTRIBUTE_NAMES,
    POSITION_CODES,
    Budget,
    Match,
    Player,
    ReleaseClause,
    ReleaseScope,
    Snapshot,
    Vacancy,
)

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
    club_nation_id INTEGER,
    format INTEGER NOT NULL DEFAULT 1,
    vacancies TEXT,
    matches TEXT,
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


def encode_match(match: Match) -> list[Any]:
    return [
        match.day.isoformat(), match.competition_id, match.home_club_uid, match.home_club_name, match.away_club_uid,
        match.away_club_name, match.played, match.home_goals, match.away_goals, match.neutral,
    ]  # fmt: skip


def decode_match(stored: list[Any]) -> Match:
    day, competition, home_uid, home_name, away_uid, away_name, played, home_goals, away_goals, *rest = stored
    return Match(date.fromisoformat(day), competition, home_uid, home_name, away_uid, away_name, played, home_goals,
                 away_goals, bool(rest[0]) if rest else False)  # fmt: skip


def encode_vacancy(vacancy: Vacancy) -> list[Any]:
    return [
        vacancy.club_uid, vacancy.club_name, vacancy.club_reputation, optional_text(vacancy.advertised),
        vacancy.balance, vacancy.transfer_budget,
    ]  # fmt: skip


def decode_vacancy(stored: list[Any]) -> Vacancy:
    club_uid, club_name, reputation, advertised, balance, transfer_budget = stored
    return Vacancy(club_uid, club_name, reputation, optional_date(advertised), balance, transfer_budget)


def encode_clause(clause: ReleaseClause) -> list[Any]:
    return [clause.scope.value, clause.fee, optional_text(clause.expires)]


def encode_player(player: Player) -> list[Any]:
    return [
        player.uid, player.name, player.age, optional_text(player.birth_date), player.club_uid, player.club_name,
        [player.position_ratings[code] for code in POSITION_CODES], player.current_ability,
        player.potential_ability, player.value, player.wage, optional_text(player.contract_end), player.on_loan,
        player.loan_parent_club_uid, optional_text(player.loan_end),
        [player.attributes[name] for name in ATTRIBUTE_NAMES], player.reputation, player.professionalism,
        player.ambition, player.first_team, player.club_reputation, player.club_nation_id, player.league_id,
        player.youth_contract, [encode_clause(clause) for clause in player.release_clauses],
        player.loan_wage,
    ]  # fmt: skip


ORIGINAL_FIELDS = 19
FACTS_ADDED_LATER: list[Any] = [None, None, None, None, None, [], None]
CURRENT_FORMAT = 7
COLUMNS_ADDED_LATER = {
    "club_nation_id": "INTEGER",
    "format": "INTEGER NOT NULL DEFAULT 1",
    "vacancies": "TEXT",
    "matches": "TEXT",
}


def add_column(db: sqlite3.Connection, name: str, definition: str) -> None:
    try:
        db.execute(f"ALTER TABLE snapshots ADD COLUMN {name} {definition}")
    except sqlite3.OperationalError as error:
        if "duplicate column" not in str(error):
            raise


def decode_clause(stored: list[Any]) -> ReleaseClause:
    scope, fee, *expiry = stored
    return ReleaseClause(ReleaseScope(scope), fee, optional_date(expiry[0]) if expiry else None)


def decode_player(row: list[Any]) -> Player:
    row = [*row, *FACTS_ADDED_LATER[len(row) - ORIGINAL_FIELDS :]]
    (uid, name, age, birth_date, club_uid, club_name, ratings, current, potential, value, wage, contract_end,
     on_loan, loan_parent, loan_end, attributes, reputation, professionalism, ambition, first_team,
     club_reputation, club_nation_id, league_id, youth_contract, clauses, loan_wage) = row  # fmt: skip
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
        first_team=first_team,
        club_reputation=club_reputation,
        club_nation_id=club_nation_id,
        league_id=league_id,
        youth_contract=youth_contract,
        release_clauses=tuple(decode_clause(clause) for clause in clauses),
        loan_wage=loan_wage,
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
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(snapshots)")}
        for name, definition in COLUMNS_ADDED_LATER.items():
            if name not in columns:
                add_column(self._db, name, definition)

    def close(self) -> None:
        self._db.close()

    def latest_stamp(self, career: str) -> FileStamp | None:
        row = self._db.execute(
            "SELECT file_mtime_ns, file_size, format FROM snapshots WHERE career = ? ORDER BY id DESC LIMIT 1",
            (career,),
        ).fetchone()
        if row is None or row[2] != CURRENT_FORMAT:
            return None
        return FileStamp(row[0], row[1])

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
                "club_reputation, club_nation_id, format, budget, players, vacancies, matches) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    career, snapshot.game_date.isoformat(), stamp.mtime_ns, stamp.size, snapshot.club_uid,
                    snapshot.club_name,
                    snapshot.club_reputation,
                    snapshot.club_nation_id,
                    CURRENT_FORMAT,
                    json.dumps([budget.transfer_remaining, budget.wage_budget_weekly, budget.wage_payroll_weekly]),
                    encode_players(snapshot.players),
                    json.dumps([encode_vacancy(vacancy) for vacancy in snapshot.vacancies]),
                    json.dumps([encode_match(match) for match in snapshot.matches]),
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
            "SELECT club_uid, club_name, club_reputation, club_nation_id, budget, players, vacancies, matches "
            "FROM snapshots "
            "WHERE career = ? AND game_date = ?",
            (career, game_date.isoformat()),
        ).fetchone()
        if row is None:
            raise KeyError(f"No snapshot of {career} on {game_date.isoformat()}")
        club_uid, club_name, reputation, nation_id, budget, players, vacancies, matches = row
        return Snapshot(
            game_date,
            club_uid,
            club_name,
            reputation,
            nation_id,
            Budget(*json.loads(budget)),
            decode_players(players),
            tuple(decode_vacancy(vacancy) for vacancy in json.loads(vacancies or "[]")),
            tuple(decode_match(match) for match in json.loads(matches or "[]")),
        )
