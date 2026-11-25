from collections.abc import Callable
from dataclasses import dataclass

from mezzala.core.availability import absence, possible_ban
from mezzala.core.formations import Shape
from mezzala.core.lineup import pick_lineup
from mezzala.core.players import Player, Snapshot
from mezzala.core.squad import available_squad
from mezzala.core.view import View, shows_hidden_information

INJURY_PRONE_FROM = 14
RECENT_INJURIES_FOR_RISK = 2
LOW_CONDITION_BELOW = 90
LOW_SHARPNESS_BELOW = 70


@dataclass(frozen=True)
class FitnessEntry:
    name: str
    detail: str


@dataclass(frozen=True)
class FitnessReport:
    formation: str
    explanation: str
    unavailable: list[str]
    possible_bans: list[str]
    injury_risks_in_the_eleven: list[FitnessEntry]
    low_condition: list[FitnessEntry]
    low_match_sharpness: list[FitnessEntry]


CONDITION_NOTE = (
    f"Condition below {LOW_CONDITION_BELOW}% raises the chance of injury; match sharpness below "
    f"{LOW_SHARPNESS_BELOW}% means a player needs games. "
)
RISK_FROM_HISTORY = f"{RECENT_INJURIES_FOR_RISK} or more injuries in the save's last two years"
BAN_NOTE = (
    " The save keeps bans the game has stopped showing and does not name their competitions, so bans are only "
    "possible: check them in the game."
)


def explanation(view: View) -> str:
    who = (
        f"prone to injury or have had {RISK_FROM_HISTORY}"
        if shows_hidden_information(view)
        else f"have had {RISK_FROM_HISTORY}"
    )
    return f"{CONDITION_NOTE}Injury risks are starters in the best eleven who {who}.{BAN_NOTE}"


def injury_risk(player: Player, view: View) -> str | None:
    reasons: list[str] = []
    if shows_hidden_information(view) and player.attributes["injury_proneness"] >= INJURY_PRONE_FROM:
        reasons.append("prone to injury")
    if len(player.injuries) >= RECENT_INJURIES_FOR_RISK:
        reasons.append(f"{len(player.injuries)} injuries in the last two years")
    return ", ".join(reasons) or None


def below(players: list[Player], measure: Callable[[Player], int | None], limit: int) -> list[FitnessEntry]:
    found = [(value, player) for player in players if (value := measure(player)) is not None and value < limit]
    return [FitnessEntry(player.name, f"{value}%") for value, player in sorted(found, key=lambda item: item[0])]


def fitness(snapshot: Snapshot, shape: Shape, view: View) -> FitnessReport:
    squad = available_squad(snapshot)
    starters = pick_lineup(squad, shape).starters
    risks = [FitnessEntry(player.name, risk) for player in starters if (risk := injury_risk(player, view)) is not None]
    return FitnessReport(
        shape.name,
        explanation(view),
        [missing for player in squad if (missing := absence(player, snapshot.game_date)) is not None],
        [ban for player in squad if (ban := possible_ban(player)) is not None],
        risks,
        below(squad, lambda player: player.condition, LOW_CONDITION_BELOW),
        below(squad, lambda player: player.match_sharpness, LOW_SHARPNESS_BELOW),
    )
