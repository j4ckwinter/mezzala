from dataclasses import dataclass

from mezzala.money import format_money
from mezzala.players import Player, Snapshot
from mezzala.positions import PositionGroup, covers, primary_group
from mezzala.profile import profile_similarity, strongest_attributes
from mezzala.reach import within_reach
from mezzala.squad import is_outside_club, leaves_within
from mezzala.summary import PlayerSummary, summarize

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
    if candidate.is_free_agent or limits.max_fee is None:
        return True
    return candidate.value is not None and candidate.value <= limits.max_fee


def ability_score(target: Player, candidate: Player) -> float:
    floor = target.current_ability - ABILITY_SCORE_FLOOR_BELOW_TARGET
    return min(max((candidate.current_ability - floor) / ABILITY_SCORE_SPAN, 0.0), 1.0)


def reasons(snapshot: Snapshot, target: Player, candidate: Player, similarity: float) -> list[str]:
    found = [
        f"profile {similarity:.0%} similar, strongest in {', '.join(strongest_attributes(candidate, SHOWN_STRENGTHS))}",
        f"CA {candidate.current_ability} against {target.name}'s {target.current_ability}, "
        f"PA {candidate.potential_ability}",
    ]
    if candidate.is_free_agent:
        found.append("free agent, no fee")
    else:
        found.append(f"transfer value {format_money(candidate.value)}")
    leaving = leaves_within(candidate, snapshot.club_uid, snapshot.game_date, CHEAP_CONTRACT_MONTHS)
    if leaving is not None and not candidate.is_free_agent:
        found.append(f"contract ends {leaving.isoformat()}, so cheaper now or free on a pre-contract")
    if candidate.current_ability < target.current_ability - ABILITY_SHORTFALL_ALLOWED:
        found.append(f"not there yet at {candidate.age}, but PA {candidate.potential_ability} covers it")
    return found


def find_replacements(
    snapshot: Snapshot, target: Player, limits: Limits, limit: int, group: PositionGroup | None = None
) -> Replacements:
    position = group or primary_group(target)
    ranked: list[Candidate] = []
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
            Candidate(summarize(candidate), round(score, 3), round(similarity, 3),
                      reasons(snapshot, target, candidate, similarity))
        )  # fmt: skip
    ranked.sort(key=lambda candidate: candidate.score, reverse=True)
    fee_cap = "no limit" if limits.max_fee is None else format_money(limits.max_fee)
    return Replacements(summarize(target), position.value, fee_cap, ranked[:limit])
