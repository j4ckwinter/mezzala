from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.players import Tactic
from mezzala.core.positions import GROUP_POSITION_CODES
from mezzala.core.positions import PositionGroup as G


class Formation(StrEnum):
    FOUR_THREE_THREE = "4-3-3"
    FOUR_TWO_THREE_ONE = "4-2-3-1"
    FOUR_FOUR_TWO = "4-4-2"
    THREE_FIVE_TWO = "3-5-2"
    FOUR_FOUR_TWO_DIAMOND = "4-4-2 diamond"
    THREE_FOUR_THREE = "3-4-3"


STARTERS: dict[Formation, dict[G, int]] = {
    Formation.FOUR_THREE_THREE: {
        G.GOALKEEPER: 1, G.CENTRE_BACK: 2, G.LEFT_BACK: 1, G.RIGHT_BACK: 1,
        G.DEFENSIVE_MIDFIELD: 1, G.CENTRAL_MIDFIELD: 2, G.LEFT_WING: 1, G.RIGHT_WING: 1, G.STRIKER: 1,
    },
    Formation.FOUR_TWO_THREE_ONE: {
        G.GOALKEEPER: 1, G.CENTRE_BACK: 2, G.LEFT_BACK: 1, G.RIGHT_BACK: 1, G.DEFENSIVE_MIDFIELD: 1,
        G.CENTRAL_MIDFIELD: 1, G.ATTACKING_MIDFIELD: 1, G.LEFT_WING: 1, G.RIGHT_WING: 1, G.STRIKER: 1,
    },
    Formation.FOUR_FOUR_TWO: {
        G.GOALKEEPER: 1, G.CENTRE_BACK: 2, G.LEFT_BACK: 1, G.RIGHT_BACK: 1,
        G.CENTRAL_MIDFIELD: 2, G.LEFT_WING: 1, G.RIGHT_WING: 1, G.STRIKER: 2,
    },
    Formation.THREE_FIVE_TWO: {
        G.GOALKEEPER: 1, G.CENTRE_BACK: 3, G.LEFT_BACK: 1, G.RIGHT_BACK: 1,
        G.DEFENSIVE_MIDFIELD: 1, G.CENTRAL_MIDFIELD: 2, G.STRIKER: 2,
    },
    Formation.FOUR_FOUR_TWO_DIAMOND: {
        G.GOALKEEPER: 1, G.CENTRE_BACK: 2, G.LEFT_BACK: 1, G.RIGHT_BACK: 1,
        G.DEFENSIVE_MIDFIELD: 1, G.CENTRAL_MIDFIELD: 2, G.ATTACKING_MIDFIELD: 1, G.STRIKER: 2,
    },
    Formation.THREE_FOUR_THREE: {
        G.GOALKEEPER: 1, G.CENTRE_BACK: 3, G.LEFT_BACK: 1, G.RIGHT_BACK: 1,
        G.CENTRAL_MIDFIELD: 2, G.LEFT_WING: 1, G.RIGHT_WING: 1, G.STRIKER: 1,
    },
}  # fmt: skip

PLAYERS_PER_STARTING_PLACE = 2


@dataclass(frozen=True)
class Shape:
    name: str
    starters: Mapping[G, int]


def shape_for(formation: Formation) -> Shape:
    return Shape(formation.value, STARTERS[formation])


DEFAULT_FORMATION = Formation.FOUR_THREE_THREE
GROUP_OF_POSITION = {code: group for group, codes in GROUP_POSITION_CODES.items() for code in codes}


CENTRAL_MIDFIELD_GROUPS = frozenset({G.DEFENSIVE_MIDFIELD, G.CENTRAL_MIDFIELD})


def merge_central_midfield(counts: Mapping[G | None, int] | Mapping[G, int]) -> Counter[G | None]:
    merged: Counter[G | None] = Counter()
    for group, count in counts.items():
        merged[G.CENTRAL_MIDFIELD if group in CENTRAL_MIDFIELD_GROUPS else group] += count
    return merged


def shape_of(positions: Iterable[str | None]) -> Formation | None:
    counts = Counter(GROUP_OF_POSITION.get(code) if code is not None else None for code in positions)
    exact = next((formation for formation, starters in STARTERS.items() if counts == Counter(starters)), None)
    if exact is not None:
        return exact
    merged = merge_central_midfield(counts)
    return next(
        (formation for formation, starters in STARTERS.items() if merged == merge_central_midfield(Counter(starters))),
        None,
    )


def saved_formation(tactics: Iterable[Tactic]) -> tuple[Formation, Tactic] | None:
    for tactic in tactics:
        formation = shape_of(tactic.positions)
        if formation is not None:
            return formation, tactic
    return None
