from dataclasses import dataclass
from enum import StrEnum
from statistics import median

from mezzala.core.metrics import PeerMedians, weekly_wage
from mezzala.core.money import format_weekly_wage
from mezzala.core.players import Player, Snapshot
from mezzala.core.reach import REPUTATION_REACH

GOING_RATE_ABILITY_BAND = 5
WIDER_GOING_RATE_ABILITY_BAND = 10
MIN_GOING_RATE_PLAYERS = 5


class WageSource(StrEnum):
    CURRENT = "his current wage"
    DOMESTIC = "the going rate at clubs like yours in your country"
    SIMILAR_CLUBS = "the going rate at clubs like yours"
    WORLDWIDE = "similar players worldwide"


@dataclass(frozen=True)
class WageEstimate:
    amount: int
    source: WageSource


@dataclass(frozen=True)
class WageGuide:
    domestic: list[tuple[int, int]]
    similar_clubs: list[tuple[int, int]]
    peers: PeerMedians

    def going_rate(self, player: Player) -> WageEstimate | None:
        searches = (
            (self.domestic, GOING_RATE_ABILITY_BAND, WageSource.DOMESTIC),
            (self.domestic, WIDER_GOING_RATE_ABILITY_BAND, WageSource.DOMESTIC),
            (self.similar_clubs, GOING_RATE_ABILITY_BAND, WageSource.SIMILAR_CLUBS),
        )
        for wages, band, source in searches:
            nearby = [wage for ability, wage in wages if abs(ability - player.current_ability) <= band]
            if len(nearby) >= MIN_GOING_RATE_PLAYERS:
                return WageEstimate(round(median(nearby)), source)
        estimate = self.peers.of(player)
        return None if estimate is None else WageEstimate(round(estimate), WageSource.WORLDWIDE)

    def expected(self, player: Player) -> WageEstimate | None:
        rate = self.going_rate(player)
        if player.wage and (rate is None or player.wage >= rate.amount):
            return WageEstimate(player.wage, WageSource.CURRENT)
        return rate


def at_similar_club(player: Player, snapshot: Snapshot) -> bool:
    if player.club_reputation is None:
        return False
    return abs(player.club_reputation - snapshot.club_reputation) <= REPUTATION_REACH


def wage_guide(snapshot: Snapshot) -> WageGuide:
    similar = [
        player for player in snapshot.players if player.first_team and player.wage and at_similar_club(player, snapshot)
    ]
    return WageGuide(
        [(p.current_ability, p.wage or 0) for p in similar if p.club_nation_id == snapshot.club_nation_id],
        [(p.current_ability, p.wage or 0) for p in similar],
        PeerMedians(snapshot.players, weekly_wage),
    )


def describe_wage(estimate: WageEstimate | None) -> str:
    if estimate is None:
        return "unknown"
    if estimate.source is WageSource.CURRENT:
        return format_weekly_wage(estimate.amount)
    return f"about {format_weekly_wage(estimate.amount)} ({estimate.source.value})"


def amount(estimate: WageEstimate | None) -> int | None:
    return None if estimate is None else estimate.amount
