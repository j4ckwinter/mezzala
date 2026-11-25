from dataclasses import dataclass
from datetime import date

from mezzala.core.players import Injury, Player, SeasonStats, Snapshot, is_same_person
from mezzala.core.positions import PositionGroup, covers, fit
from mezzala.core.profile import (
    HIDDEN_ATTRIBUTES,
    MENTAL_ATTRIBUTES,
    PHYSICAL_ATTRIBUTES,
    attribute_label,
    first_group,
    personality,
    position_score,
    visible_profile,
)
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View, ability_text, rating, shows_hidden_information

ATTRIBUTE_CHANGE_MIN = 1


@dataclass(frozen=True)
class PositionFit:
    position: str
    fit: str
    key_attribute_score: float


@dataclass(frozen=True)
class Fitness:
    condition_percent: int | None
    match_sharpness_percent: int | None
    injury: str | None
    injured_until: str | None
    banned_from: list[str]
    injuries_in_the_last_two_years: list[str]


@dataclass(frozen=True)
class Profile:
    player: PlayerSummary
    left_foot: int | None
    right_foot: int | None
    height_cm: int | None
    attributes: dict[str, dict[str, int]]
    hidden_attributes: dict[str, int] | None
    personality: dict[str, int] | None
    traits: list[str]
    positions: list[PositionFit]
    fitness: Fitness
    season: SeasonStats | None
    changes_since_first_snapshot: list[str]


@dataclass(frozen=True)
class PlayerProfiles:
    compared_with: str | None
    explanation: str
    profiles: list[Profile]


EXPLANATION = (
    "Attributes run from 1 to 20. Traits are the ones fmsave can name; some players have others it cannot. "
    "Season stats cover all competitions this season, so they are empty before a player has played. Injuries "
    "come from the save's record of about the last two years."
)
SPOILER_FREE_NOTE = " Fog of war is on, so hidden attributes and personality numbers are left out."


def labelled(player: Player, names: tuple[str, ...]) -> dict[str, int]:
    return {attribute_label(name): player.attributes[name] for name in names}


def grouped_attributes(player: Player) -> dict[str, dict[str, int]]:
    first, names = first_group(player)
    return {
        first: labelled(player, names),
        "mental": labelled(player, MENTAL_ATTRIBUTES),
        "physical": labelled(player, PHYSICAL_ATTRIBUTES),
    }


def position_fits(player: Player) -> list[PositionFit]:
    fits = [
        PositionFit(group.value, fit(player, group).value, position_score(player, group))
        for group in PositionGroup
        if covers(player, group)
    ]
    return sorted(fits, key=lambda found: found.key_attribute_score, reverse=True)


def injury_line(injury: Injury) -> str:
    details = ", ".join(detail for detail in (injury.severity, injury.cause) if detail)
    return f"{injury.day.isoformat()}: {details}" if details else injury.day.isoformat()


def fitness(player: Player) -> Fitness:
    return Fitness(
        player.condition,
        player.match_sharpness,
        player.injury,
        player.injured_until.isoformat() if player.injured_until else None,
        list(player.banned_from),
        [injury_line(injury) for injury in player.injuries],
    )


def changes(earlier: Player | None, player: Player, view: View) -> list[str]:
    if earlier is None or not is_same_person(earlier, player):
        return []
    found: list[str] = []
    if earlier.current_ability != player.current_ability:
        found.append(f"{ability_text(view, earlier.current_ability)} -> {rating(view, player.current_ability)}")
    for name in visible_profile(player):
        before, now = earlier.attributes[name], player.attributes[name]
        if abs(now - before) >= ATTRIBUTE_CHANGE_MIN:
            found.append(f"{attribute_label(name)} {before} -> {now}")
    return found


def profile(player: Player, earlier: Player | None, view: View) -> Profile:
    hidden = shows_hidden_information(view)
    return Profile(
        player=summarize(player, view),
        left_foot=player.left_foot,
        right_foot=player.right_foot,
        height_cm=player.height_cm,
        attributes=grouped_attributes(player),
        hidden_attributes=labelled(player, HIDDEN_ATTRIBUTES) if hidden else None,
        personality=personality(player) if hidden else None,
        traits=list(player.traits),
        positions=position_fits(player),
        fitness=fitness(player),
        season=player.season,
        changes_since_first_snapshot=changes(earlier, player, view),
    )


def player_profiles(players: list[Player], first: Snapshot | None, view: View) -> PlayerProfiles:
    earlier = first.by_uid() if first is not None else {}
    compared: date | None = first.game_date if first is not None else None
    note = EXPLANATION if shows_hidden_information(view) else EXPLANATION + SPOILER_FREE_NOTE
    return PlayerProfiles(
        compared.isoformat() if compared else None,
        note,
        [profile(player, earlier.get(player.uid), view) for player in players],
    )
