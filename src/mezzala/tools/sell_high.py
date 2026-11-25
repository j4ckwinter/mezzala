from dataclasses import dataclass

from mezzala.core.metrics import PeerMedians, transfer_value
from mezzala.core.money import format_money
from mezzala.core.players import PastPlayers, Player, Snapshot, is_same_person
from mezzala.core.positions import is_goalkeeper
from mezzala.core.squad import leaves_within, owned_players
from mezzala.core.view import Rating, View, ability_text, potential_text, rating, signed_amount_text

PEAK_OUTFIELD_AGE = 29
PEAK_GOALKEEPER_AGE = 32
AT_CEILING_HEADROOM = 3
PEER_MIN_AGE = 24
OVERVALUED_RATIO = 1.3
CONTRACT_RUNNING_DOWN_MONTHS = 12
STALLED_ABILITY_GAIN = 1
STALL_MIN_DAYS = 180
VALUE_RISE_RATIO = 1.1
VALUE_FALL_RATIO = 0.9


@dataclass(frozen=True)
class SaleCandidate:
    name: str
    age: int
    current_ability: Rating
    potential_ability: Rating
    value: str
    signals: list[str]


@dataclass(frozen=True)
class SellHigh:
    compared_with: str | None
    candidates: list[SaleCandidate]


def present_signals(player: Player, snapshot: Snapshot, peer_median: float | None, view: View) -> list[str]:
    signals: list[str] = []
    peak_age = PEAK_GOALKEEPER_AGE if is_goalkeeper(player) else PEAK_OUTFIELD_AGE
    if player.age >= peak_age:
        signals.append(f"past peak age at {player.age}, value tends to fall from here")
    if player.headroom <= AT_CEILING_HEADROOM:
        ceiling = f"{ability_text(view, player.current_ability)} of {potential_text(view, player.potential_ability)}"
        signals.append(f"at his ceiling: {ceiling}")
    if (
        player.age >= PEER_MIN_AGE
        and peer_median is not None
        and player.value is not None
        and player.value >= OVERVALUED_RATIO * peer_median
    ):
        signals.append(
            f"valued at {player.value / peer_median:.1f}x similar players ({format_money(round(peer_median))})"
        )
    leaving = leaves_within(player, snapshot.club_uid, snapshot.game_date, CONTRACT_RUNNING_DOWN_MONTHS)
    if leaving is not None:
        signals.append(f"contract ends {leaving.isoformat()}, sell now or lose him for free")
    return signals


def history_signals(
    player: Player, history: list[tuple[PastPlayers, Player]], current: Snapshot, view: View
) -> list[str]:
    signals: list[str] = []
    values = [earlier.value for _, earlier in history if earlier.value]
    if player.value and values and player.value <= VALUE_FALL_RATIO * max(values):
        signals.append(f"value already down from a high of {format_money(max(values))}")
    stalled = [
        (snapshot, earlier)
        for snapshot, earlier in history
        if (current.game_date - snapshot.game_date).days >= STALL_MIN_DAYS
    ]
    if stalled and player.value:
        snapshot, earlier = stalled[-1]
        gain = player.current_ability - earlier.current_ability
        if gain <= STALLED_ABILITY_GAIN and earlier.value and player.value >= VALUE_RISE_RATIO * earlier.value:
            signals.append(
                f"CA moved {signed_amount_text(view, gain, 0)} since {snapshot.game_date.isoformat()} while value rose "
                f"from {format_money(earlier.value)}"
            )
    return signals


def earlier_selves(player: Player, earlier: list[PastPlayers]) -> list[tuple[PastPlayers, Player]]:
    found: list[tuple[PastPlayers, Player]] = []
    for past in earlier:
        before = past.by_uid.get(player.uid)
        if before is not None and is_same_person(before, player):
            found.append((past, before))
    return found


def sell_high(current: Snapshot, earlier: list[PastPlayers], limit: int, view: View) -> SellHigh:
    values = PeerMedians(current.players, transfer_value)
    candidates: list[SaleCandidate] = []
    for player in owned_players(current):
        if not player.value:
            continue
        signals = present_signals(player, current, values.of(player), view)
        signals += history_signals(player, earlier_selves(player, earlier), current, view)
        if signals:
            candidates.append(
                SaleCandidate(player.name, player.age, rating(view, player.current_ability),
                              rating(view, player.potential_ability), format_money(player.value), signals)
            )  # fmt: skip
    candidates.sort(key=lambda candidate: len(candidate.signals), reverse=True)
    compared_with = earlier[0].game_date.isoformat() if earlier else None
    return SellHigh(compared_with, candidates[:limit])
