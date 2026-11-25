from dataclasses import dataclass
from statistics import median

from mezzala.core.leagues import league_names
from mezzala.core.metrics import PeerMedians, league_levels, market_value, transfer_value
from mezzala.core.money import format_money
from mezzala.core.players import Snapshot

MIN_PRICED_PLAYERS = 30


@dataclass(frozen=True)
class LeagueValue:
    league: str
    level: float
    value_vs_similar_players: str
    median_value: str
    priced_players: int
    yours: bool


@dataclass(frozen=True)
class LeagueValues:
    explanation: str
    leagues: list[LeagueValue]


EXPLANATION = (
    "Leagues whose first-team players cost least against similar players (same CA, age and potential) in the "
    "whole save, cheapest first. A league is named after its three biggest clubs; level is its first-team median "
    "CA. Only leagues loaded in the save with enough priced players appear."
)


def league_values(snapshot: Snapshot, limit: int) -> LeagueValues:
    levels = league_levels(snapshot.players)
    names = league_names(snapshot.players)
    peers = PeerMedians(snapshot.players, transfer_value)
    ratios: dict[int, list[float]] = {}
    values: dict[int, list[int]] = {}
    for player in snapshot.players:
        price = market_value(player)
        if player.league_id not in levels or not player.first_team or price is None:
            continue
        ratio = peers.ratio_of(price, player)
        if ratio is not None:
            ratios.setdefault(player.league_id, []).append(ratio)
            values.setdefault(player.league_id, []).append(price)
    yours = {player.league_id for player in snapshot.players if player.club_uid == snapshot.club_uid}
    ranked = sorted(
        ((median(found), league) for league, found in ratios.items() if len(found) >= MIN_PRICED_PLAYERS),
        key=lambda item: item[0],
    )
    rows = [
        LeagueValue(names.get(league, "unknown"), levels[league], f"{ratio:.2f}x",
                    format_money(round(median(values[league]))), len(ratios[league]), league in yours)
        for ratio, league in ranked[:limit]
    ]  # fmt: skip
    return LeagueValues(EXPLANATION, rows)
