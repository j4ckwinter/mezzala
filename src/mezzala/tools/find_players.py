from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from mezzala.core.metrics import (
    PeerMedians,
    above_league,
    league_levels,
    market_value,
    release_clause_for,
    transfer_value,
    weekly_wage,
)
from mezzala.core.money import format_money
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers, primary_group
from mezzala.core.profile import position_score
from mezzala.core.reach import within_reach
from mezzala.core.squad import (
    belongs_to_club,
    contract_ends_within,
    is_outside_club,
    leaves_within,
    plays_for_club,
    wage_paid_by_club,
)
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import Measure, View, measure_change


class SearchScope(StrEnum):
    ELSEWHERE = "elsewhere"
    OWN = "own"
    EVERYONE = "everyone"


class SortBy(StrEnum):
    CURRENT_ABILITY = "current ability"
    POTENTIAL_ABILITY = "potential ability"
    HEADROOM = "headroom"
    VALUE_FOR_MONEY = "value for money"
    ABOVE_LEAGUE = "above league level"
    POSITION_ATTRIBUTES = "position attributes"
    CHEAPEST = "cheapest"
    LOWEST_RELEASE_CLAUSE = "lowest release clause"
    YOUNGEST = "youngest"
    MOST_OVERPAID = "most overpaid"


@dataclass(frozen=True)
class PlayerSearch:
    scope: SearchScope
    position: PositionGroup | None
    min_age: int | None
    max_age: int | None
    min_ca: int | None
    max_ca: int | None
    min_pa: int | None
    max_fee: int | None
    max_wage: int | None
    free_agents_only: bool
    contract_ending_within_months: int | None
    max_release_clause: int | None
    youth_contract_only: bool
    reserves_only: bool
    bigger_clubs_only: bool
    within_reach: bool
    sort_by: SortBy
    limit: int


@dataclass(frozen=True)
class FoundPlayer:
    player: PlayerSummary
    team: str
    value_vs_similar_players: str
    wage_vs_similar_players: str
    above_league_level: Measure | None
    position: str
    position_attribute_score: float
    release_clause: str


@dataclass(frozen=True)
class FoundPlayers:
    matched: int
    sorted_by: str
    players: list[FoundPlayer]


@dataclass(frozen=True)
class Measures:
    snapshot: Snapshot
    values: PeerMedians
    wages: PeerMedians
    leagues: dict[int, float]

    def value_ratio(self, player: Player) -> float | None:
        return self.values.ratio_of(market_value(player), player)

    def wage_ratio(self, player: Player) -> float | None:
        return self.wages.ratio_of(wage_for(player, self.snapshot), player)

    def release_clause(self, player: Player) -> int | None:
        return release_clause_for(player, self.snapshot.club_nation_id, self.snapshot.game_date)


def in_scope(player: Player, snapshot: Snapshot, scope: SearchScope) -> bool:
    match scope:
        case SearchScope.ELSEWHERE:
            return is_outside_club(player, snapshot.club_uid)
        case SearchScope.OWN:
            return plays_for_club(player, snapshot.club_uid) or belongs_to_club(player, snapshot.club_uid)
        case SearchScope.EVERYONE:
            return True


def at_most(amount: int | None, limit: int | None) -> bool:
    return limit is None or (amount is not None and amount <= limit)


def at_least(amount: int | None, limit: int | None) -> bool:
    return limit is None or (amount is not None and amount >= limit)


def matches_profile(player: Player, search: PlayerSearch) -> bool:
    return (
        (search.position is None or covers(player, search.position))
        and at_least(player.age, search.min_age)
        and at_most(player.age, search.max_age)
        and at_least(player.current_ability, search.min_ca)
        and at_most(player.current_ability, search.max_ca)
        and at_least(player.potential_ability, search.min_pa)
    )


def ending(player: Player, snapshot: Snapshot, months: int) -> date | None:
    if is_outside_club(player, snapshot.club_uid):
        return contract_ends_within(player, snapshot.game_date, months)
    return leaves_within(player, snapshot.club_uid, snapshot.game_date, months)


def wage_for(player: Player, snapshot: Snapshot) -> int | None:
    if is_outside_club(player, snapshot.club_uid):
        return player.wage
    return wage_paid_by_club(player, snapshot.club_uid)


