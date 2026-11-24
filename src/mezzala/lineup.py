from collections.abc import Mapping
from dataclasses import dataclass
from statistics import median

from mezzala.formations import STARTERS, Formation
from mezzala.players import Player
from mezzala.positions import Fit, PositionGroup, fit

ACCOMPLISHED_PENALTY = 5


def ability_in(player: Player, group: PositionGroup) -> float | None:
    match fit(player, group):
        case Fit.NATURAL:
            return player.current_ability
        case Fit.ACCOMPLISHED:
            return player.current_ability - ACCOMPLISHED_PENALTY
        case Fit.OUT_OF_POSITION:
            return None


def assign_starters(squad: list[Player], places: Mapping[PositionGroup, int]) -> dict[PositionGroup, list[Player]]:
    options = [
        (ability, player.current_ability, player.uid, group, player)
        for player in squad
        for group in places
        if (ability := ability_in(player, group)) is not None
    ]
    options.sort(key=lambda option: option[:3], reverse=True)
    assigned: dict[PositionGroup, list[Player]] = {group: [] for group in places}
    used: set[int] = set()
    for _, _, uid, group, player in options:
        if uid in used or len(assigned[group]) >= places[group]:
            continue
        assigned[group].append(player)
        used.add(uid)
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
