from collections.abc import Mapping
from dataclasses import dataclass
from statistics import median

from mezzala.formations import STARTERS, Formation
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


@dataclass(frozen=True)
class Place:
    group: PositionGroup
    player: Player | None


@dataclass(frozen=True)
class Lineup:
    formation: Formation
    places: tuple[Place, ...]

    @property
    def starters(self) -> list[Player]:
        return [place.player for place in self.places if place.player is not None]

    def at(self, group: PositionGroup) -> list[Player]:
        return [place.player for place in self.places if place.group is group and place.player is not None]

    def median_ability(self) -> float:
        starters = self.starters
        return median(player.current_ability for player in starters) if starters else 0.0


def pick_lineup(squad: list[Player], formation: Formation) -> Lineup:
    places = STARTERS[formation]
    assigned = assign_starters(squad, places)
    chosen: list[Place] = []
    for group, needed in places.items():
        starters: list[Player | None] = [*assigned[group]]
        starters += [None] * (needed - len(starters))
        chosen.extend(Place(group, player) for player in starters)
    return Lineup(formation, tuple(chosen))
