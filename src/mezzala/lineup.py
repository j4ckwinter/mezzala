from collections.abc import Mapping

from mezzala.players import Player
from mezzala.positions import PositionGroup, primary_group
from mezzala.squad import depth_chart


def assign_starters(squad: list[Player], places: Mapping[PositionGroup, int]) -> dict[PositionGroup, list[Player]]:
    assigned: dict[PositionGroup, list[Player]] = {group: [] for group in places}
    used: set[int] = set()
    by_ability = sorted(squad, key=lambda player: player.current_ability, reverse=True)
    for player in by_ability:
        group = primary_group(player)
        if group in assigned and len(assigned[group]) < places[group]:
            assigned[group].append(player)
            used.add(player.uid)
    for group, needed in places.items():
        for player in depth_chart(squad, group):
            if len(assigned[group]) >= needed:
                break
            if player.uid not in used:
                assigned[group].append(player)
                used.add(player.uid)
        assigned[group].sort(key=lambda player: player.current_ability, reverse=True)
    return assigned
