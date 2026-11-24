from dataclasses import dataclass
from statistics import median

from mezzala.formations import PLAYERS_PER_STARTING_PLACE, STARTERS, Formation
from mezzala.lineup import assign_starters
from mezzala.players import Player, Snapshot
from mezzala.positions import PositionGroup
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


@dataclass(frozen=True)
class PositionGap:
    group: str
    starters_needed: int
    depth_target: int
    depth: list[DepthEntry]
    issues: list[str]


@dataclass(frozen=True)
class SquadGaps:
    formation: str
    starting_eleven_median_ability: float
    gaps: list[PositionGap]
    covered: list[str]


def ageing_age(group: PositionGroup) -> int:
    return AGEING_GOALKEEPER_AGE if group is PositionGroup.GOALKEEPER else AGEING_OUTFIELD_AGE


def depth_entry(player: Player) -> DepthEntry:
    return DepthEntry(player.name, player.age, player.current_ability, player.potential_ability)


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
        return issues
    for starter in starters:
        if starter.age + LOOKAHEAD_SEASONS >= ageing_age(group):
            issues.append(f"ageing: {starter.name} is {starter.age}, {starter.age + LOOKAHEAD_SEASONS} in two seasons")
        leaving = leaves_within(starter, snapshot.club_uid, snapshot.game_date, LEAVING_WITHIN_MONTHS)
        if leaving is not None:
            how = "loan ends" if starter.on_loan else "contract ends"
            issues.append(f"leaving: {starter.name}'s {how} {leaving.isoformat()}")
    weakest = starters[-1]
    if weakest.current_ability < eleven_median - WEAK_STARTER_MARGIN:
        issues.append(f"weak: {weakest.name} (CA {weakest.current_ability}) is well below the XI median")
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
    starters = STARTERS[formation]
    assigned = assign_starters(squad, starters)
    eleven = [player for group_starters in assigned.values() for player in group_starters]
    eleven_median = median(player.current_ability for player in eleven) if eleven else 0.0
    gaps: list[PositionGap] = []
    covered: list[str] = []
    for group, needed in starters.items():
        chart = depth_chart(squad, group)
        issues = group_issues(snapshot, group, chart, assigned[group], needed, eleven_median)
        if not issues:
            covered.append(group.value)
            continue
        entry = PositionGap(
            group.value, needed, needed * PLAYERS_PER_STARTING_PLACE, [depth_entry(p) for p in chart], issues
        )
        gaps.append(entry)
    gaps.sort(key=lambda gap: len(gap.issues), reverse=True)
    return SquadGaps(formation.value, eleven_median, gaps, covered)
