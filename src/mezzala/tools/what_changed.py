from dataclasses import dataclass

from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Player, Snapshot, is_same_person
from mezzala.core.squad import belongs_to_club, plays_for_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.tools.regen_intake import regen_intake

ABILITY_CHANGE_MIN = 2
VALUE_CHANGE_SHARE = 0.25
NOTABLE_TRANSFER_VALUE = 5_000_000
NOTABLE_TRANSFERS_SHOWN = 10
REGENS_SHOWN = 3

NO_EARLIER_SNAPSHOT = (
    "This is the first snapshot of the save, so there is nothing to compare with yet. Save again later in the "
    "game and ask again."
)


@dataclass(frozen=True)
class Change:
    player: PlayerSummary
    detail: str


@dataclass(frozen=True)
class WhatChanged:
    compared_with: str | None
    explanation: str
    budget: list[str]
    joined: list[Change]
    left: list[Change]
    ability: list[Change]
    contracts: list[Change]
    values: list[Change]
    new_regens: int
    best_new_regens: list[PlayerSummary]
    notable_transfers: list[Change]


def is_ours(player: Player, club_uid: int) -> bool:
    return plays_for_club(player, club_uid) or belongs_to_club(player, club_uid)


def budget_changes(before: Snapshot, after: Snapshot) -> list[str]:
    changes: list[str] = []
    if before.budget.transfer_remaining != after.budget.transfer_remaining:
        changes.append(
            f"transfer budget {format_money(before.budget.transfer_remaining)} -> "
            f"{format_money(after.budget.transfer_remaining)}"
        )
    if before.budget.wage_headroom_weekly != after.budget.wage_headroom_weekly:
        changes.append(
            f"wage room {format_weekly_wage(before.budget.wage_headroom_weekly)} -> "
            f"{format_weekly_wage(after.budget.wage_headroom_weekly)}"
        )
    return changes


def matched(before: Snapshot, after: Snapshot) -> list[tuple[Player, Player]]:
    earlier = before.by_uid()
    pairs: list[tuple[Player, Player]] = []
    for player in after.players:
        old = earlier.get(player.uid)
        if old is not None and is_same_person(old, player):
            pairs.append((old, player))
    return pairs


def squad_moves(before: Snapshot, after: Snapshot) -> tuple[list[Change], list[Change]]:
    club = after.club_uid
    now = {player.uid: player for player in after.players if is_ours(player, club)}
    then = {player.uid: player for player in before.players if is_ours(player, club)}
    current = after.by_uid()
    earlier = before.by_uid()
    joined = [Change(summarize(p), f"from {then_club(earlier, p)}") for uid, p in now.items() if uid not in then]
    left = [
        Change(
            summarize(p), f"now at {current[uid].club_name or 'no club'}" if uid in current else "no longer in the save"
        )
        for uid, p in then.items()
        if uid not in now
    ]
    return joined, left


def then_club(earlier: dict[int, Player], player: Player) -> str:
    old = earlier.get(player.uid)
    if old is None or not is_same_person(old, player):
        return "nowhere (new to the save)"
    return old.club_name or "no club"


def own_changes(pairs: list[tuple[Player, Player]], club: int) -> tuple[list[Change], list[Change], list[Change]]:
    ability: list[tuple[int, Change]] = []
    contracts: list[Change] = []
    values: list[Change] = []
    for old, new in pairs:
        if not is_ours(new, club) or not is_ours(old, club):
            continue
        gain = new.current_ability - old.current_ability
        if abs(gain) >= ABILITY_CHANGE_MIN:
            ability.append((gain, Change(summarize(new), f"CA {old.current_ability} -> {new.current_ability}")))
        if old.contract_end != new.contract_end:
            before_end = old.contract_end.isoformat() if old.contract_end else "none"
            after_end = new.contract_end.isoformat() if new.contract_end else "none"
            contracts.append(Change(summarize(new), f"contract {before_end} -> {after_end}"))
        if old.value and new.value and abs(new.value - old.value) >= VALUE_CHANGE_SHARE * old.value:
            values.append(Change(summarize(new), f"value {format_money(old.value)} -> {format_money(new.value)}"))
    ability.sort(key=lambda item: abs(item[0]), reverse=True)
    return [change for _, change in ability], contracts, values


def notable_transfers(pairs: list[tuple[Player, Player]], club: int) -> list[Change]:
    moved = [
        (old, new)
        for old, new in pairs
        if old.club_uid != new.club_uid
        and (new.value or 0) >= NOTABLE_TRANSFER_VALUE
        and not is_ours(new, club)
        and not is_ours(old, club)
    ]
    moved.sort(key=lambda pair: pair[1].value or 0, reverse=True)
    return [
        Change(summarize(new), f"{old.club_name or 'no club'} -> {new.club_name or 'no club'}")
        for old, new in moved[:NOTABLE_TRANSFERS_SHOWN]
    ]


def what_changed(current: Snapshot, previous: Snapshot | None) -> WhatChanged:
    if previous is None:
        return WhatChanged(None, NO_EARLIER_SNAPSHOT, [], [], [], [], [], [], 0, [], [])
    pairs = matched(previous, current)
    joined, left = squad_moves(previous, current)
    ability, contracts, values = own_changes(pairs, current.club_uid)
    regens = regen_intake(current, previous, 0, False, REGENS_SHOWN)
    return WhatChanged(
        compared_with=previous.game_date.isoformat(),
        explanation=f"Changes between the snapshots of {previous.game_date.isoformat()} and "
        f"{current.game_date.isoformat()}.",
        budget=budget_changes(previous, current),
        joined=joined,
        left=left,
        ability=ability,
        contracts=contracts,
        values=values,
        new_regens=regens.total_new,
        best_new_regens=regens.regens,
        notable_transfers=notable_transfers(pairs, current.club_uid),
    )
