from statistics import correlation

from mezzala.players import Player
from mezzala.positions import is_goalkeeper

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


def strongest_attributes(player: Player, count: int) -> tuple[str, ...]:
    names = visible_profile(player)
    return tuple(sorted(names, key=lambda name: player.attributes[name], reverse=True)[:count])
