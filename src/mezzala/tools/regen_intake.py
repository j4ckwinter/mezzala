from dataclasses import dataclass

from mezzala.core.players import Player, Snapshot, is_same_person
from mezzala.core.summary import PlayerSummary, summarize

REGEN_MAX_AGE = 17
CLUBS_SHOWN = 10


@dataclass(frozen=True)
class ClubRegens:
    club: str
    new_regens: int
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


def clubs_producing(regens: list[Player]) -> list[ClubRegens]:
    by_club: dict[str, list[Player]] = {}
    for player in regens:
        if player.club_name is not None:
            by_club.setdefault(player.club_name, []).append(player)
    clubs = [
        ClubRegens(club, len(found), best.potential_ability, best.name)
        for club, found in by_club.items()
        if (best := max(found, key=lambda player: player.potential_ability))
    ]
    clubs.sort(key=lambda club: (club.best_potential, club.new_regens), reverse=True)
    return clubs[:CLUBS_SHOWN]


def regen_intake(
    current: Snapshot, baseline: Snapshot | None, min_potential: int, unsigned_only: bool, limit: int
) -> RegenIntake:
    if baseline is None:
        return RegenIntake(None, NO_BASELINE, 0, [], [])
    before = baseline.by_uid()
    new = [
        player
        for player in current.players
        if player.age <= REGEN_MAX_AGE and not (player.uid in before and is_same_person(before[player.uid], player))
    ]
    new.sort(key=lambda player: (player.potential_ability, player.current_ability), reverse=True)
    shown = [
        summarize(player)
        for player in new
        if player.potential_ability >= min_potential and (not unsigned_only or is_unsigned(player))
    ][:limit]
    explanation = f"Players aged {REGEN_MAX_AGE} or under who were not in the save on {baseline.game_date.isoformat()}."
    return RegenIntake(baseline.game_date.isoformat(), explanation, len(new), shown, clubs_producing(new))
