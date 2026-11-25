from datetime import date
from itertools import count
from typing import Any

from mezzala.core.players import ATTRIBUTE_NAMES, POSITION_CODES, Budget, Player, Snapshot

MY_CLUB = 1
MY_CLUB_NAME = "Paisley"
OTHER_CLUB = 2
MY_NATION = 167
MY_LEAGUE = 33
SEASON_START = date(2026, 6, 29)
_uids = count(1000)


def player(
    name: str,
    *,
    positions: tuple[str, ...] = ("dc",),
    age: int = 25,
    ca: int = 100,
    pa: int = 110,
    club: int | None = OTHER_CLUB,
    value: int | None = 500_000,
    contract_end: date | None = date(2029, 6, 30),
    attributes: dict[str, int] | None = None,
    **overrides: Any,
) -> Player:
    ratings = {code: (20 if code in positions else 1) for code in POSITION_CODES}
    profile = dict.fromkeys(ATTRIBUTE_NAMES, 10) | (attributes or {})
    fields: dict[str, Any] = {
        "uid": next(_uids),
        "name": name,
        "age": age,
        "birth_date": date(SEASON_START.year - age, 1, 1),
        "club_uid": club,
        "club_name": None if club is None else ("Paisley" if club == MY_CLUB else f"Club {club}"),
        "position_ratings": ratings,
        "current_ability": ca,
        "potential_ability": pa,
        "value": value,
        "wage": 2_000,
        "contract_end": contract_end,
        "on_loan": False,
        "loan_parent_club_uid": None,
        "loan_end": None,
        "attributes": profile,
        "reputation": 5_000,
        "professionalism": 10,
        "ambition": 10,
        "first_team": club is not None,
        "club_reputation": None if club is None else 5_000,
        "club_nation_id": None if club is None else MY_NATION,
        "league_id": None if club is None else MY_LEAGUE,
        "youth_contract": None if club is None else False,
        "release_clauses": (),
    }
    return Player(**(fields | overrides))


def snapshot(
    players: list[Player],
    *,
    game_date: date = SEASON_START,
    transfer_budget: int = 1_000_000,
    club_reputation: int = 5_000,
) -> Snapshot:
    return Snapshot(
        game_date=game_date,
        club_uid=MY_CLUB,
        club_name=MY_CLUB_NAME,
        club_reputation=club_reputation,
        club_nation_id=MY_NATION,
        budget=Budget(transfer_budget, 60_000, 55_000),
        players=tuple(players),
    )


def mine(name: str, **fields: Any) -> Player:
    return player(name, club=MY_CLUB, **fields)


def eleven(**fields: Any) -> list[Player]:
    shape = [("gk",), ("dc",), ("dc",), ("dl",), ("dr",), ("dm",), ("mc",), ("mc",), ("aml",), ("amr",), ("stc",)]
    return [mine(f"Starter {index}", positions=positions, **fields) for index, positions in enumerate(shape)]
