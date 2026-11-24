from dataclasses import dataclass

from mezzala.money import format_money, format_weekly_wage
from mezzala.players import Player
from mezzala.positions import NATURAL_POSITION_RATING


@dataclass(frozen=True)
class PlayerSummary:
    name: str
    age: int
    club: str
    positions: str
    current_ability: int
    potential_ability: int
    value: str
    wage: str
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


def summarize(player: Player) -> PlayerSummary:
    return PlayerSummary(
        name=player.name,
        age=player.age,
        club=club_label(player),
        positions=natural_positions(player),
        current_ability=player.current_ability,
        potential_ability=player.potential_ability,
        value=format_money(player.value),
        wage=format_weekly_wage(player.wage),
        contract_end=player.contract_end.isoformat() if player.contract_end else "none",
    )
