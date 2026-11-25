from dataclasses import dataclass
from statistics import mean

from mezzala.core.assignment import BLOCKED, min_cost_assignment
from mezzala.core.feet import preferred_foot
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import Fit, covers, fit
from mezzala.core.roles import FootPreference, role_score
from mezzala.core.shapes import Slot
from mezzala.core.squad import available_squad

ROLE_ACCOMPLISHED_PENALTY = 1.0
ALTERNATIVES_PER_SLOT = 2
WEAKEST_SLOTS_SHOWN = 3
FILLED_SLOT_BONUS = 1_000
SCORE_DECIMALS = 1

EXPLANATION = (
    "Each slot is filled by the player whose attributes suit its role best, using each player once. A role score "
    "is out of 20: the role's key attributes count double, its preferable ones once, as FM describes the role. "
    f"Playing where he is only accomplished costs {ROLE_ACCOMPLISHED_PENALTY:g}, and a foot that suits the role "
    "and side (opposite for inside forwards, inverted wingers and wing-backs, same side for wingers and "
    "full-backs) adds 1 or costs 1. These are mezzala's weightings, not the match engine's."
)


@dataclass(frozen=True)
class SlotFit:
    slot: str
    role: str
    player: str | None
    role_score: float | None
    fit: str | None
    preferred_foot: str | None
    alternatives: list[str]


@dataclass(frozen=True)
class TacticFit:
    explanation: str
    average_role_score: float | None
    slots: list[SlotFit]
    weakest_slots: list[str]


def slot_score(player: Player, slot: Slot) -> float | None:
    if not covers(player, slot.group):
        return None
    penalty = 0.0 if fit(player, slot.group) is Fit.NATURAL else ROLE_ACCOMPLISHED_PENALTY
    return round(role_score(player, slot.role, slot.side) - penalty, SCORE_DECIMALS)


def best_eleven(squad: list[Player], slots: list[Slot]) -> list[Player | None]:
    cost = [
        [BLOCKED if (score := slot_score(player, slot)) is None else -(FILLED_SLOT_BONUS + score) for player in squad]
        + [0.0] * len(slots)
        for slot in slots
    ]
    chosen = min_cost_assignment(cost) if slots else []
    return [
        squad[column] if column < len(squad) and row[column] != BLOCKED else None
        for row, column in zip(cost, chosen, strict=True)
    ]


def alternatives(squad: list[Player], slot: Slot, starters: set[int]) -> list[str]:
    scored = [(score, p) for p in squad if p.uid not in starters and (score := slot_score(p, slot)) is not None]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [f"{p.name} ({score:g})" for score, p in scored[:ALTERNATIVES_PER_SLOT]]


def slot_fit(slot: Slot, player: Player | None, squad: list[Player], starters: set[int]) -> SlotFit:
    foot = preferred_foot(player) if player else None
    return SlotFit(
        slot=slot.label,
        role=slot.role.name
        if slot.role.foot is FootPreference.ANY
        else f"{slot.role.name} ({slot.role.foot.value} foot)",
        player=player.name if player else None,
        role_score=slot_score(player, slot) if player else None,
        fit=fit(player, slot.group).value if player else None,
        preferred_foot=foot.value if foot else None,
        alternatives=alternatives(squad, slot, starters),
    )


def tactic_fit(snapshot: Snapshot, slots: list[Slot]) -> TacticFit:
    squad = available_squad(snapshot)
    eleven = best_eleven(squad, slots)
    starters = {player.uid for player in eleven if player is not None}
    fits = [slot_fit(slot, player, squad, starters) for slot, player in zip(slots, eleven, strict=True)]
    scored = [entry.role_score for entry in fits if entry.role_score is not None]
    weakest = sorted(fits, key=lambda entry: -1.0 if entry.role_score is None else entry.role_score)
    return TacticFit(
        EXPLANATION,
        round(mean(scored), SCORE_DECIMALS) if scored else None,
        fits,
        [f"{entry.slot} {entry.role}: {entry.player or 'nobody'}" for entry in weakest[:WEAKEST_SLOTS_SHOWN]],
    )
