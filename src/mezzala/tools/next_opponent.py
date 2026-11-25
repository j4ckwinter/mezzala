from dataclasses import dataclass

from mezzala.core.formations import Formation
from mezzala.core.lineup import Lineup, StarterEntry, pick_lineup, starter_entries
from mezzala.core.players import Match, Player, Snapshot
from mezzala.core.profile import outfield_profile
from mezzala.core.squad import available_squad, club_league
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.tools.compare_formations import SCORE_TIE_MARGIN, score

KEY_PLAYERS_SHOWN = 3
RECENT_RESULTS_SHOWN = 5


@dataclass(frozen=True)
class GroupComparison:
    group: str
    yours: float
    theirs: float
    difference: float


@dataclass(frozen=True)
class NextOpponent:
    explanation: str
    date: str | None
    opponent: str | None
    competition: str | None
    venue: str | None
    their_likely_formations: list[str]
    their_eleven: list[StarterEntry]
    their_key_players: list[PlayerSummary]
    attributes: list[GroupComparison]
    their_recent_results: list[str]


NO_FIXTURE = "No upcoming first-team fixture is stored for your club in this save."
EXPLANATION = (
    "Their likely formations are the ones their squad fits best, listing every formation within a whisker of the "
    "best (the eleven shown is for the first); the save does not say which they actually use. The attribute groups "
    "compare their best eleven's outfield players with yours (positive means you are stronger). Recent results are "
    "their last five first-team matches in the save."
)


def next_match(snapshot: Snapshot) -> Match | None:
    upcoming = [
        match
        for match in snapshot.matches
        if not match.played and match.day >= snapshot.game_date
        and snapshot.club_uid in (match.home_club_uid, match.away_club_uid)
    ]  # fmt: skip
    return min(upcoming, key=lambda match: match.day, default=None)


def likely_shapes(squad: list[Player]) -> list[Lineup]:
    lineups = sorted((pick_lineup(squad, formation) for formation in Formation), key=score, reverse=True)
    best = score(lineups[0])
    return [lineup for lineup in lineups if round(best - score(lineup), 1) <= SCORE_TIE_MARGIN]


def competition_label(match: Match, snapshot: Snapshot) -> str:
    return (
        "league"
        if match.competition_id is not None and match.competition_id == club_league(snapshot)
        else "cup or other competition"
    )


def venue(match: Match, home: bool) -> str:
    if match.neutral:
        return "neutral"
    return "home" if home else "away"


def result_line(match: Match, club_uid: int) -> str:
    home = match.home_club_uid == club_uid
    scored, conceded = (match.home_goals, match.away_goals) if home else (match.away_goals, match.home_goals)
    rival = match.away_club_name if home else match.home_club_name
    if scored is None or conceded is None:
        return f"{match.day.isoformat()} v {rival}: score unknown"
    outcome = "W" if scored > conceded else "L" if scored < conceded else "D"
    return f"{match.day.isoformat()} {outcome} {scored}-{conceded} {'v' if home else 'at'} {rival}"


def compare(mine: dict[str, float], theirs: dict[str, float]) -> list[GroupComparison]:
    return [
        GroupComparison(group, mine[group], theirs[group], round(mine[group] - theirs[group], 1))
        for group in mine
        if group in theirs
    ]


def next_opponent(snapshot: Snapshot, formation: Formation) -> NextOpponent:
    match = next_match(snapshot)
    if match is None:
        return NextOpponent(NO_FIXTURE, None, None, None, None, [], [], [], [], [])
    home = match.home_club_uid == snapshot.club_uid
    opponent_uid = match.away_club_uid if home else match.home_club_uid
    squad = [player for player in snapshot.players if player.club_uid == opponent_uid]
    shapes = likely_shapes(squad) if squad else []
    their_lineup = shapes[0] if shapes else None
    mine = outfield_profile(pick_lineup(available_squad(snapshot), formation).starters)
    theirs = outfield_profile(their_lineup.starters) if their_lineup else {}
    played = sorted(
        (m for m in snapshot.matches if m.played and opponent_uid in (m.home_club_uid, m.away_club_uid)),
        key=lambda m: m.day,
        reverse=True,
    )
    return NextOpponent(
        explanation=EXPLANATION,
        date=match.day.isoformat(),
        opponent=match.away_club_name if home else match.home_club_name,
        competition=competition_label(match, snapshot),
        venue=venue(match, home),
        their_likely_formations=[shape.formation.value for shape in shapes],
        their_eleven=starter_entries(their_lineup) if their_lineup else [],
        their_key_players=[
            summarize(p) for p in sorted(squad, key=lambda p: p.current_ability, reverse=True)[:KEY_PLAYERS_SHOWN]
        ],
        attributes=compare(mine, theirs),
        their_recent_results=[result_line(m, opponent_uid) for m in played[:RECENT_RESULTS_SHOWN]],
    )
