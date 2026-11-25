from dataclasses import dataclass
from datetime import date

from mezzala.core.players import Player, Snapshot, is_same_person
from mezzala.core.summary import PlayerSummary, summarize

REGEN_MAX_AGE = 17
CLUBS_SHOWN = 10


@dataclass(frozen=True)
class ClubRegens:
    club: str
    promising_regens: int
    best_potential: int
    best: str


@dataclass(frozen=True)
class RegenIntake:
    compared_with: str | None
    explanation: str
    total_new: int
    regens: list[PlayerSummary]
    by_club: list[ClubRegens]


NO_BASELINE = (
    "This is the first snapshot of the save, so it becomes the baseline. Regens arrive at youth intakes; "
    "ask again after one and every new player since this date will show up."
)


def is_unsigned(player: Player) -> bool:
    return player.is_free_agent or player.youth_contract is True


def clubs_producing(regens: list[Player], min_potential: int) -> list[ClubRegens]:
    by_club: dict[str, list[Player]] = {}
    for player in regens:
        if player.club_name is not None and player.potential_ability >= min_potential:
            by_club.setdefault(player.club_name, []).append(player)
    clubs = [
        ClubRegens(club, len(found), best.potential_ability, best.name)
        for club, found in by_club.items()
        if (best := max(found, key=lambda player: player.potential_ability))
    ]
    clubs.sort(key=lambda club: (club.promising_regens, club.best_potential), reverse=True)
    return clubs[:CLUBS_SHOWN]


def was_youth_at(player: Player, day: date) -> bool:
    if player.birth_date is None:
        return player.age <= REGEN_MAX_AGE
    adult_year = day.year - REGEN_MAX_AGE - 1
    try:
        youngest_adult_birthday = day.replace(year=adult_year)
    except ValueError:
        youngest_adult_birthday = date(adult_year, 2, 28)
    return player.birth_date > youngest_adult_birthday


def regen_intake(
    current: Snapshot, baseline: Snapshot | None, min_potential: int, unsigned_only: bool, limit: int
) -> RegenIntake:
    if baseline is None:
        return RegenIntake(None, NO_BASELINE, 0, [], [])
    before = baseline.by_uid()
    new = [
        player
        for player in current.players
        if was_youth_at(player, baseline.game_date)
        and not (player.uid in before and is_same_person(before[player.uid], player))
    ]
    new.sort(key=lambda player: (player.potential_ability, player.current_ability), reverse=True)
    shown = [
        summarize(player)
        for player in new
        if player.potential_ability >= min_potential and (not unsigned_only or is_unsigned(player))
    ][:limit]
    explanation = (
        f"Players who were {REGEN_MAX_AGE} or under on {baseline.game_date.isoformat()} and were not in the save then. "
        f"Clubs are ranked by how many of them with potential of at least {min_potential} they hold now (the save "
        "does not record where a player came through)."
    )
    return RegenIntake(
        baseline.game_date.isoformat(), explanation, len(new), shown, clubs_producing(new, min_potential)
    )
