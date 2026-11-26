from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from mezzala.core.leagues import League, leagues
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
from mezzala.core.nationality import holds_nationality, needs_no_work_permit
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import Fit, PositionGroup, covers, fit, primary_group
from mezzala.core.profile import position_score
from mezzala.core.reach import within_reach
from mezzala.core.roles import Role, Side, role_score
from mezzala.core.signing import can_sign_on_pre_contract
from mezzala.core.squad import (
    belongs_to_club,
    contract_ends_within,
    is_outside_club,
    leaves_within,
    not_counted_on,
    plays_for_club,
    wage_paid_by_club,
)
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import Measure, Rating, View, measure_change
from mezzala.core.wages import WageGuide, describe_wage, wage_guide


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
    ROLE_FIT = "role fit"


@dataclass(frozen=True)
class PlayerSearch:
    scope: SearchScope
    position: PositionGroup | None
    natural_only: bool
    min_age: int | None
    max_age: int | None
    min_ca: int | None
    max_ca: int | None
    min_pa: int | None
    max_fee: int | None
    max_wage: int | None
    free_agents_only: bool
    clubs_only: bool
    contract_ending_within_months: int | None
    pre_contract_only: bool
    max_release_clause: int | None
    youth_contract_only: bool
    nationality: str | None
    work_permit_free_only: bool
    country: str | None
    division_level: int | None
    league: str | None
    fringe_only: bool
    reserves_only: bool
    bigger_clubs_only: bool
    within_reach: bool
    sort_by: SortBy
    limit: int
    compact: bool
    role: Role | None
    side: Side | None


@dataclass(frozen=True)
class FoundPlayer:
    player: PlayerSummary
    team: str
    reputation: int
    club_reputation: int | None
    squad_status: str | None
    league: str | None
    country: str | None
    division_level: int | None
    value_vs_similar_players: str
    wage_vs_similar_players: str
    expected_wage: str
    above_league_level: Measure | None
    position: str
    position_attribute_score: float
    role_score: float | None
    release_clause: str
    needs_no_work_permit: bool


@dataclass(frozen=True)
class CompactPlayer:
    name: str
    age: int
    club: str
    nationality: str
    positions: str
    current_ability: Rating
    potential_ability: Rating
    value: str
    expected_wage: str


@dataclass(frozen=True)
class FoundPlayers:
    matched: int
    sorted_by: str
    players: list[FoundPlayer]
    compact_players: list[CompactPlayer]


@dataclass(frozen=True)
class Measures:
    snapshot: Snapshot
    values: PeerMedians
    wages: PeerMedians
    leagues: dict[int, float]
    named_leagues: dict[int, League]
    wage_guide: WageGuide

    def league_of(self, player: Player) -> League | None:
        return self.named_leagues.get(player.league_id) if player.league_id is not None else None

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


def plays_there(player: Player, group: PositionGroup, natural_only: bool) -> bool:
    return fit(player, group) is Fit.NATURAL if natural_only else covers(player, group)


def at_most(amount: int | None, limit: int | None) -> bool:
    return limit is None or (amount is not None and amount <= limit)


def at_least(amount: int | None, limit: int | None) -> bool:
    return limit is None or (amount is not None and amount >= limit)


def matches_profile(player: Player, search: PlayerSearch) -> bool:
    return (
        (search.position is None or plays_there(player, search.position, search.natural_only))
        and at_least(player.age, search.min_age)
        and at_most(player.age, search.max_age)
        and at_least(player.current_ability, search.min_ca)
        and at_most(player.current_ability, search.max_ca)
        and at_least(player.potential_ability, search.min_pa)
        and (search.nationality is None or holds_nationality(player, search.nationality))
        and (not search.work_permit_free_only or needs_no_work_permit(player))
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
    if search.clubs_only and player.is_free_agent:
        return False
    if search.max_fee is not None and not player.costs_no_fee and not at_most(player.value, search.max_fee):
        return False
    if not player.is_free_agent and not at_most(wage_for(player, snapshot), search.max_wage):
        return False
    if search.contract_ending_within_months is not None and (
        player.is_free_agent or ending(player, snapshot, search.contract_ending_within_months) is None
    ):
        return False
    if search.pre_contract_only and not can_sign_on_pre_contract(player, snapshot.game_date):
        return False
    if search.max_release_clause is not None and not at_most(
        measures.release_clause(player), search.max_release_clause
    ):
        return False
    if search.youth_contract_only and player.youth_contract is not True:
        return False
    if not in_league(player, search, measures):
        return False
    if search.fringe_only and not not_counted_on(player):
        return False
    if search.reserves_only and player.first_team is not False:
        return False
    if search.bigger_clubs_only and not at_least(player.club_reputation, snapshot.club_reputation + 1):
        return False
    return not (search.within_reach and search.scope is not SearchScope.OWN and not within_reach(player, snapshot))


def same_words(text: str | None, wanted: str) -> bool:
    return text is not None and text.casefold() == wanted.strip().casefold()


def in_league(player: Player, search: PlayerSearch, measures: Measures) -> bool:
    league = measures.league_of(player)
    if search.country is not None and not same_words(player.club_country, search.country):
        return False
    if search.division_level is not None and (league is None or league.division_level != search.division_level):
        return False
    return search.league is None or (league is not None and search.league.casefold() in league.name.casefold())


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
            case SortBy.ROLE_FIT:
                return missing_last(role_fit(player, search), True)

    return key


def role_fit(player: Player, search: PlayerSearch) -> float | None:
    return None if search.role is None else role_score(player, search.role, search.side)


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
        reputation=player.reputation,
        club_reputation=player.club_reputation,
        squad_status=player.squad_status,
        league=league.name if (league := measures.league_of(player)) else None,
        country=player.club_country,
        division_level=league.division_level if league else None,
        value_vs_similar_players=describe_ratio(measures.value_ratio(player)),
        wage_vs_similar_players=describe_ratio(measures.wage_ratio(player)),
        expected_wage=describe_wage(measures.wage_guide.expected(player)),
        above_league_level=None if excess is None else measure_change(view, round(excess, 1)),
        position=group.value,
        position_attribute_score=position_score(player, group),
        role_score=role_fit(player, search),
        release_clause="none" if clause is None else format_money(clause),
        needs_no_work_permit=needs_no_work_permit(player),
    )


def compact(player: Player, measures: Measures, view: View) -> CompactPlayer:
    summary = summarize(player, view)
    return CompactPlayer(
        summary.name, summary.age, summary.club, summary.nationality, summary.positions, summary.current_ability,
        summary.potential_ability, summary.value, describe_wage(measures.wage_guide.expected(player)),
    )  # fmt: skip


def find_players(snapshot: Snapshot, search: PlayerSearch, view: View) -> FoundPlayers:
    measures = Measures(
        snapshot,
        PeerMedians(snapshot.players, transfer_value),
        PeerMedians(snapshot.players, weekly_wage),
        league_levels(snapshot.players),
        leagues(snapshot.players),
        wage_guide(snapshot),
    )
    matched = [
        player
        for player in snapshot.players
        if in_scope(player, snapshot, search.scope)
        and matches_profile(player, search)
        and matches_market(player, search, measures)
    ]
    matched.sort(key=sort_key(search.sort_by, search, measures))
    shown = matched[: search.limit]
    if search.compact:
        return FoundPlayers(len(matched), search.sort_by.value, [], [compact(p, measures, view) for p in shown])
    return FoundPlayers(len(matched), search.sort_by.value, [found(p, search, measures, view) for p in shown], [])
