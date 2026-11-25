from dataclasses import dataclass
from statistics import median

from mezzala.core.formations import Formation
from mezzala.core.lineup import pick_lineup
from mezzala.core.players import Player, Snapshot
from mezzala.core.profile import outfield_profile
from mezzala.core.squad import available_squad, club_league

NOTABLE_DIFFERENCE = 0.5


@dataclass(frozen=True)
class AttributeGroup:
    group: str
    yours: float
    league_median: float | None
    difference: float | None


@dataclass(frozen=True)
class SquadProfile:
    formation: str
    explanation: str
    groups: list[AttributeGroup]
    strengths: list[str]
    weaknesses: list[str]


EXPLANATION = (
    "Average attributes (1-20) of the best eleven's outfield players by group, against the median of the other "
    "clubs' best elevens in your league, each picked in your formation. Use the strengths and weaknesses to shape "
    "tactics; mezzala cannot read your tactic itself."
)


def league_rivals(snapshot: Snapshot) -> dict[int, list[Player]]:
    league = club_league(snapshot)
    rivals: dict[int, list[Player]] = {}
    if league is None:
        return rivals
    for player in snapshot.players:
        if player.league_id == league and player.club_uid is not None and player.club_uid != snapshot.club_uid:
            rivals.setdefault(player.club_uid, []).append(player)
    return rivals


def compare_profiles(mine: dict[str, float], others: list[dict[str, float]]) -> list[AttributeGroup]:
    groups: list[AttributeGroup] = []
    for group, yours in mine.items():
        values = [profile[group] for profile in others if group in profile]
        league = round(median(values), 1) if values else None
        groups.append(AttributeGroup(group, yours, league, None if league is None else round(yours - league, 1)))
    return groups


def squad_profile(snapshot: Snapshot, formation: Formation) -> SquadProfile:
    mine = outfield_profile(pick_lineup(available_squad(snapshot), formation).starters)
    others = [outfield_profile(pick_lineup(squad, formation).starters) for squad in league_rivals(snapshot).values()]
    groups = compare_profiles(mine, others)
    ranked = sorted((g for g in groups if g.difference is not None), key=lambda g: g.difference or 0.0, reverse=True)
    strengths = [g.group for g in ranked if (g.difference or 0.0) >= NOTABLE_DIFFERENCE]
    weaknesses = [g.group for g in reversed(ranked) if (g.difference or 0.0) <= -NOTABLE_DIFFERENCE]
    return SquadProfile(formation.value, EXPLANATION, groups, strengths, weaknesses)
