from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from mezzala.players import Player

HEADROOM_SHARE_PER_SEASON_BY_AGE: tuple[tuple[int, float], ...] = (
    (17, 0.30),
    (19, 0.25),
    (21, 0.18),
    (23, 0.10),
    (26, 0.04),
)
LOWEST_ATTITUDE_FACTOR = 0.6
HIGHEST_ATTITUDE_FACTOR = 1.4
REGULAR_MINUTES = 1500
REGULAR_MINUTES_FACTOR = 1.15
DAYS_PER_SEASON = 365


class GrowthBasis(StrEnum):
    OBSERVED = "observed"
    PROJECTED = "projected"


@dataclass(frozen=True)
class Growth:
    basis: GrowthBasis
    ability_gain: float
    value_change: int | None
    days: int


def headroom_share(age: int) -> float:
    for oldest, share in HEADROOM_SHARE_PER_SEASON_BY_AGE:
        if age <= oldest:
            return share
    return 0.0


def attitude_factor(player: Player) -> float:
    attitude = (player.professionalism + player.attributes["determination"] + player.ambition) / 3
    spread = HIGHEST_ATTITUDE_FACTOR - LOWEST_ATTITUDE_FACTOR
    return LOWEST_ATTITUDE_FACTOR + spread * (attitude - 1) / 19


def minutes_factor(player: Player) -> float:
    return REGULAR_MINUTES_FACTOR if player.last_season_minutes >= REGULAR_MINUTES else 1.0


def projected_growth(player: Player) -> Growth:
    gain = player.headroom * headroom_share(player.age) * attitude_factor(player) * minutes_factor(player)
    return Growth(GrowthBasis.PROJECTED, round(min(gain, player.headroom), 1), None, DAYS_PER_SEASON)


def observed_growth(before: Player, after: Player, before_date: date, after_date: date) -> Growth:
    value_change = None
    if before.value is not None and after.value is not None:
        value_change = after.value - before.value
    return Growth(
        GrowthBasis.OBSERVED,
        float(after.current_ability - before.current_ability),
        value_change,
        (after_date - before_date).days,
    )
