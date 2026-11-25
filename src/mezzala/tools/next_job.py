from dataclasses import dataclass

from mezzala.core.formations import Formation
from mezzala.core.leagues import club_leagues
from mezzala.core.lineup import pick_lineup
from mezzala.core.metrics import league_levels
from mezzala.core.money import format_money
from mezzala.core.players import Player, Snapshot, Vacancy
from mezzala.core.view import Measure, View, measure


@dataclass(frozen=True)
class JobOption:
    club: str
    club_reputation: int | None
    bigger_than_yours: bool
    league_level: Measure | None
    best_eleven_average: Measure | None
    balance: str
    transfer_budget: str
    advertised: str


@dataclass(frozen=True)
class NextJob:
    your_club_reputation: int
    explanation: str
    jobs: list[JobOption]


EXPLANATION = (
    "Open first-team manager jobs in the save, biggest club first. League level is the median CA of first-team "
    "players in the club's league; money comes from the club's latest finance month where the save has one. "
    "Clubs whose players are not loaded in the save have no league level or best eleven."
)


def squads(snapshot: Snapshot) -> dict[int, list[Player]]:
    found: dict[int, list[Player]] = {}
    for player in snapshot.players:
        if player.club_uid is not None:
            found.setdefault(player.club_uid, []).append(player)
    return found


def option(
    vacancy: Vacancy,
    snapshot: Snapshot,
    squad: list[Player],
    league: int | None,
    levels: dict[int, float],
    formation: Formation,
    view: View,
) -> JobOption:
    return JobOption(
        club=vacancy.club_name,
        club_reputation=vacancy.club_reputation,
        bigger_than_yours=(vacancy.club_reputation or 0) > snapshot.club_reputation,
        league_level=measure(view, levels[league]) if league is not None and league in levels else None,
        best_eleven_average=measure(view, pick_lineup(squad, formation).average_ability()) if squad else None,
        balance=format_money(vacancy.balance),
        transfer_budget=format_money(vacancy.transfer_budget),
        advertised=vacancy.advertised.isoformat() if vacancy.advertised else "unknown",
    )


def next_job(snapshot: Snapshot, formation: Formation, bigger_only: bool, limit: int, view: View) -> NextJob:
    levels = league_levels(snapshot.players)
    by_club = squads(snapshot)
    leagues = club_leagues(snapshot.players)
    jobs = [
        option(
            vacancy, snapshot, by_club.get(vacancy.club_uid, []), leagues.get(vacancy.club_uid), levels, formation, view
        )
        for vacancy in snapshot.vacancies
        if not bigger_only or (vacancy.club_reputation or 0) > snapshot.club_reputation
    ]
    jobs.sort(key=lambda job: job.club_reputation or 0, reverse=True)
    return NextJob(snapshot.club_reputation, EXPLANATION, jobs[:limit])
