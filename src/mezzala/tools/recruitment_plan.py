from dataclasses import dataclass

from mezzala.core.formations import Shape
from mezzala.core.lineup import Bar, level_in, weakest_starters
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import within_reach
from mezzala.core.signing import Route, pre_contract_status, route_fee, signing_route, signing_warnings
from mezzala.core.squad import available_squad, is_outside_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View
from mezzala.core.wages import WageGuide, amount, describe_wage, wage_guide
from mezzala.tools.shortlist import CLOSE_ENOUGH_ABILITY, SpendingRoom, age_limit, improves_on
from mezzala.tools.squad_gaps import squad_gaps

OPTIONS_PER_POSITION = 5


@dataclass(frozen=True)
class Option:
    player: PlayerSummary
    route: str
    how: str
    fee: str
    expected_wage: str
    warnings: list[str]


@dataclass(frozen=True)
class PositionPlan:
    position: str
    why: list[str]
    improves_on: str
    pick: Option | None
    options: list[Option]


@dataclass(frozen=True)
class RecruitmentPlan:
    formation: str
    transfer_budget: str
    weekly_wage_room: str
    total_fees: str
    total_weekly_wages: str
    positions: list[PositionPlan]


@dataclass(frozen=True)
class Candidate:
    player: Player
    route: Route
    fee: int
    wage: int | None


def how_to_sign(candidate: Candidate, snapshot: Snapshot) -> str:
    match candidate.route:
        case Route.FREE_AGENT:
            return "free agent: wages only, no fee"
        case Route.PRE_CONTRACT:
            return pre_contract_status(candidate.player, snapshot.game_date)
        case Route.TRANSFER:
            return "transfer: his club will want a fee"


def option(candidate: Candidate, snapshot: Snapshot, wages: WageGuide, view: View) -> Option:
    player = candidate.player
    return Option(
        summarize(player, view),
        candidate.route.value,
        how_to_sign(candidate, snapshot),
        format_money(candidate.fee),
        describe_wage(wages.expected(player)),
        signing_warnings(player, snapshot),
    )


def candidates(
    snapshot: Snapshot, group: PositionGroup, bar: Bar | None, budget: SpendingRoom, wages: WageGuide
) -> list[Candidate]:
    found: list[Candidate] = []
    for player in snapshot.players:
        if not (
            is_outside_club(player, snapshot.club_uid)
            and covers(player, group)
            and player.age <= age_limit(group)
            and within_reach(player, snapshot)
            and (bar is None or level_in(player, group) > bar.level)
        ):
            continue
        route = signing_route(player, snapshot.game_date)
        fee = route_fee(player, route)
        wage = amount(wages.expected(player))
        if fee is not None and budget.affords(fee, wage):
            found.append(Candidate(player, route, fee, wage))
    if not found:
        return []
    best = max(level_in(c.player, group) for c in found)
    return sorted(
        found,
        key=lambda c: (
            level_in(c.player, group) < best - CLOSE_ENOUGH_ABILITY,
            budget.share_used(c.fee, c.wage),
            -level_in(c.player, group),
        ),
    )


def recruitment_plan(
    snapshot: Snapshot, shape: Shape, transfer_budget: int | None, weekly_wage_room: int | None, view: View
) -> RecruitmentPlan:
    bars = weakest_starters(available_squad(snapshot), shape)
    wages = wage_guide(snapshot)
    budget = SpendingRoom(transfer_budget, weekly_wage_room)
    taken: set[int] = set()
    fees = 0
    weekly = 0
    plans: list[PositionPlan] = []
    for position in squad_gaps(snapshot, shape, view).positions:
        if not position.issues:
            continue
        group = PositionGroup(position.group)
        bar = bars[group]
        ranked = [c for c in candidates(snapshot, group, bar, budget, wages) if c.player.uid not in taken]
        shown = ranked[:OPTIONS_PER_POSITION]
        pick = shown[0] if shown else None
        if pick is not None:
            budget.spend(pick.fee, pick.wage)
            taken.add(pick.player.uid)
            fees += pick.fee
            weekly += pick.wage or 0
        plans.append(
            PositionPlan(
                position.group,
                position.issues,
                improves_on(bar, view),
                None if pick is None else option(pick, snapshot, wages, view),
                [option(c, snapshot, wages, view) for c in shown],
            )
        )
    return RecruitmentPlan(
        shape.name,
        "no limit" if transfer_budget is None else format_money(transfer_budget),
        "no limit" if weekly_wage_room is None else format_weekly_wage(weekly_wage_room),
        format_money(fees),
        format_weekly_wage(weekly),
        plans,
    )
