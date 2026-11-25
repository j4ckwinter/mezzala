from enum import StrEnum
from math import floor

ABILITY_PER_STAR = 40
STAR_STEPS = 2
FEWEST_STARS = 0.5

type Rating = int | str
type Measure = float | str


class View(StrEnum):
    FULL = "full"
    SPOILER_FREE = "spoiler-free"


def star_count(ability: float) -> float:
    return floor(ability / ABILITY_PER_STAR * STAR_STEPS + 0.5) / STAR_STEPS


def stars(ability: float) -> str:
    count = max(star_count(ability), FEWEST_STARS)
    return f"{count:g} star" if count == 1 else f"{count:g} stars"


def rating(view: View, ability: int) -> Rating:
    match view:
        case View.FULL:
            return ability
        case View.SPOILER_FREE:
            return stars(ability)


def measure(view: View, ability: float) -> Measure:
    match view:
        case View.FULL:
            return float(ability)
        case View.SPOILER_FREE:
            return stars(ability)


def star_change(change: float) -> str:
    count = floor(abs(change) / ABILITY_PER_STAR * STAR_STEPS + 0.5) / STAR_STEPS
    sign = "-" if change < 0 and count else "+"
    return f"{sign}{count:g} stars"


def rating_change(view: View, change: int) -> Rating:
    match view:
        case View.FULL:
            return change
        case View.SPOILER_FREE:
            return star_change(change)


def measure_change(view: View, change: float) -> Measure:
    match view:
        case View.FULL:
            return float(change)
        case View.SPOILER_FREE:
            return star_change(change)


def ability_text(view: View, ability: float) -> str:
    match view:
        case View.FULL:
            return f"CA {ability:g}"
        case View.SPOILER_FREE:
            return stars(ability)


def potential_text(view: View, potential: float) -> str:
    match view:
        case View.FULL:
            return f"PA {potential:g}"
        case View.SPOILER_FREE:
            return f"potential {stars(potential)}"


def amount_text(view: View, change: float, decimals: int) -> str:
    match view:
        case View.FULL:
            return f"{change:.{decimals}f}"
        case View.SPOILER_FREE:
            return star_change(change)


def gain_text(view: View, change: float, decimals: int) -> str:
    match view:
        case View.FULL:
            return f"{change:.{decimals}f} CA"
        case View.SPOILER_FREE:
            return amount_text(view, change, decimals)


def signed_amount_text(view: View, change: float, decimals: int) -> str:
    match view:
        case View.FULL:
            return f"{change:+.{decimals}f}"
        case View.SPOILER_FREE:
            return amount_text(view, change, decimals)


def rating_text(view: View, ability: float) -> str:
    match view:
        case View.FULL:
            return f"{ability:g}"
        case View.SPOILER_FREE:
            return stars(ability)


def shows_hidden_information(view: View) -> bool:
    match view:
        case View.FULL:
            return True
        case View.SPOILER_FREE:
            return False


def ability_moved(view: View, before: int, after: int) -> bool:
    match view:
        case View.FULL:
            return before != after
        case View.SPOILER_FREE:
            return star_count(before) != star_count(after)
