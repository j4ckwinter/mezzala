from dataclasses import dataclass

from mezzala.core.formations import Formation
from mezzala.core.growth import projected_growth
from mezzala.core.lineup import backup_lineup, pick_lineup, weakest_starters
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers
from mezzala.core.squad import YOUNG_PLAYER_MAX_AGE, available_squad, owned_players, plays_for_club, squad_level
from mezzala.core.view import Measure, Rating, View, measure_change, rating, rating_change

READY_MARGIN = 3
LOAN_MIN_AGE = 17
LOAN_MIN_HEADROOM = 10
FOCUS_LIMIT = 5


@dataclass(frozen=True)
class YoungPlayer:
    name: str
    age: int
    current_ability: Rating
    potential_ability: Rating
    best_position: str | None
    gap_to_first_team: Rating | None
    projected_gain_next_season: Measure


@dataclass(frozen=True)
class DevelopmentPlan:
    formation: str
    ready_for_first_team: list[YoungPlayer]
    loan_out: list[YoungPlayer]
    already_on_loan: list[YoungPlayer]
    focus: list[YoungPlayer]


def closest_place(player: Player, bars: dict[PositionGroup, Player | None]) -> tuple[PositionGroup, int] | None:
    gaps = [
        (group, player.current_ability - bar.current_ability)
        for group, bar in bars.items()
        if bar is not None and covers(player, group)
    ]
    return max(gaps, key=lambda gap: gap[1], default=None)


def young_player(player: Player, bars: dict[PositionGroup, Player | None], view: View) -> YoungPlayer:
    place = closest_place(player, bars)
    return YoungPlayer(
        player.name, player.age, rating(view, player.current_ability), rating(view, player.potential_ability),
        place[0].value if place else None, rating_change(view, place[1]) if place else None,
        measure_change(view, projected_growth(player).ability_gain),
    )  # fmt: skip


def development_plan(snapshot: Snapshot, formation: Formation, view: View) -> DevelopmentPlan:
    squad = available_squad(snapshot)
    starters = {player.uid for player in pick_lineup(squad, formation).starters}
    backups = {player.uid for player in backup_lineup(squad, formation).starters}
    bars = weakest_starters(squad, formation)
    youngsters = [player for player in owned_players(snapshot) if player.age <= YOUNG_PLAYER_MAX_AGE]
    ready: list[YoungPlayer] = []
    loan_out: list[YoungPlayer] = []
    on_loan: list[YoungPlayer] = []
    for player in sorted(youngsters, key=lambda p: p.current_ability, reverse=True):
        entry = young_player(player, bars, view)
        place = closest_place(player, bars)
        if not plays_for_club(player, snapshot.club_uid):
            on_loan.append(entry)
        elif player.uid in starters:
            continue
        elif place is not None and place[1] >= -READY_MARGIN:
            ready.append(entry)
        elif player.uid not in backups and player.age >= LOAN_MIN_AGE and player.headroom >= LOAN_MIN_HEADROOM:
            loan_out.append(entry)
    level = squad_level(snapshot)
    focus = sorted(
        (player for player in youngsters if player.potential_ability >= level),
        key=lambda player: (player.potential_ability, projected_growth(player).ability_gain),
        reverse=True,
    )
    shown = [young_player(player, bars, view) for player in focus[:FOCUS_LIMIT]]
    return DevelopmentPlan(formation.value, ready, loan_out, on_loan, shown)
