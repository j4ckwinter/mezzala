from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.growth import Growth, GrowthBasis, observed_growth, projected_growth
from mezzala.core.money import format_money
from mezzala.core.players import Player, Snapshot, is_same_person
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import within_reach
from mezzala.core.squad import belongs_to_club, is_outside_club
from mezzala.core.summary import PlayerSummary, summarize


class RiserScope(StrEnum):
    ELSEWHERE = "elsewhere"
    OWN = "own"
    FORMER = "former"


@dataclass(frozen=True)
class RiserFilters:
    scope: RiserScope
    min_ability_gain: float
    min_current_ability: float
    within_reach: bool
    max_age: int | None
    max_fee: int | None
    group: PositionGroup | None


@dataclass(frozen=True)
class Riser:
    player: PlayerSummary
    ability_gain: float
    value_change: str
    reason: str


@dataclass(frozen=True)
class Risers:
    basis: str
    compared_with: str | None
    explanation: str
    risers: list[Riser]


PROJECTED_EXPLANATION = (
    "Only one snapshot so far, so gains are projected for the next season from age, the gap between "
    "potential and current ability, professionalism, determination and ambition. "
    "Observed gains start once the save has a second snapshot."
)
OBSERVED_EXPLANATION = "Gains are measured between the two snapshots."


def in_scope(player: Player, earlier: Player | None, club_uid: int, scope: RiserScope) -> bool:
    match scope:
        case RiserScope.ELSEWHERE:
            return is_outside_club(player, club_uid)
        case RiserScope.OWN:
            return belongs_to_club(player, club_uid)
        case RiserScope.FORMER:
            return earlier is not None and belongs_to_club(earlier, club_uid) and is_outside_club(player, club_uid)


def passes(player: Player, snapshot: Snapshot, filters: RiserFilters) -> bool:
    if player.current_ability < filters.min_current_ability:
        return False
    if filters.within_reach and filters.scope is RiserScope.ELSEWHERE and not within_reach(player, snapshot):
        return False
    if filters.max_age is not None and player.age > filters.max_age:
        return False
    if filters.group is not None and not covers(player, filters.group):
        return False
    if filters.scope is RiserScope.ELSEWHERE and filters.max_fee is not None and not player.costs_no_fee:
        return player.value is not None and player.value <= filters.max_fee
    return True


def describe_change(growth: Growth) -> str:
    if growth.value_change is None:
        return "unknown"
    sign = "+" if growth.value_change >= 0 else "-"
    return f"{sign}{format_money(abs(growth.value_change))}"


def reason(player: Player, growth: Growth) -> str:
    if growth.basis is GrowthBasis.OBSERVED:
        return (
            f"gained {growth.ability_gain:.0f} CA in {growth.days} days, "
            f"now {player.current_ability} of {player.potential_ability}"
        )
    return f"{player.headroom} CA of headroom at {player.age}, projected +{growth.ability_gain:.1f} next season"


def find_risers(current: Snapshot, earlier: Snapshot | None, filters: RiserFilters, limit: int) -> Risers:
    earlier_by_uid = earlier.by_uid() if earlier is not None else {}
    found: list[tuple[Growth, Player]] = []
    for player in current.players:
        before = earlier_by_uid.get(player.uid)
        if before is not None and not is_same_person(before, player):
            before = None
        if not in_scope(player, before, current.club_uid, filters.scope) or not passes(player, current, filters):
            continue
        if earlier is None:
            growth = projected_growth(player)
        elif before is None:
            continue
        else:
            growth = observed_growth(before, player, earlier.game_date, current.game_date)
        if growth.ability_gain >= filters.min_ability_gain:
            found.append((growth, player))
    found.sort(key=lambda pair: (pair[0].ability_gain, -(pair[1].value or 0)), reverse=True)
    return Risers(
        basis=(GrowthBasis.PROJECTED if earlier is None else GrowthBasis.OBSERVED).value,
        compared_with=earlier.game_date.isoformat() if earlier is not None else None,
        explanation=PROJECTED_EXPLANATION if earlier is None else OBSERVED_EXPLANATION,
        risers=[Riser(summarize(p), g.ability_gain, describe_change(g), reason(p, g)) for g, p in found[:limit]],
    )
