from enum import StrEnum

from mezzala.core.players import Player


class PositionGroup(StrEnum):
    GOALKEEPER = "goalkeeper"
    CENTRE_BACK = "centre back"
    LEFT_BACK = "left back"
    RIGHT_BACK = "right back"
    DEFENSIVE_MIDFIELD = "defensive midfield"
    CENTRAL_MIDFIELD = "central midfield"
    ATTACKING_MIDFIELD = "attacking midfield"
    LEFT_WING = "left wing"
    RIGHT_WING = "right wing"
    STRIKER = "striker"


GROUP_POSITION_CODES: dict[PositionGroup, tuple[str, ...]] = {
    PositionGroup.GOALKEEPER: ("gk",),
    PositionGroup.CENTRE_BACK: ("dc", "sw"),
    PositionGroup.LEFT_BACK: ("dl", "wbl"),
    PositionGroup.RIGHT_BACK: ("dr", "wbr"),
    PositionGroup.DEFENSIVE_MIDFIELD: ("dm",),
    PositionGroup.CENTRAL_MIDFIELD: ("mc",),
    PositionGroup.ATTACKING_MIDFIELD: ("amc",),
    PositionGroup.LEFT_WING: ("aml", "ml"),
    PositionGroup.RIGHT_WING: ("amr", "mr"),
    PositionGroup.STRIKER: ("stc",),
}

NATURAL_POSITION_RATING = 18
ACCOMPLISHED_POSITION_RATING = 15


class Fit(StrEnum):
    NATURAL = "natural"
    ACCOMPLISHED = "accomplished"
    OUT_OF_POSITION = "out of position"


def group_rating(player: Player, group: PositionGroup) -> int:
    return max(player.position_ratings.get(code, 0) for code in GROUP_POSITION_CODES[group])


def fit(player: Player, group: PositionGroup) -> Fit:
    rating = group_rating(player, group)
    if rating >= NATURAL_POSITION_RATING:
        return Fit.NATURAL
    if rating >= ACCOMPLISHED_POSITION_RATING:
        return Fit.ACCOMPLISHED
    return Fit.OUT_OF_POSITION


def covers(player: Player, group: PositionGroup) -> bool:
    return group_rating(player, group) >= ACCOMPLISHED_POSITION_RATING


def primary_group(player: Player) -> PositionGroup:
    return max(PositionGroup, key=lambda group: group_rating(player, group))


def is_goalkeeper(player: Player) -> bool:
    return primary_group(player) is PositionGroup.GOALKEEPER
