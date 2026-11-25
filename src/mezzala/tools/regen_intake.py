from dataclasses import dataclass

from mezzala.core.players import Snapshot, is_same_person
from mezzala.core.summary import PlayerSummary, summarize

REGEN_MAX_AGE = 17


@dataclass(frozen=True)
class RegenIntake:
    compared_with: str | None
    explanation: str
    total_new: int
    regens: list[PlayerSummary]


NO_BASELINE = (
    "This is the first snapshot of the save, so it becomes the baseline. Regens arrive at youth intakes; "
    "ask again after one and every new player since this date will show up."
)


def regen_intake(current: Snapshot, baseline: Snapshot | None, min_potential: int, limit: int) -> RegenIntake:
    if baseline is None:
        return RegenIntake(None, NO_BASELINE, 0, [])
    before = baseline.by_uid()
    new = [
        player
        for player in current.players
        if player.age <= REGEN_MAX_AGE and not (player.uid in before and is_same_person(before[player.uid], player))
    ]
    new.sort(key=lambda player: (player.potential_ability, player.current_ability), reverse=True)
    shown = [summarize(player) for player in new if player.potential_ability >= min_potential][:limit]
    explanation = f"Players aged {REGEN_MAX_AGE} or under who were not in the save on {baseline.game_date.isoformat()}."
    return RegenIntake(baseline.game_date.isoformat(), explanation, len(new), shown)
