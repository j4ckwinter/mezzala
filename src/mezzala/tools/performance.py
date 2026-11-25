from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from statistics import median

from mezzala.core.players import Player, SeasonStats, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import within_reach
from mezzala.core.squad import belongs_to_club, is_outside_club, plays_for_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View, shows_hidden_information

MINUTES_PER_MATCH = 90
RATING_PEER_ABILITY_BAND = 10
MIN_RATING_PEERS = 10
DECIMALS = 2


class PerformanceScope(StrEnum):
    OWN = "own"
    ELSEWHERE = "elsewhere"
    EVERYONE = "everyone"


class PerformanceSort(StrEnum):
    ABOVE_HIS_LEVEL = "rating above similar players"
    AVERAGE_RATING = "average rating"
    GOALS_ABOVE_XG = "goals above xg"
    GOALS_BELOW_XG = "goals below xg"
    GOALS_PER_90 = "goals per 90"
    ASSISTS_PER_90 = "assists per 90"
    KEY_PASSES_PER_90 = "key passes per 90"
    DEFENSIVE_ACTIONS_PER_90 = "tackles and interceptions per 90"


@dataclass(frozen=True)
class Performer:
    player: PlayerSummary
    minutes: int
    average_rating: float | None
    rating_above_similar_players: float | None
    goals: int
    expected_goals: float
    goals_above_xg: float
    assists: int
    expected_assists: float
    goals_per_90: float
    assists_per_90: float
    key_passes_per_90: float
    tackles_and_interceptions_per_90: float


@dataclass(frozen=True)
class Performance:
    explanation: str
    sorted_by: str
    matched: int
    players: list[Performer]


EXPLANATION = (
    "Season stats as the save holds them, all competitions added up. A league's stats reset when its new season "
    "starts, so leagues between seasons have none. 'Rating above similar players' is his average rating minus the "
    "median of the similar players who also reached the minimum minutes: "
)
SIMILAR_BY_ABILITY = f"those within {RATING_PEER_ABILITY_BAND} ability of him."
SIMILAR_BY_LEAGUE = "those in his league, since fog of war hides ability."


def explanation(view: View) -> str:
    return EXPLANATION + (SIMILAR_BY_ABILITY if shows_hidden_information(view) else SIMILAR_BY_LEAGUE)


def per_90(count: float, minutes: int) -> float:
    return round(count * MINUTES_PER_MATCH / minutes, DECIMALS) if minutes else 0.0


def similar(view: View, player: Player, other: Player) -> bool:
    if shows_hidden_information(view):
        return abs(other.current_ability - player.current_ability) <= RATING_PEER_ABILITY_BAND
    return player.league_id is not None and other.league_id == player.league_id


class RatingPeers:
    def __init__(self, players: list[tuple[Player, SeasonStats]], view: View) -> None:
        self._view = view
        self._rated = [(player, season.average_rating) for player, season in players
                       if season.average_rating is not None]  # fmt: skip

    def above(self, player: Player, season: SeasonStats) -> float | None:
        if season.average_rating is None:
            return None
        peers = [rating for other, rating in self._rated if similar(self._view, player, other)]
        if len(peers) < MIN_RATING_PEERS:
            return None
        return round(season.average_rating - median(peers), DECIMALS)


def in_scope(player: Player, snapshot: Snapshot, scope: PerformanceScope) -> bool:
    match scope:
        case PerformanceScope.OWN:
            return plays_for_club(player, snapshot.club_uid) or belongs_to_club(player, snapshot.club_uid)
        case PerformanceScope.ELSEWHERE:
            return is_outside_club(player, snapshot.club_uid)
        case PerformanceScope.EVERYONE:
            return True


def performer(player: Player, season: SeasonStats, peers: RatingPeers, view: View) -> Performer:
    minutes = season.minutes
    return Performer(
        player=summarize(player, view),
        minutes=minutes,
        average_rating=season.average_rating,
        rating_above_similar_players=peers.above(player, season),
        goals=season.goals,
        expected_goals=season.expected_goals,
        goals_above_xg=round(season.goals - season.expected_goals, DECIMALS),
        assists=season.assists,
        expected_assists=season.expected_assists,
        goals_per_90=per_90(season.goals, minutes),
        assists_per_90=per_90(season.assists, minutes),
        key_passes_per_90=per_90(season.key_passes, minutes),
        tackles_and_interceptions_per_90=per_90(season.tackles_completed + season.interceptions, minutes),
    )


def sort_value(sort_by: PerformanceSort) -> Callable[[Performer], float | None]:
    match sort_by:
        case PerformanceSort.ABOVE_HIS_LEVEL:
            return lambda entry: entry.rating_above_similar_players
        case PerformanceSort.AVERAGE_RATING:
            return lambda entry: entry.average_rating
        case PerformanceSort.GOALS_ABOVE_XG:
            return lambda entry: entry.goals_above_xg
        case PerformanceSort.GOALS_BELOW_XG:
            return lambda entry: -entry.goals_above_xg
        case PerformanceSort.GOALS_PER_90:
            return lambda entry: entry.goals_per_90
        case PerformanceSort.ASSISTS_PER_90:
            return lambda entry: entry.assists_per_90
        case PerformanceSort.KEY_PASSES_PER_90:
            return lambda entry: entry.key_passes_per_90
        case PerformanceSort.DEFENSIVE_ACTIONS_PER_90:
            return lambda entry: entry.tackles_and_interceptions_per_90


@dataclass(frozen=True)
class PerformanceSearch:
    scope: PerformanceScope
    sort_by: PerformanceSort
    min_minutes: int
    position: PositionGroup | None
    reachable_only: bool
    limit: int


def wanted(player: Player, snapshot: Snapshot, search: PerformanceSearch) -> bool:
    return (
        in_scope(player, snapshot, search.scope)
        and (search.position is None or covers(player, search.position))
        and (not search.reachable_only or search.scope is PerformanceScope.OWN or within_reach(player, snapshot))
    )


def performance(snapshot: Snapshot, search: PerformanceSearch, view: View) -> Performance:
    played = [(player, player.season) for player in snapshot.players
              if player.season is not None and player.season.minutes >= search.min_minutes]  # fmt: skip
    peers = RatingPeers(played, view)
    entries = [performer(player, season, peers, view) for player, season in played if wanted(player, snapshot, search)]
    value = sort_value(search.sort_by)
    scored = [(found, entry) for entry in entries if (found := value(entry)) is not None]
    ranked = [entry for _, entry in sorted(scored, key=lambda item: item[0], reverse=True)]
    return Performance(explanation(view), search.sort_by.value, len(ranked), ranked[: search.limit])
