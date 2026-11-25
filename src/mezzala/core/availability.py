from datetime import date

from mezzala.core.players import Player


def injured_on(player: Player, day: date) -> bool:
    return player.injured_until is not None and player.injured_until >= day


def absence(player: Player, day: date) -> str | None:
    if injured_on(player, day) and player.injured_until is not None:
        what = player.injury or "injured"
        return f"{player.name}: {what}, back {player.injured_until.isoformat()}"
    if player.banned_from:
        return f"{player.name}: banned from {', '.join(player.banned_from)}"
    return None
