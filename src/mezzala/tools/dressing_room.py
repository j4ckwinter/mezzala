from dataclasses import dataclass

from mezzala.core.players import Player, Snapshot
from mezzala.core.squad import available_squad, leaves_within, squad_level

CAPTAIN_MIN_AGE = 23
CAPTAIN_CONTRACT_MONTHS = 12
CAPTAINS_SHOWN = 3
NEUTRAL_PERSONALITY = 10
LEADERSHIP_WEIGHT = 2
STRONG_FROM = 15
WEAK_BELOW = 8
VOLATILE_FROM = 15
HOTHEAD_BELOW = 6
AMBITIOUS_FROM = 16
DISLOYAL_BELOW = 8


@dataclass(frozen=True)
class SquadMember:
    name: str
    age: int
    why: list[str]


@dataclass(frozen=True)
class DressingRoom:
    explanation: str
    captain_candidates: list[SquadMember]
    concerns: list[SquadMember]


EXPLANATION = (
    "Captains are ranked on leadership (counted twice), determination, professionalism, temperament and handling "
    f"pressure, from players aged {CAPTAIN_MIN_AGE} or over who are not leaving within {CAPTAIN_CONTRACT_MONTHS} "
    "months. Concerns are players whose personality tends to unsettle a squad or who may push to leave."
)


def known(value: int | None) -> int:
    return NEUTRAL_PERSONALITY if value is None else value


def captaincy(player: Player) -> int:
    return (
        LEADERSHIP_WEIGHT * player.attributes["leadership"]
        + player.attributes["determination"]
        + player.professionalism
        + known(player.temperament)
        + known(player.pressure)
    )


def strengths(player: Player) -> list[str]:
    found = [f"leadership {player.attributes['leadership']}", f"determination {player.attributes['determination']}"]
    if player.professionalism >= STRONG_FROM:
        found.append("very professional")
    if known(player.temperament) >= STRONG_FROM:
        found.append("keeps his head")
    if known(player.pressure) >= STRONG_FROM:
        found.append("handles pressure well")
    return found


def could_captain(player: Player, snapshot: Snapshot) -> bool:
    staying = leaves_within(player, snapshot.club_uid, snapshot.game_date, CAPTAIN_CONTRACT_MONTHS) is None
    return player.age >= CAPTAIN_MIN_AGE and not player.on_loan and staying


def concerns(player: Player, level: float) -> list[str]:
    found: list[str] = []
    if known(player.controversy) >= VOLATILE_FROM:
        found.append("likely to speak out and stir up trouble")
    if known(player.temperament) < HOTHEAD_BELOW:
        found.append("loses his temper")
    if player.professionalism < WEAK_BELOW:
        found.append("unprofessional")
    if player.ambition >= AMBITIOUS_FROM and known(player.loyalty) < DISLOYAL_BELOW and player.current_ability >= level:
        found.append("ambitious, not loyal, and good enough to push for a bigger club")
    return found


def dressing_room(snapshot: Snapshot) -> DressingRoom:
    squad = available_squad(snapshot)
    candidates = sorted((p for p in squad if could_captain(p, snapshot)), key=captaincy, reverse=True)
    level = squad_level(snapshot)
    worries = [SquadMember(p.name, p.age, found) for p in squad if (found := concerns(p, level))]
    return DressingRoom(
        EXPLANATION,
        [SquadMember(p.name, p.age, strengths(p)) for p in candidates[:CAPTAINS_SHOWN]],
        sorted(worries, key=lambda member: len(member.why), reverse=True),
    )
