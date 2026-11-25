from dataclasses import dataclass

from mezzala.core.formations import Shape
from mezzala.core.lineup import Bar, describe_bar, level_in, weakest_starters
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import within_reach
from mezzala.core.squad import LOOKAHEAD_SEASONS, ageing_age, available_squad, is_outside_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View
from mezzala.core.wages import WageGuide, amount, describe_wage, wage_guide
from mezzala.tools.squad_gaps import squad_gaps

ALTERNATIVES_PER_POSITION = 2
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


def fee_for(player: Player) -> int | None:
    return 0 if player.costs_no_fee else player.value


def age_limit(group: PositionGroup) -> int:
    return ageing_age(group) - LOOKAHEAD_SEASONS - 1


def candidates(
    snapshot: Snapshot,
    group: PositionGroup,
    bar: Bar | None,
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
        and (bar is None or level_in(player, group) > bar.level)
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


def improves_on(bar: Bar | None, view: View) -> str:
    return "nobody (an empty place)" if bar is None else describe_bar(bar, view)


def shortlist(
    snapshot: Snapshot,
    shape: Shape,
    transfer_budget: int | None,
    weekly_wage_budget: int | None,
    view: View,
) -> Shortlist:
    bars = weakest_starters(available_squad(snapshot), shape)
    wages_of_peers = wage_guide(snapshot)
    budget = SpendingRoom(transfer_budget, weekly_wage_budget)
    taken: set[int] = set()
    fees = 0
    wages = 0
    picks: list[ShortlistPick] = []
    for position in squad_gaps(snapshot, shape, view).positions:
        if not position.issues:
            continue
        group = PositionGroup(position.group)
        bar = bars[group]
        options = candidates(snapshot, group, bar, age_limit(group), budget, taken, wages_of_peers)
        if not options:
            picks.append(
                ShortlistPick(position.group, position.issues, None, improves_on(bar, view), "none", "none", [])
            )
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
                summarize(target, view),
                improves_on(bar, view),
                format_money(fee),
                describe_wage(estimate),
                [summarize(player, view) for player in options[1 : 1 + ALTERNATIVES_PER_POSITION]],
            )
        )
    return Shortlist(
        shape.name,
        "no limit" if transfer_budget is None else format_money(transfer_budget),
        "no limit" if weekly_wage_budget is None else format_weekly_wage(weekly_wage_budget),
        format_money(fees),
        format_weekly_wage(wages),
        picks,
    )
