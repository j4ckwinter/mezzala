import json
import sqlite3
import zlib
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path
from typing import Any

from mezzala.core.players import (
    ATTRIBUTE_NAMES,
    POSITION_CODES,
    Budget,
    Injury,
    Match,
    MentoringGroup,
    Player,
    ReleaseClause,
    ReleaseScope,
    SeasonStats,
    Snapshot,
    StaffMember,
    Tactic,
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
    staff TEXT,
    tactics TEXT,
    mentoring TEXT,
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
        match.away_club_name, match.played, match.home_goals, match.away_goals, match.neutral, match.home_team_slot,
        match.away_team_slot,
    ]  # fmt: skip


def decode_match(stored: list[Any]) -> Match:
    day, competition, home_uid, home_name, away_uid, away_name, played, home_goals, away_goals, *later = stored
    neutral, home_slot, away_slot = [*later, *MATCH_FACTS_ADDED_LATER[len(later) :]]
    return Match(date.fromisoformat(day), competition, home_uid, home_name, away_uid, away_name, played, home_goals,
                 away_goals, bool(neutral), home_slot, away_slot)  # fmt: skip


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


def encode_injury(injury: Injury) -> list[Any]:
    return [injury.day.isoformat(), injury.severity, injury.cause]


def decode_injury(stored: list[Any]) -> Injury:
    day, severity, cause = stored
    return Injury(date.fromisoformat(day), severity, cause)


SEASON_STAT_FIELDS = tuple(field.name for field in fields(SeasonStats))


def encode_season(season: SeasonStats | None) -> list[Any] | None:
    return None if season is None else [getattr(season, name) for name in SEASON_STAT_FIELDS]


def decode_season(stored: list[Any] | None) -> SeasonStats | None:
    return None if stored is None else SeasonStats(*stored)


def encode_staff(member: StaffMember) -> list[Any]:
    return [member.name, member.job, member.age, dict(member.ratings)]


def decode_staff(stored: list[Any]) -> StaffMember:
    name, job, age, ratings = stored
    return StaffMember(name, job, age, ratings)


def encode_tactic(tactic: Tactic) -> list[Any]:
    return [tactic.name, tactic.mentality, list(tactic.positions)]


def decode_tactic(stored: list[Any]) -> Tactic:
    name, mentality, positions = stored
    return Tactic(name, mentality, tuple(positions))


def encode_mentoring(group: MentoringGroup) -> list[Any]:
    return [group.label, list(group.member_uids)]


def decode_mentoring(stored: list[Any]) -> MentoringGroup:
    label, members = stored
    return MentoringGroup(label, tuple(members))


def encode_player(player: Player) -> list[Any]:
    return [
        player.uid, player.name, player.age, optional_text(player.birth_date), player.club_uid, player.club_name,
        [player.position_ratings[code] for code in POSITION_CODES], player.current_ability,
        player.potential_ability, player.value, player.wage, optional_text(player.contract_end), player.on_loan,
        player.loan_parent_club_uid, optional_text(player.loan_end),
        [player.attributes[name] for name in ATTRIBUTE_NAMES], player.reputation, player.professionalism,
        player.ambition, player.first_team, player.club_reputation, player.club_nation_id, player.league_id,
        player.youth_contract, [encode_clause(clause) for clause in player.release_clauses],
        player.loan_wage, player.adaptability, player.loyalty, player.pressure, player.sportsmanship,
        player.temperament, player.controversy, player.left_foot, player.right_foot, player.height_cm,
        list(player.traits), player.condition, player.match_sharpness, list(player.banned_from), player.injury,
        optional_text(player.injured_until), [encode_injury(injury) for injury in player.injuries],
        encode_season(player.season), list(player.nationalities), player.club_country, player.squad_status,
    ]  # fmt: skip


ORIGINAL_FIELDS = 19
FACTS_ADDED_LATER: list[Any] = [
    None,
    None,
    None,
    None,
    None,
    [],
    None,
    *[None] * 9,
    [],
    None,
    None,
    [],
    None,
    None,
    [],
    None,
    [],
    None,
    None,
]
CURRENT_FORMAT = 12
MATCH_FACTS_ADDED_LATER: list[Any] = [False, 0, 0]
COLUMNS_ADDED_LATER = {
    "club_nation_id": "INTEGER",
    "format": "INTEGER NOT NULL DEFAULT 1",
    "vacancies": "TEXT",
    "matches": "TEXT",
    "staff": "TEXT",
    "tactics": "TEXT",
    "mentoring": "TEXT",
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
     club_reputation, club_nation_id, league_id, youth_contract, clauses, loan_wage, adaptability, loyalty,
     pressure, sportsmanship, temperament, controversy, left_foot, right_foot, height_cm, traits, condition,
     match_sharpness, banned_from, injury, injured_until, injuries, season, nationalities,
     club_country, squad_status) = row  # fmt: skip
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
        adaptability=adaptability,
        loyalty=loyalty,
        pressure=pressure,
        sportsmanship=sportsmanship,
        temperament=temperament,
        controversy=controversy,
        left_foot=left_foot,
        right_foot=right_foot,
        height_cm=height_cm,
        traits=tuple(traits),
        condition=condition,
        match_sharpness=match_sharpness,
        banned_from=tuple(banned_from),
        injury=injury,
        injured_until=optional_date(injured_until),
        injuries=tuple(decode_injury(stored) for stored in injuries),
        season=decode_season(season),
        nationalities=tuple(nationalities),
        club_country=club_country,
        squad_status=squad_status,
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
                "club_reputation, club_nation_id, format, budget, players, vacancies, matches, staff, tactics, "
                "mentoring) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    json.dumps([encode_staff(member) for member in snapshot.staff]),
                    json.dumps([encode_tactic(tactic) for tactic in snapshot.tactics]),
                    json.dumps([encode_mentoring(group) for group in snapshot.mentoring]),
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
            "SELECT club_uid, club_name, club_reputation, club_nation_id, budget, players, vacancies, matches, "
            "staff, tactics, mentoring "
            "FROM snapshots "
            "WHERE career = ? AND game_date = ?",
            (career, game_date.isoformat()),
        ).fetchone()
        if row is None:
            raise KeyError(f"No snapshot of {career} on {game_date.isoformat()}")
        club_uid, club_name, reputation, nation_id, budget, players, vacancies, matches, staff, tactics, mentoring = row
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
            tuple(decode_staff(member) for member in json.loads(staff or "[]")),
            tuple(decode_tactic(tactic) for tactic in json.loads(tactics or "[]")),
            tuple(decode_mentoring(group) for group in json.loads(mentoring or "[]")),
        )
