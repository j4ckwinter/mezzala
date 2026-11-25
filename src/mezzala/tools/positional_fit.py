from dataclasses import dataclass

from mezzala.core.formations import Shape
from mezzala.core.lineup import pick_lineup
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers, fit
from mezzala.core.profile import position_score
from mezzala.core.squad import available_squad

BETTER_FIT_MARGIN = 1.0


@dataclass(frozen=True)
class StarterFit:
    name: str
    position: str
    fit: str
    attribute_score: float
    better_suited_to: str | None
    score_there: float | None


@dataclass(frozen=True)
class PositionalFit:
    formation: str
    explanation: str
    starters: list[StarterFit]
    misplaced: list[str]


EXPLANATION = (
    "Each starter's key-attribute score (1-20) for the position he is picked in, and any other position he can "
    f"play where his attributes score at least {BETTER_FIT_MARGIN:g} higher. Treat these as hints: the scores weigh "
    "a fixed set of key attributes per position and cannot see the roles your tactic asks for."
)


def best_other_position(player: Player, picked: PositionGroup) -> tuple[PositionGroup, float] | None:
    options = [
        (group, position_score(player, group))
        for group in PositionGroup
        if group is not picked and covers(player, group)
    ]
    return max(options, key=lambda option: option[1], default=None)


def starter_fit(player: Player, group: PositionGroup) -> StarterFit:
    score = position_score(player, group)
    other = best_other_position(player, group)
    better = other is not None and other[1] - score >= BETTER_FIT_MARGIN
    return StarterFit(
        player.name, group.value, fit(player, group).value, score,
        other[0].value if better and other else None, other[1] if better and other else None,
    )  # fmt: skip


def positional_fit(snapshot: Snapshot, shape: Shape) -> PositionalFit:
    lineup = pick_lineup(available_squad(snapshot), shape)
    starters = [starter_fit(place.player, place.group) for place in lineup.places if place.player is not None]
    misplaced = [
        f"{s.name}: picked at {s.position} ({s.attribute_score:g}) but better suited to {s.better_suited_to} "
        f"({s.score_there:g})"
        for s in starters
        if s.better_suited_to is not None
    ]
    return PositionalFit(shape.name, EXPLANATION, starters, misplaced)
