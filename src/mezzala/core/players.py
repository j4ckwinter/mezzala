from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

ATTRIBUTE_NAMES: tuple[str, ...] = (
    "crossing", "dribbling", "finishing", "heading", "long_shots", "marking", "off_the_ball", "passing",
    "penalty_taking", "tackling", "vision", "handling", "aerial_reach", "command_of_area", "communication",
    "kicking", "throwing", "anticipation", "decisions", "one_on_ones", "positioning", "reflexes",
    "first_touch", "technique", "flair", "corners", "teamwork", "work_rate", "long_throws", "eccentricity",
    "rushing_out", "punching", "acceleration", "free_kick_taking", "strength", "stamina", "pace",
    "jumping_reach", "leadership", "dirtiness", "balance", "bravery", "consistency", "aggression", "agility",
    "important_matches", "injury_proneness", "versatility", "natural_fitness", "determination", "composure",
    "concentration",
)  # fmt: skip

POSITION_CODES: tuple[str, ...] = (
    "gk", "sw", "dl", "dc", "dr", "wbl", "wbr", "dm", "ml", "mc", "mr", "aml", "amc", "amr", "stc",
)  # fmt: skip


class ReleaseScope(StrEnum):
    ANY = "any"
    DOMESTIC = "domestic"
    FOREIGN = "foreign"


@dataclass(frozen=True)
class ReleaseClause:
    scope: ReleaseScope
    fee: int
    expires: date | None


@dataclass(frozen=True)
class Player:
    uid: int
    name: str
    age: int
    birth_date: date | None
    club_uid: int | None
    club_name: str | None
    position_ratings: Mapping[str, int]
    current_ability: int
    potential_ability: int
    value: int | None
    wage: int | None
    contract_end: date | None
    on_loan: bool
    loan_parent_club_uid: int | None
    loan_end: date | None
    attributes: Mapping[str, int]
    reputation: int
    professionalism: int
    ambition: int
    first_team: bool | None
    club_reputation: int | None
    club_nation_id: int | None
    league_id: int | None
    youth_contract: bool | None
    release_clauses: tuple[ReleaseClause, ...]
    loan_wage: int | None

    @property
    def headroom(self) -> int:
        return max(self.potential_ability - self.current_ability, 0)

    @property
    def is_free_agent(self) -> bool:
        return self.club_uid is None

    @property
    def costs_no_fee(self) -> bool:
        return self.is_free_agent or self.value == 0


@dataclass(frozen=True)
class Budget:
    transfer_remaining: int | None
    wage_budget_weekly: int | None
    wage_payroll_weekly: int | None

    @property
    def wage_headroom_weekly(self) -> int | None:
        if self.wage_budget_weekly is None or self.wage_payroll_weekly is None:
            return None
        return self.wage_budget_weekly - self.wage_payroll_weekly


@dataclass(frozen=True)
class Vacancy:
    club_uid: int
    club_name: str
    club_reputation: int | None
    advertised: date | None
    balance: int | None
    transfer_budget: int | None


@dataclass(frozen=True)
class Snapshot:
    game_date: date
    club_uid: int
    club_name: str
    club_reputation: int
    club_nation_id: int | None
    budget: Budget
    players: tuple[Player, ...]
    vacancies: tuple[Vacancy, ...]

    def by_uid(self) -> dict[int, Player]:
        return {player.uid: player for player in self.players}


@dataclass(frozen=True)
class WatchedPlayer:
    uid: int
    birth_date: date | None
    name: str
    added_on: date
    value: int | None
    current_ability: int
    club_name: str | None
    note: str


@dataclass(frozen=True)
class PastPlayers:
    game_date: date
    by_uid: Mapping[int, Player]


def is_same_person(earlier: Player, later: Player) -> bool:
    return earlier.uid == later.uid and earlier.birth_date == later.birth_date
