from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.growth import expected_gain_over
from mezzala.core.players import Player, Snapshot, is_same_person
from mezzala.core.squad import YOUNG_PLAYER_MAX_AGE, belongs_to_club, plays_for_club
from mezzala.core.summary import PlayerSummary, summarize

UNDERDEVELOPING_SHARE = 0.5
MIN_EXPECTED_GAIN = 1.0
DECLINE_MIN_DROP = 3
MIN_DAYS_BETWEEN = 90


class CheckScope(StrEnum):
    OWN = "own"
    EVERYONE = "everyone"


@dataclass(frozen=True)
class DevelopmentEntry:
    player: PlayerSummary
    ability_change: int
    expected_change: float | None
    detail: str


@dataclass(frozen=True)
class DevelopmentCheck:
    compared_with: str | None
    explanation: str
    not_developing: list[DevelopmentEntry]
    declining: list[DevelopmentEntry]


def no_comparison(baseline: Snapshot | None, current: Snapshot) -> str | None:
    if baseline is None:
        return "Only one snapshot so far. Development shows once the save has a later snapshot to compare with."
    days = (current.game_date - baseline.game_date).days
    if days < MIN_DAYS_BETWEEN:
        return (
            f"The snapshot compared with ({baseline.game_date.isoformat()}) is only {days} days earlier; development "
            f"needs at least {MIN_DAYS_BETWEEN} days to judge. Ask with an earlier since date."
        )
    return None


def in_scope(player: Player, club_uid: int, scope: CheckScope) -> bool:
    match scope:
        case CheckScope.OWN:
            return plays_for_club(player, club_uid) or belongs_to_club(player, club_uid)
        case CheckScope.EVERYONE:
            return True


def development_check(
    current: Snapshot, baseline: Snapshot | None, scope: CheckScope, min_pa: int, limit: int
) -> DevelopmentCheck:
    reason = no_comparison(baseline, current)
    if baseline is None or reason is not None:
        return DevelopmentCheck(None, reason or "", [], [])
    days = (current.game_date - baseline.game_date).days
    earlier = baseline.by_uid()
    behind: list[tuple[float, DevelopmentEntry]] = []
    declining: list[tuple[int, DevelopmentEntry]] = []
    for player in current.players:
        before = earlier.get(player.uid)
        if before is None or not is_same_person(before, player) or not in_scope(player, current.club_uid, scope):
            continue
        change = player.current_ability - before.current_ability
        if before.age <= YOUNG_PLAYER_MAX_AGE and before.potential_ability >= min_pa:
            expected = expected_gain_over(before, days)
            if expected >= MIN_EXPECTED_GAIN and change < UNDERDEVELOPING_SHARE * expected:
                detail = f"gained {change} CA in {days} days, expected about {expected:.0f}"
                behind.append(
                    (expected - change, DevelopmentEntry(summarize(player), change, round(expected, 1), detail))
                )
        if change <= -DECLINE_MIN_DROP:
            detail = f"CA {before.current_ability} -> {player.current_ability} in {days} days at {player.age}"
            declining.append((change, DevelopmentEntry(summarize(player), change, None, detail)))
    behind.sort(key=lambda item: item[0], reverse=True)
    declining.sort(key=lambda item: item[0])
    return DevelopmentCheck(
        baseline.game_date.isoformat(),
        f"Compared with the snapshot of {baseline.game_date.isoformat()}, {days} days earlier.",
        [entry for _, entry in behind[:limit]],
        [entry for _, entry in declining[:limit]],
    )