def matches_market(player: Player, search: PlayerSearch, measures: Measures) -> bool:
    snapshot = measures.snapshot
    if search.free_agents_only and not player.is_free_agent:
        return False
    if search.max_fee is not None and not player.costs_no_fee and not at_most(player.value, search.max_fee):
        return False
    if not player.is_free_agent and not at_most(wage_for(player, snapshot), search.max_wage):
        return False
    if search.contract_ending_within_months is not None and (
        player.is_free_agent or ending(player, snapshot, search.contract_ending_within_months) is None
    ):
        return False
    if search.max_release_clause is not None and not at_most(
        measures.release_clause(player), search.max_release_clause
    ):
        return False
    if search.youth_contract_only and player.youth_contract is not True:
        return False
    if search.reserves_only and player.first_team is not False:
        return False
    if search.bigger_clubs_only and not at_least(player.club_reputation, snapshot.club_reputation + 1):
        return False
    return not (search.within_reach and search.scope is not SearchScope.OWN and not within_reach(player, snapshot))


def group_for(player: Player, search: PlayerSearch) -> PositionGroup:
    return search.position or primary_group(player)


def sort_key(sort_by: SortBy, search: PlayerSearch, measures: Measures) -> Callable[[Player], tuple[bool, float]]:
    def missing_last(amount: float | None, highest_first: bool) -> tuple[bool, float]:
        if amount is None:
            return (True, 0.0)
        return (False, -amount if highest_first else amount)

    def key(player: Player) -> tuple[bool, float]:
        match sort_by:
            case SortBy.CURRENT_ABILITY:
                return missing_last(player.current_ability, True)
            case SortBy.POTENTIAL_ABILITY:
                return missing_last(player.potential_ability, True)
            case SortBy.HEADROOM:
                return missing_last(player.headroom, True)
            case SortBy.VALUE_FOR_MONEY:
                return missing_last(measures.value_ratio(player), False)
            case SortBy.ABOVE_LEAGUE:
                return missing_last(above_league(player, measures.leagues), True)
            case SortBy.POSITION_ATTRIBUTES:
                return missing_last(position_score(player, group_for(player, search)), True)
            case SortBy.CHEAPEST:
                return missing_last(0 if player.costs_no_fee else player.value, False)
            case SortBy.LOWEST_RELEASE_CLAUSE:
                return missing_last(measures.release_clause(player), False)
            case SortBy.YOUNGEST:
                return missing_last(player.age, False)
            case SortBy.MOST_OVERPAID:
                return missing_last(measures.wage_ratio(player), True)

    return key


def describe_ratio(ratio: float | None) -> str:
    return "unknown" if ratio is None else f"{ratio:.2f}x"


def team_label(player: Player) -> str:
    if player.first_team is None:
        return "unknown"
    return "first team" if player.first_team else "reserves or youth"


def found(player: Player, search: PlayerSearch, measures: Measures, view: View) -> FoundPlayer:
    group = group_for(player, search)
    excess = above_league(player, measures.leagues)
    clause = measures.release_clause(player)
    return FoundPlayer(
        player=summarize(player, view),
        team=team_label(player),
        value_vs_similar_players=describe_ratio(measures.value_ratio(player)),
        wage_vs_similar_players=describe_ratio(measures.wage_ratio(player)),
        above_league_level=None if excess is None else measure_change(view, round(excess, 1)),
        position=group.value,
        position_attribute_score=position_score(player, group),
        release_clause="none" if clause is None else format_money(clause),
    )


def find_players(snapshot: Snapshot, search: PlayerSearch, view: View) -> FoundPlayers:
    measures = Measures(
        snapshot,
        PeerMedians(snapshot.players, transfer_value),
        PeerMedians(snapshot.players, weekly_wage),
        league_levels(snapshot.players),
    )
    matched = [
        player
        for player in snapshot.players
        if in_scope(player, snapshot, search.scope)
        and matches_profile(player, search)
        and matches_market(player, search, measures)
    ]
    matched.sort(key=sort_key(search.sort_by, search, measures))
    return FoundPlayers(
        len(matched), search.sort_by.value, [found(p, search, measures, view) for p in matched[: search.limit]]
    )
