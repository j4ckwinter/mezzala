from dataclasses import dataclass

from mezzala.formations import PLAYERS_PER_STARTING_PLACE, STARTERS, Formation
from mezzala.lineup import StarterEntry, pick_lineup, starter_entries
from mezzala.players import Player, Snapshot
from mezzala.positions import PositionGroup, fit
from mezzala.squad import available_squad, depth_chart, leaves_within

AGEING_OUTFIELD_AGE = 30
AGEING_GOALKEEPER_AGE = 32
SUCCESSOR_MAX_AGE = 23
LOOKAHEAD_SEASONS = 2
LEAVING_WITHIN_MONTHS = 12
WEAK_STARTER_MARGIN = 8


@dataclass(frozen=True)
class DepthEntry:
    name: str
    age: int
    current_ability: int
    potential_ability: int
    fit: str
    starts_here: bool


@dataclass(frozen=True)
class PositionReport:
    group: str
    starters_needed: int
    depth_target: int
    depth: list[DepthEntry]
    issues: list[str]


@dataclass(frozen=True)
class SquadGaps:
    formation: str
    starting_eleven_median_ability: float
    eleven: list[StarterEntry]
    positions: list[PositionReport]


def ageing_age(group: PositionGroup) -> int:
    return AGEING_GOALKEEPER_AGE if group is PositionGroup.GOALKEEPER else AGEING_OUTFIELD_AGE


def depth_entry(player: Player, group: PositionGroup, starters: list[Player]) -> DepthEntry:
    return DepthEntry(
        player.name, player.age, player.current_ability, player.potential_ability, fit(player, group).value,
        player in starters,
    )  # fmt: skip


def group_issues(
    snapshot: Snapshot,
    group: PositionGroup,
    chart: list[Player],
    starters: list[Player],
    needed: int,
    eleven_median: float,
) -> list[str]:
    issues: list[str] = []
    target = needed * PLAYERS_PER_STARTING_PLACE
    if len(chart) < target:
        issues.append(f"thin: {len(chart)} of {target} players who can play here")
    if len(starters) < needed:
        issues.append(f"empty: {needed - len(starters)} of {needed} starting places with nobody to fill them")
        return issues
    for starter in starters:
        if starter.age + LOOKAHEAD_SEASONS >= ageing_age(group):
            issues.append(f"ageing: {starter.name} is {starter.age}, {starter.age + LOOKAHEAD_SEASONS} in two seasons")
        leaving = leaves_within(starter, snapshot.club_uid, snapshot.game_date, LEAVING_WITHIN_MONTHS)
        if leaving is not None:
            how = "loan ends" if starter.on_loan else "contract ends"
            issues.append(f"leaving: {starter.name}'s {how} {leaving.isoformat()}")
    weakest = min(starters, key=lambda player: player.current_ability)
    if weakest.current_ability < eleven_median - WEAK_STARTER_MARGIN:
        issues.append(
            f"weak: {weakest.name} (CA {weakest.current_ability}) starts here, "
            f"well below the XI median of {eleven_median:g}"
        )
    successors = [
        player
        for player in chart
        if player not in starters
        and player.age <= SUCCESSOR_MAX_AGE
        and player.potential_ability >= weakest.current_ability
    ]
    if not successors:
        issues.append(f"no successor: nobody {SUCCESSOR_MAX_AGE} or under can reach {weakest.name}'s level")
    return issues


def squad_gaps(snapshot: Snapshot, formation: Formation) -> SquadGaps:
    squad = available_squad(snapshot)
    lineup = pick_lineup(squad, formation)
    eleven_median = lineup.median_ability()
    positions: list[PositionReport] = []
    for group, needed in STARTERS[formation].items():
        chart = depth_chart(squad, group)
        starters = lineup.at(group)
        issues = group_issues(snapshot, group, chart, starters, needed, eleven_median)
        depth = [depth_entry(player, group, starters) for player in chart]
        positions.append(PositionReport(group.value, needed, needed * PLAYERS_PER_STARTING_PLACE, depth, issues))
    positions.sort(key=lambda position: len(position.issues), reverse=True)
    return SquadGaps(formation.value, eleven_median, starter_entries(lineup), positions)
