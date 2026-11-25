from collections.abc import Callable, Iterable
from statistics import median

from mezzala.core.players import Player

PEER_ABILITY_BAND = 3
PEER_AGE_BAND = 2
MIN_PEERS = 20


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


def transfer_value(player: Player) -> int | None:
    return player.value
