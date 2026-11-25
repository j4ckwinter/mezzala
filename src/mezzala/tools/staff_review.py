from dataclasses import dataclass

from mezzala.core.players import Snapshot, StaffMember

COACHING_JOBS = frozenset(
    {"coach", "assistant manager", "goalkeeping coach", "fitness coach", "set piece coach", "manager"}
)
SCOUTING_JOBS = frozenset({"scout", "chief scout", "recruitment analyst", "director of football"})
MEDICAL_JOBS = frozenset(
    {"physio", "head physio", "doctor", "chief doctor", "sports scientist", "head of sports science"}
)
COACHING_AREAS = (
    "attacking", "defending", "fitness", "goalkeeping", "possession", "tactical", "technical", "set_pieces",
    "working_with_youngsters",
)  # fmt: skip
SCOUTING_AREAS = ("judging_player_ability", "judging_player_potential")
MEDICAL_AREAS = ("physiotherapy", "sports_science")
WEAK_BELOW = 12


@dataclass(frozen=True)
class AreaRating:
    area: str
    best: int | None
    by: str | None


@dataclass(frozen=True)
class StaffEntry:
    name: str
    job: str
    age: int | None


@dataclass(frozen=True)
class StaffReview:
    explanation: str
    coaching: list[AreaRating]
    scouting: list[AreaRating]
    medical: list[AreaRating]
    weak_coaching_areas: list[str]
    staff: list[StaffEntry]


EXPLANATION = (
    "Ratings are out of 20. Each area shows the best rating anyone in that part of the staff has, since that is "
    f"who you would put in charge of it. Coaching areas with nobody at {WEAK_BELOW} or above are worth a hire."
)


def area_label(area: str) -> str:
    return area.replace("_", " ")


def best_in(staff: list[StaffMember], area: str) -> AreaRating:
    rated = [member for member in staff if area in member.ratings]
    best = max(rated, key=lambda member: member.ratings[area], default=None)
    if best is None:
        return AreaRating(area_label(area), None, None)
    return AreaRating(area_label(area), best.ratings[area], best.name)


def ratings_for(staff: tuple[StaffMember, ...], jobs: frozenset[str], areas: tuple[str, ...]) -> list[AreaRating]:
    chosen = [member for member in staff if member.job in jobs]
    return [best_in(chosen, area) for area in areas]


def staff_review(snapshot: Snapshot) -> StaffReview:
    coaching = ratings_for(snapshot.staff, COACHING_JOBS, COACHING_AREAS)
    return StaffReview(
        EXPLANATION,
        coaching,
        ratings_for(snapshot.staff, SCOUTING_JOBS, SCOUTING_AREAS),
        ratings_for(snapshot.staff, MEDICAL_JOBS, MEDICAL_AREAS),
        [rating.area for rating in coaching if rating.best is None or rating.best < WEAK_BELOW],
        [StaffEntry(member.name, member.job, member.age) for member in snapshot.staff],
    )
