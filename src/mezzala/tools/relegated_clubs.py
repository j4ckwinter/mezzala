from dataclasses import dataclass

from mezzala.core.leagues import club_leagues, league_names
from mezzala.core.metrics import league_levels
from mezzala.core.players import Player, Snapshot
from mezzala.core.reach import within_reach
from mezzala.core.summary import PlayerSummary, summarize
from mezzala.core.view import View

PLAYERS_SHOWN_PER_CLUB = 3


NO_LEAGUES_THEN = (
    "The snapshot compared with was taken before mezzala recorded leagues, so relegations cannot be worked out "
    "from it. Ask again with a later since date that is still before the season changed."
)


@dataclass(frozen=True)
class RelegatedClub:
    club: str
    from_league: str
    to_league: str
    players_worth_a_look: list[PlayerSummary]


@dataclass(frozen=True)
class RelegatedClubs:
    compared_with: str | None
    explanation: str
    clubs: list[RelegatedClub]


NO_HISTORY = (
    "Relegation shows as a club moving to a weaker league between two snapshots, so it needs a snapshot from "
    "before the season changed. Until then, find_players sorted by 'above league level' finds players too good "
    "for their league."
)


def worth_a_look(players: list[Player], snapshot: Snapshot, view: View) -> list[PlayerSummary]:
    reachable = [player for player in players if within_reach(player, snapshot)]
    reachable.sort(key=lambda player: player.current_ability, reverse=True)
    return [summarize(player, view) for player in reachable[:PLAYERS_SHOWN_PER_CLUB]]


def relegated_clubs(current: Snapshot, baseline: Snapshot | None, view: View) -> RelegatedClubs:
    if baseline is None:
        return RelegatedClubs(None, NO_HISTORY, [])
    if not any(player.league_id is not None for player in baseline.players):
        return RelegatedClubs(baseline.game_date.isoformat(), NO_LEAGUES_THEN, [])
    then, now = club_leagues(baseline.players), club_leagues(current.players)
    then_levels, now_levels = league_levels(baseline.players), league_levels(current.players)
    names = league_names(current.players)
    old_names = league_names(baseline.players)
    squads: dict[int, list[Player]] = {}
    for player in current.players:
        if player.club_uid is not None:
            squads.setdefault(player.club_uid, []).append(player)
    clubs: list[RelegatedClub] = []
    for club, league in now.items():
        before = then.get(club)
        if before is None or before == league or before not in then_levels or league not in now_levels:
            continue
        if now_levels[league] >= then_levels[before]:
            continue
        squad = squads.get(club, [])
        club_name = next((p.club_name for p in squad if p.club_name), "unknown")
        clubs.append(RelegatedClub(club_name, old_names.get(before, "unknown"), names.get(league, "unknown"),
                                   worth_a_look(squad, current, view)))  # fmt: skip
    explanation = (
        f"Clubs now in a weaker league than on {baseline.game_date.isoformat()}, with their best players within reach."
    )
    return RelegatedClubs(baseline.game_date.isoformat(), explanation, clubs)
