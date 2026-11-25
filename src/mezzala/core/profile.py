from statistics import correlation

from mezzala.core.players import Player
from mezzala.core.positions import PositionGroup, is_goalkeeper

TECHNICAL_ATTRIBUTES = (
    "corners", "crossing", "dribbling", "finishing", "first_touch", "free_kick_taking", "heading",
    "long_shots", "long_throws", "marking", "passing", "penalty_taking", "tackling", "technique",
)  # fmt: skip
GOALKEEPING_ATTRIBUTES = (
    "aerial_reach", "command_of_area", "communication", "eccentricity", "first_touch", "handling", "kicking",
    "one_on_ones", "passing", "punching", "reflexes", "rushing_out", "throwing",
)  # fmt: skip
MENTAL_ATTRIBUTES = (
    "aggression", "anticipation", "bravery", "composure", "concentration", "decisions", "determination",
    "flair", "leadership", "off_the_ball", "positioning", "teamwork", "vision", "work_rate",
)  # fmt: skip
PHYSICAL_ATTRIBUTES = (
    "acceleration", "agility", "balance", "jumping_reach", "natural_fitness", "pace", "stamina", "strength",
)  # fmt: skip

OUTFIELD_PROFILE = TECHNICAL_ATTRIBUTES + MENTAL_ATTRIBUTES + PHYSICAL_ATTRIBUTES
GOALKEEPER_PROFILE = GOALKEEPING_ATTRIBUTES + MENTAL_ATTRIBUTES + PHYSICAL_ATTRIBUTES


def visible_profile(player: Player) -> tuple[str, ...]:
    return GOALKEEPER_PROFILE if is_goalkeeper(player) else OUTFIELD_PROFILE


def profile_similarity(target: Player, candidate: Player) -> float:
    names = visible_profile(target)
    target_values = [target.attributes[name] for name in names]
    candidate_values = [candidate.attributes[name] for name in names]
    if len(set(target_values)) < 2 or len(set(candidate_values)) < 2:
        return 0.0
    return (correlation(target_values, candidate_values) + 1) / 2


def attribute_label(name: str) -> str:
    return name.replace("_", " ")


def strongest_attributes(player: Player, count: int) -> tuple[str, ...]:
    names = sorted(visible_profile(player), key=lambda name: player.attributes[name], reverse=True)
    return tuple(attribute_label(name) for name in names[:count])


KEY_ATTRIBUTES: dict[PositionGroup, tuple[str, ...]] = {
    PositionGroup.GOALKEEPER: (
        "handling", "reflexes", "one_on_ones", "aerial_reach", "command_of_area", "positioning", "concentration",
        "agility",
    ),
    PositionGroup.CENTRE_BACK: (
        "marking", "tackling", "heading", "positioning", "jumping_reach", "strength", "anticipation", "concentration",
    ),
    PositionGroup.LEFT_BACK: (
        "tackling", "marking", "crossing", "pace", "acceleration", "stamina", "work_rate", "positioning",
    ),
    PositionGroup.RIGHT_BACK: (
        "tackling", "marking", "crossing", "pace", "acceleration", "stamina", "work_rate", "positioning",
    ),
    PositionGroup.DEFENSIVE_MIDFIELD: (
        "tackling", "positioning", "anticipation", "passing", "decisions", "teamwork", "work_rate", "concentration",
    ),
    PositionGroup.CENTRAL_MIDFIELD: (
        "passing", "first_touch", "vision", "decisions", "teamwork", "stamina", "work_rate", "technique",
    ),
    PositionGroup.ATTACKING_MIDFIELD: (
        "passing", "vision", "first_touch", "technique", "flair", "off_the_ball", "decisions", "dribbling",
    ),
    PositionGroup.LEFT_WING: (
        "crossing", "dribbling", "pace", "acceleration", "technique", "flair", "off_the_ball", "agility",
    ),
    PositionGroup.RIGHT_WING: (
        "crossing", "dribbling", "pace", "acceleration", "technique", "flair", "off_the_ball", "agility",
    ),
    PositionGroup.STRIKER: (
        "finishing", "off_the_ball", "composure", "first_touch", "anticipation", "pace", "acceleration", "heading",
    ),
}  # fmt: skip


def position_score(player: Player, group: PositionGroup) -> float:
    names = KEY_ATTRIBUTES[group]
    return round(sum(player.attributes[name] for name in names) / len(names), 1)


ATTRIBUTE_GROUPS: dict[str, tuple[str, ...]] = {
    "pace": ("pace", "acceleration"),
    "physical": ("strength", "stamina", "natural_fitness", "balance"),
    "aerial": ("heading", "jumping_reach"),
    "defending": ("tackling", "marking", "positioning", "anticipation"),
    "passing": ("passing", "vision", "first_touch", "technique"),
    "creativity": ("vision", "flair", "dribbling", "off_the_ball"),
    "finishing": ("finishing", "composure", "long_shots"),
    "work rate": ("work_rate", "teamwork", "determination", "bravery"),
}


def group_score(player: Player, names: tuple[str, ...]) -> float:
    return sum(player.attributes[name] for name in names) / len(names)


def outfield_profile(players: list[Player]) -> dict[str, float]:
    outfield = [player for player in players if not is_goalkeeper(player)]
    if not outfield:
        return {}
    return {
        group: round(sum(group_score(player, names) for player in outfield) / len(outfield), 1)
        for group, names in ATTRIBUTE_GROUPS.items()
    }
