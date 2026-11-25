from dataclasses import dataclass
from statistics import median

from mezzala.core.formations import STARTERS, Formation
from mezzala.core.leagues import club_league
from mezzala.core.lineup import Lineup, pick_lineup
from mezzala.core.money import format_money
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup
from mezzala.core.squad import available_squad


@dataclass(frozen=True)
class ClubRow:
    rank: int
    club: str
    eleven_average_ability: float
    squad_value: str
    yours: bool


@dataclass(frozen=True)
class PositionRow:
    position: str
    yours: float | None
    league_median: float | None
    best_club: str | None
    best: float | None


@dataclass(frozen=True)
class LeagueComparison:
    formation: str
    explanation: str
    your_rank: int | None
    clubs: list[ClubRow]
    positions: list[PositionRow]


NO_LEAGUE = "Your club's league could not be identified from this save's fixtures, so there is nothing to compare."
EXPLANATION = (
    "Each club's best eleven for the formation, ranked by its average CA (an empty place counts as 0, and "
    "equal averages share a rank), with the first team's total transfer value. Positions compare the "
    "average CA of each club's starters there."
)


def squads_in(snapshot: Snapshot, league_id: int) -> dict[int, list[Player]]:
    squads: dict[int, list[Player]] = {}
    for player in snapshot.players:
        if player.league_id == league_id and player.club_uid is not None:
            squads.setdefault(player.club_uid, []).append(player)
    return squads


def squad_value(squad: list[Player]) -> int:
    return sum(player.value or 0 for player in squad if player.first_team)


def average_at(lineup: Lineup, group: PositionGroup) -> float | None:
    starters = lineup.at(group)
    return round(sum(p.current_ability for p in starters) / len(starters), 1) if starters else None


def position_rows(
    lineups: dict[int, Lineup], names: dict[int, str], mine: int, formation: Formation
) -> list[PositionRow]:
    rows: list[PositionRow] = []
    for group in STARTERS[formation]:
        levels = {club: level for club, lineup in lineups.items() if (level := average_at(lineup, group)) is not None}
        best_club = max(levels, key=lambda club: levels[club], default=None)
        rows.append(
            PositionRow(
                group.value,
                levels.get(mine),
                round(median(levels.values()), 1) if levels else None,
                names[best_club] if best_club is not None else None,
                levels[best_club] if best_club is not None else None,
            )
        )
    return rows


def league_comparison(snapshot: Snapshot, formation: Formation) -> LeagueComparison:
    league_id = club_league(snapshot)
    if league_id is None:
        return LeagueComparison(formation.value, NO_LEAGUE, None, [], [])
    squads = squads_in(snapshot, league_id)
    squads[snapshot.club_uid] = available_squad(snapshot)
    names = {club: next((p.club_name for p in squad if p.club_name), "unknown") for club, squad in squads.items()}
    names[snapshot.club_uid] = snapshot.club_name
    lineups = {club: pick_lineup(squad, formation) for club, squad in squads.items()}
    ordered = sorted(lineups, key=lambda club: lineups[club].average_ability(), reverse=True)
    averages = [lineups[club].average_ability() for club in ordered]
    clubs = [
        ClubRow(averages.index(average) + 1, names[club], average, format_money(squad_value(squads[club])),
                club == snapshot.club_uid)
        for club, average in zip(ordered, averages, strict=True)
    ]  # fmt: skip
    your_rank = next(row.rank for row in clubs if row.yours)
    return LeagueComparison(
        formation.value, EXPLANATION, your_rank, clubs, position_rows(lineups, names, snapshot.club_uid, formation)
    )
