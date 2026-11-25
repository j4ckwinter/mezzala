from dataclasses import dataclass

from mezzala.core.money import format_money
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers, primary_group
from mezzala.core.profile import profile_similarity, strongest_attributes
from mezzala.core.reach import within_reach
from mezzala.core.squad import is_outside_club, leaves_within
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View, ability_text, potential_text, rating
from mezzala.core.wages import describe_wage, wage_guide

ABILITY_SHORTFALL_ALLOWED = 5
GROWS_INTO_IT_MAX_AGE = 21
ABILITY_SCORE_FLOOR_BELOW_TARGET = 10
ABILITY_SCORE_SPAN = 20
SIMILARITY_WEIGHT = 0.6
ABILITY_WEIGHT = 0.4
CHEAP_CONTRACT_MONTHS = 12
SHOWN_STRENGTHS = 4


@dataclass(frozen=True)
class Limits:
    max_fee: int | None
    max_age: int | None
    max_wage: int | None
    within_reach: bool


@dataclass(frozen=True)
class Candidate:
    player: PlayerSummary
    score: float
    profile_similarity: float
    reasons: list[str]
    expected_wage: str


@dataclass(frozen=True)
class Replacements:
    target: PlayerSummary
    position: str
    max_fee: str
    candidates: list[Candidate]


def can_step_in(target: Player, candidate: Player) -> bool:
    if candidate.current_ability >= target.current_ability - ABILITY_SHORTFALL_ALLOWED:
        return True
    return candidate.age <= GROWS_INTO_IT_MAX_AGE and candidate.potential_ability >= target.current_ability


def affordable(candidate: Player, snapshot: Snapshot, limits: Limits) -> bool:
    if limits.within_reach and not within_reach(candidate, snapshot):
        return False
    if limits.max_age is not None and candidate.age > limits.max_age:
        return False
    if limits.max_wage is not None and candidate.wage is not None and candidate.wage > limits.max_wage:
        return False
    if candidate.costs_no_fee or limits.max_fee is None:
        return True
    return candidate.value is not None and candidate.value <= limits.max_fee


def ability_score(target: Player, candidate: Player) -> float:
    floor = target.current_ability - ABILITY_SCORE_FLOOR_BELOW_TARGET
    return min(max((candidate.current_ability - floor) / ABILITY_SCORE_SPAN, 0.0), 1.0)


def reasons(snapshot: Snapshot, target: Player, candidate: Player, similarity: float, view: View) -> list[str]:
    found = [
        f"profile {similarity:.0%} similar, strongest in {', '.join(strongest_attributes(candidate, SHOWN_STRENGTHS))}",
        f"{ability_text(view, candidate.current_ability)} against {target.name}'s "
        f"{rating(view, target.current_ability)}, {potential_text(view, candidate.potential_ability)}",
    ]
    if candidate.is_free_agent:
        found.append("free agent, no fee")
    else:
        found.append(f"transfer value {format_money(candidate.value)}")
    leaving = leaves_within(candidate, snapshot.club_uid, snapshot.game_date, CHEAP_CONTRACT_MONTHS)
    if leaving is not None and not candidate.is_free_agent:
        found.append(f"contract ends {leaving.isoformat()}, so cheaper now or free on a pre-contract")
    if candidate.current_ability < target.current_ability - ABILITY_SHORTFALL_ALLOWED:
        found.append(
            f"not there yet at {candidate.age}, but {potential_text(view, candidate.potential_ability)} covers it"
        )
    return found


def find_replacements(
    snapshot: Snapshot, target: Player, limits: Limits, limit: int, view: View, group: PositionGroup | None = None
) -> Replacements:
    position = group or primary_group(target)
    ranked: list[Candidate] = []
    wages = wage_guide(snapshot)
    for candidate in snapshot.players:
        if candidate.uid == target.uid or not is_outside_club(candidate, snapshot.club_uid):
            continue
        if not covers(candidate, position):
            continue
        if not can_step_in(target, candidate) or not affordable(candidate, snapshot, limits):
            continue
        similarity = profile_similarity(target, candidate)
        score = SIMILARITY_WEIGHT * similarity + ABILITY_WEIGHT * ability_score(target, candidate)
        ranked.append(
            Candidate(summarize(candidate, view), round(score, 3), round(similarity, 3),
                      reasons(snapshot, target, candidate, similarity, view),
                      describe_wage(wages.expected(candidate)))
        )  # fmt: skip
    ranked.sort(key=lambda candidate: candidate.score, reverse=True)
    fee_cap = "no limit" if limits.max_fee is None else format_money(limits.max_fee)
    return Replacements(summarize(target, view), position.value, fee_cap, ranked[:limit])
