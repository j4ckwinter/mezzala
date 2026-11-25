from enum import StrEnum

from mezzala.core.players import Player

TWO_FOOTED_FROM = 15


class Foot(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    EITHER = "either"


def preferred_foot(player: Player) -> Foot | None:
    if player.left_foot is None or player.right_foot is None:
        return None
    if player.left_foot == player.right_foot or min(player.left_foot, player.right_foot) >= TWO_FOOTED_FROM:
        return Foot.EITHER
    return Foot.LEFT if player.left_foot > player.right_foot else Foot.RIGHT


def weak_foot(player: Player) -> int | None:
    if player.left_foot is None or player.right_foot is None:
        return None
    return min(player.left_foot, player.right_foot)
