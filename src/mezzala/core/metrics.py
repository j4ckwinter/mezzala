from collections.abc import Callable, Iterable
from statistics import median

from mezzala.core.players import Player, ReleaseScope

PEER_ABILITY_BAND = 3
PEER_AGE_BAND = 2
MIN_PEERS = 20
MIN_LEAGUE_PLAYERS = 50


class PeerMedians:
    def __init__(self, players: Iterable[Player], measure: Callable[[Player], int | None]) -> None:
        self._measure = measure
        self._by_ability_and_age: dict[tuple[int, int], list[int]] = {}
        for player in players:
            amount = measure(player)
            if amount:
                self._by_ability_and_age.setdefault((player.current_ability, player.age), []).append(amount)
        self._medians: dict[tuple[int, int], float | None] = {}

    def _median_at(self, ability: int, age: int) -> float | None:
        peers = [
            amount
            for peer_ability in range(ability - PEER_ABILITY_BAND, ability + PEER_ABILITY_BAND + 1)
            for peer_age in range(age - PEER_AGE_BAND, age + PEER_AGE_BAND + 1)
            for amount in self._by_ability_and_age.get((peer_ability, peer_age), [])
        ]
        return median(peers) if len(peers) >= MIN_PEERS else None

    def of(self, player: Player) -> float | None:
        key = (player.current_ability, player.age)
        if key not in self._medians:
            self._medians[key] = self._median_at(*key)
        return self._medians[key]

    def ratio(self, player: Player) -> float | None:
        return self.ratio_of(self._measure(player), player)

    def ratio_of(self, amount: int | None, player: Player) -> float | None:
        peer = self.of(player)
        if not amount or peer is None:
            return None
        return amount / peer


def transfer_value(player: Player) -> int | None:
    return player.value


def weekly_wage(player: Player) -> int | None:
    return player.wage


def league_levels(players: Iterable[Player]) -> dict[int, float]:
    abilities: dict[int, list[int]] = {}
    for player in players:
        if player.league_id is not None and player.first_team:
            abilities.setdefault(player.league_id, []).append(player.current_ability)
    return {league: median(found) for league, found in abilities.items() if len(found) >= MIN_LEAGUE_PLAYERS}


def above_league(player: Player, levels: dict[int, float]) -> float | None:
    if player.league_id is None or player.league_id not in levels:
        return None
    return player.current_ability - levels[player.league_id]


def clause_applies(scope: ReleaseScope, player: Player, buyer_nation_id: int | None) -> bool:
    match scope:
        case ReleaseScope.ANY:
            return True
        case ReleaseScope.DOMESTIC:
            return buyer_nation_id is not None and buyer_nation_id == player.club_nation_id
        case ReleaseScope.FOREIGN:
            return (
                buyer_nation_id is not None
                and player.club_nation_id is not None
                and (buyer_nation_id != player.club_nation_id)
            )


def release_clause_for(player: Player, buyer_nation_id: int | None) -> int | None:
    fees = [c.fee for c in player.release_clauses if clause_applies(c.scope, player, buyer_nation_id)]
    return min(fees) if fees else None
