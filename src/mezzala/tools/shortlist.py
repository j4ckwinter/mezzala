from dataclasses import dataclass
from enum import StrEnum
from statistics import median

from mezzala.core.formations import Formation
from mezzala.core.lineup import weakest_starters
from mezzala.core.metrics import PeerMedians, weekly_wage
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import REPUTATION_REACH, within_reach
from mezzala.core.squad import available_squad, is_outside_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.tools.squad_gaps import LOOKAHEAD_SEASONS, ageing_age, squad_gaps

ALTERNATIVES_PER_POSITION = 2
GOING_RATE_ABILITY_BAND = 5
MIN_GOING_RATE_PLAYERS = 5
CLOSE_ENOUGH_ABILITY = 3


@dataclass(frozen=True)
class ShortlistPick:
    position: str
    why: list[str]
    target: PlayerSummary | None
    improves_on: str
    fee: str
    weekly_wage: str
    alternatives: list[PlayerSummary]


@dataclass(frozen=True)
class Shortlist:
    formation: str
    transfer_budget: str
    weekly_wage_budget: str
    total_fees: str
    total_weekly_wages: str
    picks: list[ShortlistPick]


@dataclass
class SpendingRoom:
    fees: int | None
    wages: int | None

    def affords(self, fee: int, wage: int | None) -> bool:
        fee_fits = self.fees is None or fee <= self.fees
        wage_fits = self.wages is None or (wage is not None and wage <= self.wages)
        return fee_fits and wage_fits

    def share_used(self, fee: int, wage: int | None) -> float:
        fee_share = fee / self.fees if self.fees else 0.0
        wage_share = (wage or 0) / self.wages if self.wages else 0.0
        return max(fee_share, wage_share)

    def spend(self, fee: int, wage: int | None) -> None:
        if self.fees is not None:
            self.fees -= fee
        if self.wages is not None and wage is not None:
            self.wages -= wage


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
        for wages, source in ((self.domestic, WageSource.DOMESTIC), (self.similar_clubs, WageSource.SIMILAR_CLUBS)):
            nearby = [
                wage for ability, wage in wages if abs(ability - player.current_ability) <= GOING_RATE_ABILITY_BAND
            ]
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


def fee_for(player: Player) -> int | None:
    return 0 if player.costs_no_fee else player.value


def age_limit(group: PositionGroup) -> int:
    return ageing_age(group) - LOOKAHEAD_SEASONS - 1


def candidates(
    snapshot: Snapshot,
    group: PositionGroup,
    bar: Player | None,
    max_age: int,
    budget: SpendingRoom,
    taken: set[int],
    wages: WageGuide,
) -> list[Player]:
    found = [
        player
        for player in snapshot.players
        if player.uid not in taken
        and is_outside_club(player, snapshot.club_uid)
        and covers(player, group)
        and player.age <= max_age
        and within_reach(player, snapshot)
        and (bar is None or player.current_ability > bar.current_ability)
        and (fee := fee_for(player)) is not None
        and budget.affords(fee, amount(wages.expected(player)))
    ]
    if not found:
        return []
    best = max(player.current_ability for player in found)
    return sorted(
        found,
        key=lambda player: (
            player.current_ability < best - CLOSE_ENOUGH_ABILITY,
            budget.share_used(fee_for(player) or 0, amount(wages.expected(player))),
            -player.current_ability,
        ),
    )


def describe_bar(bar: Player | None) -> str:
    return "nobody (an empty place)" if bar is None else f"{bar.name} ({bar.current_ability})"


def shortlist(
    snapshot: Snapshot, formation: Formation, transfer_budget: int | None, weekly_wage_budget: int | None
) -> Shortlist:
    bars = weakest_starters(available_squad(snapshot), formation)
    wages_of_peers = wage_guide(snapshot)
    budget = SpendingRoom(transfer_budget, weekly_wage_budget)
    taken: set[int] = set()
    fees = 0
    wages = 0
    picks: list[ShortlistPick] = []
    for position in squad_gaps(snapshot, formation).positions:
        if not position.issues:
            continue
        group = PositionGroup(position.group)
        bar = bars[group]
        options = candidates(snapshot, group, bar, age_limit(group), budget, taken, wages_of_peers)
        if not options:
            picks.append(ShortlistPick(position.group, position.issues, None, describe_bar(bar), "none", "none", []))
            continue
        target = options[0]
        fee = fee_for(target) or 0
        estimate = wages_of_peers.expected(target)
        wage = amount(estimate)
        budget.spend(fee, wage)
        taken.add(target.uid)
        fees += fee
        wages += wage or 0
        picks.append(
            ShortlistPick(
                position.group,
                position.issues,
                summarize(target),
                describe_bar(bar),
                format_money(fee),
                describe_wage(estimate),
                [summarize(player) for player in options[1 : 1 + ALTERNATIVES_PER_POSITION]],
            )
        )
    return Shortlist(
        formation.value,
        "no limit" if transfer_budget is None else format_money(transfer_budget),
        "no limit" if weekly_wage_budget is None else format_weekly_wage(weekly_wage_budget),
        format_money(fees),
        format_weekly_wage(wages),
        picks,
    )
