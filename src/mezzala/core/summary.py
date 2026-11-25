from dataclasses import dataclass

from mezzala.core.feet import preferred_foot, weak_foot
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.nationality import nationality_label
from mezzala.core.players import Player
from mezzala.core.positions import NATURAL_POSITION_RATING
from mezzala.core.view import Rating, View, rating


@dataclass(frozen=True)
class PlayerSummary:
    name: str
    age: int
    club: str
    nationality: str
    positions: str
    preferred_foot: str | None
    weak_foot: int | None
    current_ability: Rating
    potential_ability: Rating
    value: str
    wage: str
    wage_while_on_loan: str
    contract_end: str


def natural_positions(player: Player) -> str:
    codes = [code.upper() for code, rating in player.position_ratings.items() if rating >= NATURAL_POSITION_RATING]
    return ", ".join(codes)


def club_label(player: Player) -> str:
    if player.club_name is None:
        return "free agent"
    if player.on_loan:
        return f"{player.club_name} (on loan)"
    return player.club_name


def summarize(player: Player, view: View) -> PlayerSummary:
    return PlayerSummary(
        name=player.name,
        age=player.age,
        club=club_label(player),
        nationality=nationality_label(player),
        positions=natural_positions(player),
        preferred_foot=foot.value if (foot := preferred_foot(player)) else None,
        weak_foot=weak_foot(player),
        current_ability=rating(view, player.current_ability),
        potential_ability=rating(view, player.potential_ability),
        value=format_money(player.value),
        wage=format_weekly_wage(player.wage),
        wage_while_on_loan=format_weekly_wage(player.loan_wage) if player.on_loan else "not on loan",
        contract_end=player.contract_end.isoformat() if player.contract_end else "none",
    )
