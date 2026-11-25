from mezzala.core.players import Player

WORK_PERMIT_FREE_NATIONS = frozenset({"England", "Scotland", "Wales", "Northern Ireland", "Republic of Ireland"})
UNKNOWN_NATIONALITY = "unknown"


def nationality_label(player: Player) -> str:
    return ", ".join(player.nationalities) or UNKNOWN_NATIONALITY


def needs_no_work_permit(player: Player) -> bool:
    return any(nation in WORK_PERMIT_FREE_NATIONS for nation in player.nationalities)


def holds_nationality(player: Player, nation: str) -> bool:
    wanted = nation.strip().casefold()
    return any(held.casefold() == wanted for held in player.nationalities)
