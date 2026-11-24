from dataclasses import dataclass

from mezzala.formations import STARTERS, Formation
from mezzala.players import Player, Snapshot
from mezzala.positions import PositionGroup, covers
from mezzala.reach import within_reach
from mezzala.squad import assign_starters, available_squad, is_outside_club, leaves_within, owned_players
from mezzala.summary import PlayerSummary, summarize

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


def benchmarks(snapshot: Snapshot, formation: Formation) -> dict[PositionGroup, Player | None]:
    places = STARTERS[formation]
    assigned = assign_starters(available_squad(snapshot), places)
    return {group: starters[-1] if len(starters) == places[group] else None for group, starters in assigned.items()}


def own_advice(player: Player, snapshot: Snapshot, bars: dict[PositionGroup, Player | None]) -> str:
    best_bar = max(
        (bar.current_ability for group, bar in bars.items() if bar is not None and covers(player, group)),
        default=None,
    )
    if player.on_loan and player.club_uid == snapshot.club_uid:
        return "loan player returning to his parent club; replace or extend the loan"
    if best_bar is not None and player.current_ability >= best_bar - KEY_PLAYER_MARGIN:
        return "first-team level: renew, or sell before he can leave for free"
    return "squad player: let him run down or sell for what you can get"


def best_improvement(player: Player, bars: dict[PositionGroup, Player | None]) -> tuple[PositionGroup, str] | None:
    options: list[tuple[int, PositionGroup, str]] = []
    for group, bar in bars.items():
        if not covers(player, group):
            continue
        if bar is None:
            options.append((player.current_ability, group, "nobody (a gap)"))
        elif player.current_ability > bar.current_ability:
            options.append((player.current_ability - bar.current_ability, group, f"{bar.name} ({bar.current_ability})"))
    if not options:
        return None
    _, group, improves_on = max(options, key=lambda option: option[0])
    return group, improves_on


def target(player: Player, bars: dict[PositionGroup, Player | None], why: str) -> Target | None:
    improvement = best_improvement(player, bars)
    if improvement is None:
        return None
    group, improves_on = improvement
    return Target(summarize(player), group.value, improves_on, why)


def target_ability(entry: Target) -> int:
    return entry.player.current_ability


def contract_watch(
    snapshot: Snapshot,
    formation: Formation,
    within_months: int,
    max_age: int | None,
    reachable_only: bool,
    limit: int,
) -> ContractWatch:
    bars = benchmarks(snapshot, formation)
    free: list[Target] = []
    pre_contract: list[Target] = []
    loaned_in = [player for player in available_squad(snapshot) if player.on_loan]
    own = [
        ExpiringOwnPlayer(summarize(player), leaving.isoformat(), own_advice(player, snapshot, bars))
        for player in sorted([*owned_players(snapshot), *loaned_in], key=lambda p: p.current_ability, reverse=True)
        if (leaving := leaves_within(player, snapshot.club_uid, snapshot.game_date, within_months)) is not None
    ]
    for player in snapshot.players:
        if max_age is not None and player.age > max_age:
            continue
        if reachable_only and not within_reach(player, snapshot):
            continue
        if player.is_free_agent:
            found = target(player, bars, "free agent: wages only, no fee")
            if found is not None:
                free.append(found)
            continue
        if not is_outside_club(player, snapshot.club_uid) or player.on_loan:
            continue
        leaving = leaves_within(player, snapshot.club_uid, snapshot.game_date, within_months)
        if leaving is not None:
            found = target(player, bars, f"contract ends {leaving.isoformat()}: pre-contract or a cut-price fee")
            if found is not None:
                pre_contract.append(found)
    free.sort(key=target_ability, reverse=True)
    pre_contract.sort(key=target_ability, reverse=True)
    return ContractWatch(within_months, own[:limit], free[:limit], pre_contract[:limit])
