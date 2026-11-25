from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.formations import PLAYERS_PER_STARTING_PLACE, STARTERS, Formation
from mezzala.core.lineup import StarterEntry, pick_lineup, starter_entries
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, fit
from mezzala.core.squad import available_squad, depth_chart, leaves_within
from mezzala.core.view import Measure, Rating, View, ability_text, measure, rating, rating_text

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
    current_ability: Rating
    potential_ability: Rating
    fit: str
    starts_here: bool


class IssueKind(StrEnum):
    THIN = "thin"
    EMPTY = "empty"
    AGEING = "ageing"
    LEAVING = "leaving"
    WEAK = "weak"
    NO_SUCCESSOR = "no successor"


@dataclass(frozen=True)
class PositionReport:
    group: str
    starters_needed: int
    depth_target: int
    depth: list[DepthEntry]
    issues: list[str]
    issue_kinds: list[str]


@dataclass(frozen=True)
class SquadGaps:
    formation: str
    starting_eleven_median_ability: Measure
    eleven: list[StarterEntry]
    positions: list[PositionReport]


def ageing_age(group: PositionGroup) -> int:
    return AGEING_GOALKEEPER_AGE if group is PositionGroup.GOALKEEPER else AGEING_OUTFIELD_AGE


def depth_entry(player: Player, group: PositionGroup, starters: list[Player], view: View) -> DepthEntry:
    return DepthEntry(
        player.name, player.age, rating(view, player.current_ability), rating(view, player.potential_ability),
        fit(player, group).value,
        player in starters,
    )  # fmt: skip


def group_issues(
    snapshot: Snapshot,
    group: PositionGroup,
    chart: list[Player],
    starters: list[Player],
    needed: int,
    eleven_median: float,
    view: View,
) -> list[tuple[IssueKind, str]]:
    issues: list[tuple[IssueKind, str]] = []
    target = needed * PLAYERS_PER_STARTING_PLACE
    if len(chart) < target:
        issues.append((IssueKind.THIN, f"{len(chart)} of {target} players who can play here"))
    if len(starters) < needed:
        issues.append(
            (IssueKind.EMPTY, f"{needed - len(starters)} of {needed} starting places with nobody to fill them")
        )
        return issues
    for starter in starters:
        if starter.age + LOOKAHEAD_SEASONS >= ageing_age(group):
            issues.append(
                (IssueKind.AGEING, f"{starter.name} is {starter.age}, {starter.age + LOOKAHEAD_SEASONS} in two seasons")
            )
        leaving = leaves_within(starter, snapshot.club_uid, snapshot.game_date, LEAVING_WITHIN_MONTHS)
        if leaving is not None:
            how = "loan ends" if starter.on_loan else "contract ends"
            issues.append((IssueKind.LEAVING, f"{starter.name}'s {how} {leaving.isoformat()}"))
    weakest = min(starters, key=lambda player: player.current_ability)
    if weakest.current_ability < eleven_median - WEAK_STARTER_MARGIN:
        detail = f"{weakest.name} ({ability_text(view, weakest.current_ability)}) starts here, well below the XI median"
        issues.append((IssueKind.WEAK, f"{detail} of {rating_text(view, eleven_median)}"))
    successors = [
        player
        for player in chart
        if player not in starters
        and player.age <= SUCCESSOR_MAX_AGE
        and player.potential_ability >= weakest.current_ability
    ]
    if not successors:
        issues.append((IssueKind.NO_SUCCESSOR, f"nobody {SUCCESSOR_MAX_AGE} or under can reach {weakest.name}'s level"))
    return issues


def squad_gaps(snapshot: Snapshot, formation: Formation, view: View) -> SquadGaps:
    squad = available_squad(snapshot)
    lineup = pick_lineup(squad, formation)
    eleven_median = lineup.median_ability()
    positions: list[PositionReport] = []
    for group, needed in STARTERS[formation].items():
        chart = depth_chart(squad, group)
        starters = lineup.at(group)
        issues = group_issues(snapshot, group, chart, starters, needed, eleven_median, view)
        depth = [depth_entry(player, group, starters, view) for player in chart]
        texts = [f"{kind.value}: {detail}" for kind, detail in issues]
        kinds = [kind.value for kind, _ in issues]
        positions.append(PositionReport(group.value, needed, needed * PLAYERS_PER_STARTING_PLACE, depth, texts, kinds))
    positions.sort(key=lambda position: len(position.issues), reverse=True)
    return SquadGaps(formation.value, measure(view, eleven_median), starter_entries(lineup, view), positions)
