from enum import StrEnum

ABILITY_PER_STAR = 40
STAR_STEPS = 2
CHANGE_DECIMALS = 1

type Rating = int | str
type Measure = float | str


class View(StrEnum):
    FULL = "full"
    SPOILER_FREE = "spoiler-free"


def stars(ability: float) -> str:
    count = round(ability / ABILITY_PER_STAR * STAR_STEPS) / STAR_STEPS
    shown = f"{count:g}"
    return f"{shown} star" if count == 1 else f"{shown} stars"


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
    return f"{change / ABILITY_PER_STAR:+.{CHANGE_DECIMALS}f} stars"


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
