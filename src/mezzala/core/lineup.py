from collections.abc import Mapping
from dataclasses import dataclass
from statistics import median

from mezzala.core.assignment import BLOCKED, min_cost_assignment
from mezzala.core.formations import STARTERS, Formation
from mezzala.core.players import Player
from mezzala.core.positions import Fit, PositionGroup, fit

ACCOMPLISHED_PENALTY = 5


def ability_in(player: Player, group: PositionGroup) -> float | None:
    match fit(player, group):
        case Fit.NATURAL:
            return player.current_ability
        case Fit.ACCOMPLISHED:
            return player.current_ability - ACCOMPLISHED_PENALTY
        case Fit.OUT_OF_POSITION:
            return None


FILLED_PLACE_BONUS = 1_000


def place_cost(player: Player, group: PositionGroup) -> float:
    ability = ability_in(player, group)
    return BLOCKED if ability is None else -(FILLED_PLACE_BONUS + ability)


def assign_starters(squad: list[Player], places: Mapping[PositionGroup, int]) -> dict[PositionGroup, list[Player]]:
    slots = [group for group, needed in places.items() for _ in range(needed)]
    empty_options = [0.0] * len(slots)
    cost = [[place_cost(player, group) for player in squad] + empty_options for group in slots]
    assigned: dict[PositionGroup, list[Player]] = {group: [] for group in places}
    for group, row, column in zip(slots, cost, min_cost_assignment(cost), strict=True):
        if row[column] != BLOCKED and column < len(squad):
            assigned[group].append(squad[column])
    for starters in assigned.values():
        starters.sort(key=lambda player: player.current_ability, reverse=True)
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

    def average_ability(self) -> float:
        if not self.places:
            return 0.0
        return round(sum(player.current_ability for player in self.starters) / len(self.places), 1)

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


def weakest_starters(squad: list[Player], formation: Formation) -> dict[PositionGroup, Player | None]:
    lineup = pick_lineup(squad, formation)
    weakest: dict[PositionGroup, Player | None] = {}
    for group, needed in STARTERS[formation].items():
        starters = lineup.at(group)
        weakest[group] = starters[-1] if len(starters) == needed else None
    return weakest


@dataclass(frozen=True)
class StarterEntry:
    position: str
    name: str | None
    age: int | None
    current_ability: int | None
    fit: str | None


def starter_entries(lineup: Lineup) -> list[StarterEntry]:
    entries: list[StarterEntry] = []
    for place in lineup.places:
        player = place.player
        if player is None:
            entries.append(StarterEntry(place.group.value, None, None, None, None))
        else:
            entries.append(
                StarterEntry(place.group.value, player.name, player.age, player.current_ability,
                             fit(player, place.group).value)
            )  # fmt: skip
    return entries


def backup_lineup(squad: list[Player], formation: Formation) -> Lineup:
    starters = {player.uid for player in pick_lineup(squad, formation).starters}
    return pick_lineup([player for player in squad if player.uid not in starters], formation)
