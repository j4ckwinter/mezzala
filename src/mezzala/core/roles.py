from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.feet import Foot, preferred_foot
from mezzala.core.lookup import folded
from mezzala.core.players import Player

KEY_WEIGHT = 2
PREFERABLE_WEIGHT = 1
FOOT_ADJUSTMENT = 1.0
SCORE_DECIMALS = 1


class Side(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class FootPreference(StrEnum):
    SAME_SIDE = "same side"
    OPPOSITE_SIDE = "opposite side"
    ANY = "any"


@dataclass(frozen=True)
class Role:
    name: str
    short: str
    key: tuple[str, ...]
    preferable: tuple[str, ...]
    foot: FootPreference = FootPreference.ANY


SAME, OPPOSITE = FootPreference.SAME_SIDE, FootPreference.OPPOSITE_SIDE

ROLES: tuple[Role, ...] = (
    Role(
        "goalkeeper",
        "gk",
        (
            "aerial_reach",
            "command_of_area",
            "communication",
            "handling",
            "kicking",
            "concentration",
            "positioning",
            "reflexes",
            "agility",
        ),
        ("one_on_ones", "throwing", "anticipation", "decisions"),
    ),
    Role(
        "sweeper keeper",
        "sk",
        (
            "command_of_area",
            "kicking",
            "one_on_ones",
            "reflexes",
            "rushing_out",
            "anticipation",
            "composure",
            "concentration",
            "positioning",
            "agility",
        ),
        ("aerial_reach", "first_touch", "handling", "passing", "throwing", "decisions", "vision", "acceleration"),
    ),
    Role(
        "centre-back",
        "cd",
        ("heading", "marking", "tackling", "positioning", "jumping_reach", "strength"),
        ("aggression", "anticipation", "bravery", "composure", "concentration", "decisions", "pace"),
    ),
    Role(
        "ball-playing centre-back",
        "bpd",
        ("heading", "marking", "passing", "tackling", "composure", "positioning", "jumping_reach", "strength"),
        ("first_touch", "technique", "vision", "anticipation", "bravery", "concentration", "decisions", "pace"),
    ),
    Role(
        "stopper",
        "sto",
        ("heading", "tackling", "aggression", "bravery", "decisions", "jumping_reach", "strength"),
        ("marking", "anticipation", "concentration", "positioning"),
    ),
    Role(
        "covering centre-back",
        "cov",
        ("marking", "tackling", "anticipation", "concentration", "decisions", "positioning", "pace"),
        ("heading", "bravery", "composure", "acceleration", "jumping_reach", "strength"),
    ),
    Role(
        "no-nonsense centre-back",
        "ncb",
        ("heading", "marking", "tackling", "positioning", "jumping_reach", "strength"),
        ("aggression", "anticipation", "bravery", "concentration"),
    ),
    Role(
        "wide centre-back",
        "wcb",
        ("heading", "marking", "tackling", "positioning", "jumping_reach", "strength"),
        ("crossing", "dribbling", "passing", "technique", "off_the_ball", "stamina", "work_rate", "pace"),
        SAME,
    ),
    Role(
        "overlapping centre-back",
        "ocb",
        ("heading", "marking", "tackling", "positioning", "jumping_reach", "strength", "stamina", "work_rate"),
        ("crossing", "dribbling", "passing", "off_the_ball", "pace", "acceleration"),
        SAME,
    ),
    Role(
        "libero",
        "lib",
        (
            "first_touch",
            "heading",
            "marking",
            "passing",
            "tackling",
            "technique",
            "composure",
            "decisions",
            "positioning",
            "jumping_reach",
            "strength",
        ),
        ("anticipation", "bravery", "concentration", "vision", "pace", "stamina"),
    ),
    Role(
        "full-back",
        "fb",
        ("marking", "tackling", "anticipation", "concentration", "positioning", "teamwork"),
        ("crossing", "passing", "decisions", "work_rate", "stamina", "pace"),
        SAME,
    ),
    Role(
        "wing-back",
        "wb",
        ("crossing", "dribbling", "tackling", "off_the_ball", "teamwork", "work_rate", "acceleration", "stamina"),
        (
            "first_touch",
            "marking",
            "passing",
            "technique",
            "anticipation",
            "decisions",
            "positioning",
            "agility",
            "balance",
            "pace",
        ),
        SAME,
    ),
    Role(
        "complete wing-back",
        "cwb",
        (
            "crossing",
            "dribbling",
            "technique",
            "flair",
            "off_the_ball",
            "teamwork",
            "work_rate",
            "acceleration",
            "stamina",
        ),
        ("first_touch", "passing", "tackling", "anticipation", "decisions", "agility", "balance", "pace"),
        SAME,
    ),
    Role(
        "inverted wing-back",
        "iwb",
        ("passing", "tackling", "anticipation", "decisions", "positioning", "teamwork", "composure"),
        ("first_touch", "marking", "technique", "vision", "work_rate", "acceleration", "stamina"),
        OPPOSITE,
    ),
    Role(
        "no-nonsense full-back",
        "nfb",
        ("marking", "tackling", "positioning", "strength"),
        ("heading", "aggression", "anticipation", "bravery", "teamwork"),
    ),
    Role(
        "defensive midfielder",
        "dm",
        ("tackling", "anticipation", "concentration", "positioning", "teamwork"),
        (
            "first_touch",
            "marking",
            "passing",
            "aggression",
            "composure",
            "decisions",
            "work_rate",
            "stamina",
            "strength",
        ),
    ),
    Role(
        "anchor",
        "a",
        ("marking", "tackling", "anticipation", "concentration", "decisions", "positioning"),
        ("composure", "teamwork", "strength"),
    ),
    Role(
        "half-back",
        "hb",
        ("marking", "tackling", "anticipation", "composure", "concentration", "decisions", "positioning", "teamwork"),
        ("first_touch", "passing", "aggression", "bravery", "work_rate", "jumping_reach", "stamina", "strength"),
    ),
    Role(
        "deep-lying playmaker",
        "dlp",
        ("first_touch", "passing", "technique", "composure", "decisions", "teamwork", "vision"),
        ("anticipation", "positioning", "balance"),
    ),
    Role(
        "ball-winning midfielder",
        "bwm",
        ("tackling", "aggression", "anticipation", "teamwork", "work_rate", "stamina"),
        ("marking", "bravery", "concentration", "positioning", "agility", "pace", "strength"),
    ),
    Role(
        "regista",
        "reg",
        (
            "first_touch",
            "passing",
            "technique",
            "composure",
            "decisions",
            "flair",
            "off_the_ball",
            "teamwork",
            "vision",
        ),
        ("dribbling", "long_shots", "anticipation", "balance"),
    ),
    Role(
        "segundo volante",
        "vol",
        ("marking", "passing", "tackling", "off_the_ball", "positioning", "work_rate", "pace", "stamina"),
        (
            "finishing",
            "first_touch",
            "long_shots",
            "anticipation",
            "composure",
            "decisions",
            "acceleration",
            "balance",
            "strength",
        ),
    ),
    Role(
        "roaming playmaker",
        "rpm",
        (
            "first_touch",
            "passing",
            "technique",
            "anticipation",
            "composure",
            "decisions",
            "off_the_ball",
            "teamwork",
            "vision",
            "work_rate",
            "acceleration",
            "stamina",
        ),
        ("dribbling", "long_shots", "concentration", "flair", "agility", "balance", "pace"),
    ),
    Role(
        "central midfielder",
        "cm",
        ("first_touch", "passing", "tackling", "decisions", "teamwork"),
        ("technique", "anticipation", "composure", "concentration", "off_the_ball", "vision", "work_rate", "stamina"),
    ),
    Role(
        "box-to-box midfielder",
        "b2b",
        ("passing", "tackling", "off_the_ball", "teamwork", "work_rate", "stamina"),
        (
            "dribbling",
            "finishing",
            "first_touch",
            "long_shots",
            "technique",
            "aggression",
            "anticipation",
            "composure",
            "decisions",
            "positioning",
            "acceleration",
            "balance",
            "pace",
            "strength",
        ),
    ),
    Role(
        "mezzala",
        "mez",
        ("passing", "technique", "decisions", "off_the_ball", "work_rate", "acceleration"),
        (
            "dribbling",
            "first_touch",
            "long_shots",
            "vision",
            "anticipation",
            "composure",
            "flair",
            "balance",
            "stamina",
        ),
    ),
    Role(
        "carrilero",
        "car",
        ("first_touch", "passing", "tackling", "decisions", "positioning", "teamwork", "stamina"),
        ("technique", "anticipation", "composure", "concentration", "off_the_ball", "vision", "work_rate"),
    ),
    Role(
        "advanced playmaker",
        "ap",
        ("first_touch", "passing", "technique", "composure", "decisions", "off_the_ball", "teamwork", "vision"),
        ("dribbling", "anticipation", "flair", "agility"),
    ),
    Role(
        "wide midfielder",
        "wm",
        ("passing", "tackling", "decisions", "teamwork", "work_rate"),
        ("crossing", "first_touch", "technique", "concentration", "off_the_ball", "positioning", "vision", "stamina"),
        SAME,
    ),
    Role(
        "winger",
        "w",
        ("crossing", "dribbling", "technique", "acceleration", "agility"),
        ("first_touch", "passing", "off_the_ball", "flair", "balance", "pace", "stamina", "work_rate"),
        SAME,
    ),
    Role(
        "defensive winger",
        "dw",
        ("technique", "anticipation", "off_the_ball", "positioning", "teamwork", "work_rate", "stamina"),
        (
            "crossing",
            "dribbling",
            "first_touch",
            "marking",
            "tackling",
            "aggression",
            "concentration",
            "decisions",
            "acceleration",
        ),
        SAME,
    ),
    Role(
        "wide playmaker",
        "wp",
        ("first_touch", "passing", "technique", "composure", "decisions", "teamwork", "vision"),
        ("dribbling", "anticipation", "flair", "off_the_ball", "agility"),
        OPPOSITE,
    ),
    Role(
        "inverted winger",
        "iw",
        ("crossing", "dribbling", "passing", "technique", "acceleration", "agility"),
        (
            "first_touch",
            "long_shots",
            "composure",
            "decisions",
            "flair",
            "off_the_ball",
            "vision",
            "balance",
            "pace",
            "stamina",
            "work_rate",
        ),
        OPPOSITE,
    ),
    Role(
        "inside forward",
        "if",
        ("dribbling", "finishing", "first_touch", "technique", "off_the_ball", "acceleration", "agility"),
        ("long_shots", "passing", "anticipation", "composure", "flair", "balance", "pace", "stamina", "work_rate"),
        OPPOSITE,
    ),
    Role(
        "raumdeuter",
        "rmd",
        ("finishing", "anticipation", "composure", "concentration", "decisions", "off_the_ball", "balance"),
        ("first_touch", "technique", "acceleration", "stamina"),
    ),
    Role(
        "wide target forward",
        "wtf",
        ("heading", "bravery", "teamwork", "jumping_reach", "strength"),
        ("crossing", "first_touch", "anticipation", "off_the_ball", "balance", "stamina", "work_rate"),
    ),
    Role(
        "attacking midfielder",
        "am",
        ("first_touch", "long_shots", "passing", "technique", "anticipation", "decisions", "flair", "off_the_ball"),
        ("dribbling", "finishing", "composure", "vision", "agility"),
    ),
    Role(
        "shadow striker",
        "ss",
        ("dribbling", "finishing", "first_touch", "anticipation", "composure", "off_the_ball", "acceleration"),
        ("passing", "technique", "concentration", "decisions", "work_rate", "agility", "balance", "pace", "stamina"),
    ),
    Role(
        "trequartista",
        "t",
        (
            "dribbling",
            "first_touch",
            "passing",
            "technique",
            "composure",
            "decisions",
            "flair",
            "off_the_ball",
            "vision",
            "acceleration",
        ),
        ("finishing", "anticipation", "agility", "balance"),
    ),
    Role(
        "enganche",
        "eng",
        ("first_touch", "passing", "technique", "composure", "decisions", "vision"),
        ("dribbling", "anticipation", "flair", "off_the_ball", "teamwork", "agility"),
    ),
    Role(
        "advanced forward",
        "af",
        ("dribbling", "finishing", "first_touch", "technique", "composure", "off_the_ball", "acceleration"),
        ("passing", "anticipation", "decisions", "work_rate", "agility", "balance", "pace", "stamina"),
    ),
    Role(
        "poacher",
        "p",
        ("finishing", "anticipation", "composure", "off_the_ball"),
        ("first_touch", "heading", "technique", "decisions", "acceleration"),
    ),
    Role(
        "target forward",
        "tf",
        ("heading", "bravery", "composure", "off_the_ball", "balance", "jumping_reach", "strength"),
        ("finishing", "first_touch", "aggression", "anticipation", "decisions", "teamwork"),
    ),
    Role(
        "complete forward",
        "cf",
        (
            "dribbling",
            "finishing",
            "first_touch",
            "heading",
            "long_shots",
            "passing",
            "technique",
            "anticipation",
            "composure",
            "decisions",
            "off_the_ball",
            "vision",
            "acceleration",
            "agility",
            "strength",
        ),
        ("teamwork", "work_rate", "balance", "jumping_reach", "pace", "stamina"),
    ),
    Role(
        "deep-lying forward",
        "dlf",
        ("first_touch", "passing", "technique", "composure", "decisions", "off_the_ball", "teamwork"),
        ("finishing", "anticipation", "flair", "vision", "balance", "strength"),
    ),
    Role(
        "pressing forward",
        "pf",
        ("aggression", "anticipation", "bravery", "decisions", "teamwork", "work_rate", "acceleration", "stamina"),
        ("finishing", "first_touch", "composure", "concentration", "agility", "balance", "pace", "strength"),
    ),
    Role(
        "false nine",
        "f9",
        (
            "dribbling",
            "first_touch",
            "passing",
            "technique",
            "composure",
            "decisions",
            "off_the_ball",
            "vision",
            "acceleration",
            "agility",
        ),
        ("finishing", "anticipation", "flair", "teamwork", "balance"),
    ),
    Role(
        "channel forward",
        "chf",
        ("finishing", "off_the_ball", "work_rate", "acceleration", "pace", "stamina"),
        ("dribbling", "first_touch", "anticipation", "composure", "decisions"),
    ),
)


class UnknownRole(LookupError):
    pass


def words(text: str) -> str:
    return " ".join(folded(text).replace("-", " ").replace("_", " ").split())


ROLE_NAMES = {words(role.name): role for role in ROLES} | {words(role.short): role for role in ROLES}
ROLE_ALIASES = {
    "ball playing defender": "ball-playing centre-back", "central defender": "centre-back",
    "cover": "covering centre-back", "inverted full back": "inverted wing-back", "target man": "target forward",
    "ball playing goalkeeper": "sweeper keeper", "box to box": "box-to-box midfielder",
}  # fmt: skip


def find_role(text: str) -> Role:
    wanted = words(text)
    found = ROLE_NAMES.get(wanted) or ROLE_NAMES.get(words(ROLE_ALIASES.get(wanted, "")))
    if found is None:
        raise UnknownRole(f"'{text}' is not a role mezzala knows. Roles: {', '.join(role.name for role in ROLES)}.")
    return found


def foot_adjustment(player: Player, role: Role, side: Side | None) -> float:
    foot = preferred_foot(player)
    if side is None or foot is None or foot is Foot.EITHER or role.foot is FootPreference.ANY:
        return 0.0
    same_side = foot.value == side.value
    wanted_same = role.foot is FootPreference.SAME_SIDE
    return FOOT_ADJUSTMENT if same_side == wanted_same else -FOOT_ADJUSTMENT


def attribute_fit(player: Player, role: Role) -> float:
    total = KEY_WEIGHT * sum(player.attributes[name] for name in role.key)
    total += PREFERABLE_WEIGHT * sum(player.attributes[name] for name in role.preferable)
    return total / (KEY_WEIGHT * len(role.key) + PREFERABLE_WEIGHT * len(role.preferable))


def role_score(player: Player, role: Role, side: Side | None) -> float:
    return round(attribute_fit(player, role) + foot_adjustment(player, role, side), SCORE_DECIMALS)
