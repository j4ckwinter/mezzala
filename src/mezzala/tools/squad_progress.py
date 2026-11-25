from dataclasses import dataclass

from mezzala.core.formations import Shape
from mezzala.core.lineup import pick_lineup
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Snapshot, is_same_person
from mezzala.core.squad import available_squad, everyone_paid, owned_players, wage_paid_by_club
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import Rating, View, rating_change, rating_text
from mezzala.tools.league_comparison import league_comparison

MOST_IMPROVED_SHOWN = 5


@dataclass(frozen=True)
class Measure:
    measure: str
    then: str
    now: str


@dataclass(frozen=True)
class Improver:
    player: PlayerSummary
    ability_change: Rating


@dataclass(frozen=True)
class SquadProgress:
    compared_with: str | None
    explanation: str
    measures: list[Measure]
    most_improved: list[Improver]


FIRST_SNAPSHOT_ONLY = (
    "This is the first snapshot of the save, so it is the starting point. Ask again after saving later in the game."
)


def rank_label(snapshot: Snapshot, shape: Shape) -> str:
    comparison = league_comparison(snapshot, shape, View.FULL)
    if comparison.your_rank is None:
        return "unknown"
    return f"{comparison.your_rank} of {len(comparison.clubs)}"


def measures(snapshot: Snapshot, shape: Shape, view: View) -> dict[str, str]:
    squad = available_squad(snapshot)
    owned = owned_players(snapshot)
    ages = [player.age for player in squad]
    wages = sum(wage_paid_by_club(player, snapshot.club_uid) or 0 for player in everyone_paid(snapshot))
    return {
        "best eleven average CA": rating_text(view, pick_lineup(squad, shape).average_ability()),
        "league rank by best eleven": rank_label(snapshot, shape),
        "players available": str(len(squad)),
        "average age": f"{sum(ages) / len(ages):.1f}" if ages else "unknown",
        "value of the club's players": format_money(sum(player.value or 0 for player in owned)),
        "weekly wage bill": format_weekly_wage(wages),
    }


def squad_progress(current: Snapshot, first: Snapshot | None, shape: Shape, view: View) -> SquadProgress:
    if first is None:
        return SquadProgress(None, FIRST_SNAPSHOT_ONLY, [], [])
    if first.club_uid != current.club_uid:
        moved = (
            f"You managed {first.club_name} in the first snapshot and {current.club_name} now, "
            "so there is no squad to compare."
        )
        return SquadProgress(first.game_date.isoformat(), moved, [], [])
    then = measures(first, shape, view)
    now = measures(current, shape, view)
    earlier = first.by_uid()
    gains = [
        (player.current_ability - before.current_ability, player)
        for player in owned_players(current)
        if (before := earlier.get(player.uid)) is not None and is_same_person(before, player)
        and player.current_ability > before.current_ability
    ]  # fmt: skip
    gains.sort(key=lambda gain: gain[0], reverse=True)
    improvers = [Improver(summarize(player, view), rating_change(view, gain)) for gain, player in gains]
    return SquadProgress(
        first.game_date.isoformat(),
        f"The squad on {current.game_date.isoformat()} against the first snapshot, {first.game_date.isoformat()}.",
        [Measure(name, then[name], now[name]) for name in now],
        improvers[:MOST_IMPROVED_SHOWN],
    )
