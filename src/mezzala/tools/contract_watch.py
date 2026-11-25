from dataclasses import dataclass

from mezzala.core.formations import Formation
from mezzala.core.lineup import Bar, describe_bar, level_in, weakest_starters
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.reach import within_reach
from mezzala.core.squad import available_squad, is_outside_club, leaves_within, owned_players
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View

KEY_PLAYER_MARGIN = 5


@dataclass(frozen=True)
class ExpiringOwnPlayer:
    player: PlayerSummary
    leaves: str
    advice: str


@dataclass(frozen=True)
class Target:
    player: PlayerSummary
    position: str
    improves_on: str
    reason: str


@dataclass(frozen=True)
class ContractWatch:
    within_months: int
    own_expiring: list[ExpiringOwnPlayer]
    free_agents: list[Target]
    pre_contract_targets: list[Target]


def own_advice(player: Player, snapshot: Snapshot, bars: dict[PositionGroup, Bar | None]) -> str:
    margins = [level_in(player, group) - bar.level for group, bar in bars.items() if bar and covers(player, group)]
    if player.on_loan and player.club_uid == snapshot.club_uid:
        return "loan player returning to his parent club; replace or extend the loan"
    if margins and max(margins) >= -KEY_PLAYER_MARGIN:
        return "first-team level: renew, or sell before he can leave for free"
    return "squad player: let him run down or sell for what you can get"


def best_improvement(
    player: Player, bars: dict[PositionGroup, Bar | None], view: View
) -> tuple[PositionGroup, str] | None:
    options: list[tuple[int, PositionGroup, str]] = []
    for group, bar in bars.items():
        if not covers(player, group):
            continue
        level = level_in(player, group)
        if bar is None:
            options.append((level, group, "nobody (a gap)"))
        elif level > bar.level:
            options.append((level - bar.level, group, describe_bar(bar, view)))
    if not options:
        return None
    _, group, improves_on = max(options, key=lambda option: option[0])
    return group, improves_on


def target(player: Player, bars: dict[PositionGroup, Bar | None], why: str, view: View) -> Target | None:
    improvement = best_improvement(player, bars, view)
    if improvement is None:
        return None
    group, improves_on = improvement
    return Target(summarize(player, view), group.value, improves_on, why)


def best_first(found: list[tuple[int, Target]], limit: int) -> list[Target]:
    return [entry for _, entry in sorted(found, key=lambda item: item[0], reverse=True)[:limit]]


def contract_watch(
    snapshot: Snapshot,
    formation: Formation,
    within_months: int,
    max_age: int | None,
    reachable_only: bool,
    limit: int,
    view: View,
) -> ContractWatch:
    bars = weakest_starters(available_squad(snapshot), formation)
    free: list[tuple[int, Target]] = []
    pre_contract: list[tuple[int, Target]] = []
    loaned_in = [player for player in available_squad(snapshot) if player.on_loan]
    own = [
        ExpiringOwnPlayer(summarize(player, view), leaving.isoformat(), own_advice(player, snapshot, bars))
        for player in sorted([*owned_players(snapshot), *loaned_in], key=lambda p: p.current_ability, reverse=True)
        if (leaving := leaves_within(player, snapshot.club_uid, snapshot.game_date, within_months)) is not None
    ]
    for player in snapshot.players:
        if max_age is not None and player.age > max_age:
            continue
        if reachable_only and not within_reach(player, snapshot):
            continue
        if player.is_free_agent:
            found = target(player, bars, "free agent: wages only, no fee", view)
            if found is not None:
                free.append((player.current_ability, found))
            continue
        if not is_outside_club(player, snapshot.club_uid) or player.on_loan:
            continue
        leaving = leaves_within(player, snapshot.club_uid, snapshot.game_date, within_months)
        if leaving is not None:
            why = f"contract ends {leaving.isoformat()}: pre-contract or a cut-price fee"
            found = target(player, bars, why, view)
            if found is not None:
                pre_contract.append((player.current_ability, found))
    return ContractWatch(within_months, own[:limit], best_first(free, limit), best_first(pre_contract, limit))
