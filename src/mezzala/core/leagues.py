from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from mezzala.core.metrics import league_levels
from mezzala.core.players import Player, Snapshot

CLUBS_IN_LEAGUE_NAME = 3


@dataclass(frozen=True)
class League:
    name: str
    country: str | None
    division_level: int | None


def biggest_clubs(players: Iterable[Player]) -> dict[int, str]:
    clubs: dict[int, dict[str, int]] = {}
    for player in players:
        if player.league_id is not None and player.club_name is not None:
            clubs.setdefault(player.league_id, {})[player.club_name] = player.club_reputation or 0
    return {
        league: ", ".join(sorted(found, key=lambda club: found[club], reverse=True)[:CLUBS_IN_LEAGUE_NAME])
        for league, found in clubs.items()
    }


def league_countries(players: Iterable[Player]) -> dict[int, str]:
    counts: dict[int, Counter[str]] = {}
    for player in players:
        if player.league_id is not None and player.club_country is not None:
            counts.setdefault(player.league_id, Counter())[player.club_country] += 1
    return {league: found.most_common(1)[0][0] for league, found in counts.items()}


def division_levels(levels: dict[int, float], countries: dict[int, str]) -> dict[int, int]:
    by_country: dict[str, list[int]] = {}
    for league, country in countries.items():
        if league in levels:
            by_country.setdefault(country, []).append(league)
    return {
        league: rank
        for found in by_country.values()
        for rank, league in enumerate(sorted(found, key=lambda league: levels[league], reverse=True), start=1)
    }


def leagues(players: Iterable[Player]) -> dict[int, League]:
    listed = list(players)
    countries = league_countries(listed)
    divisions = division_levels(league_levels(listed), countries)
    found: dict[int, League] = {}
    for league, clubs in biggest_clubs(listed).items():
        country, division = countries.get(league), divisions.get(league)
        where = f"{country} division {division}" if country and division else country or "unknown country"
        found[league] = League(f"{where} ({clubs})", country, division)
    return found


def league_names(players: Iterable[Player]) -> dict[int, str]:
    return {league: found.name for league, found in leagues(players).items()}


def club_leagues(players: Iterable[Player]) -> dict[int, int]:
    counts: dict[int, Counter[int]] = {}
    for player in players:
        if player.club_uid is not None and player.league_id is not None and player.first_team:
            counts.setdefault(player.club_uid, Counter())[player.league_id] += 1
    return {club: found.most_common(1)[0][0] for club, found in counts.items()}


def club_league(snapshot: Snapshot) -> int | None:
    return club_leagues(snapshot.players).get(snapshot.club_uid)
