from dataclasses import dataclass

from mezzala.core.formations import Formation
from mezzala.core.lineup import weakest_starters
from mezzala.core.metrics import PeerMedians, weekly_wage
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import within_reach
from mezzala.core.squad import available_squad, is_outside_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.tools.squad_gaps import squad_gaps

ALTERNATIVES_PER_POSITION = 2


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

    def spend(self, fee: int, wage: int | None) -> None:
        if self.fees is not None:
            self.fees -= fee
        if self.wages is not None and wage is not None:
            self.wages -= wage


def expected_wage(player: Player, wages: PeerMedians) -> int | None:
    if player.wage:
        return player.wage
    estimate = wages.of(player)
    return None if estimate is None else round(estimate)


def describe_wage(player: Player, wage: int | None) -> str:
    if wage is None:
        return "unknown"
    if not player.wage:
        return f"about {format_weekly_wage(wage)} (estimated from similar players)"
    return format_weekly_wage(wage)


def fee_for(player: Player) -> int | None:
    return 0 if player.costs_no_fee else player.value


def candidates(
    snapshot: Snapshot,
    group: PositionGroup,
    bar: Player | None,
    budget: SpendingRoom,
    taken: set[int],
    wages: PeerMedians,
) -> list[Player]:
    found = [
        player
        for player in snapshot.players
        if player.uid not in taken
        and is_outside_club(player, snapshot.club_uid)
        and covers(player, group)
        and within_reach(player, snapshot)
        and (bar is None or player.current_ability > bar.current_ability)
        and (fee := fee_for(player)) is not None
        and budget.affords(fee, expected_wage(player, wages))
    ]
    return sorted(found, key=lambda player: (-player.current_ability, fee_for(player) or 0))


def describe_bar(bar: Player | None) -> str:
    return "nobody (an empty place)" if bar is None else f"{bar.name} ({bar.current_ability})"


def shortlist(
    snapshot: Snapshot, formation: Formation, transfer_budget: int | None, weekly_wage_budget: int | None
) -> Shortlist:
    bars = weakest_starters(available_squad(snapshot), formation)
    wages_of_peers = PeerMedians(snapshot.players, weekly_wage)
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
        options = candidates(snapshot, group, bar, budget, taken, wages_of_peers)
        if not options:
            picks.append(ShortlistPick(position.group, position.issues, None, describe_bar(bar), "none", "none", []))
            continue
        target = options[0]
        fee = fee_for(target) or 0
        wage = expected_wage(target, wages_of_peers)
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
                describe_wage(target, wage),
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
