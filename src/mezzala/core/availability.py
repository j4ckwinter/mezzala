from datetime import date

from mezzala.core.players import Player

INJURY_PRONE_FROM = 14


def injury_prone(player: Player) -> bool:
    return player.attributes["injury_proneness"] >= INJURY_PRONE_FROM


def injured_on(player: Player, day: date) -> bool:
    return player.injured_until is not None and player.injured_until >= day


def absence(player: Player, day: date) -> str | None:
    if injured_on(player, day) and player.injured_until is not None:
        what = player.injury or "injured"
        return f"{player.name}: {what}, back {player.injured_until.isoformat()}"
    return None


def possible_ban(player: Player) -> str | None:
    if not player.banned_from:
        return None
    return f"{player.name}: may be banned from {', '.join(player.banned_from)}"
