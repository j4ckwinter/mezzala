from collections import Counter
from collections.abc import Iterable

from mezzala.core.players import Player, Snapshot

CLUBS_IN_LEAGUE_NAME = 3


def league_names(players: Iterable[Player]) -> dict[int, str]:
    clubs: dict[int, dict[str, int]] = {}
    for player in players:
        if player.league_id is not None and player.club_name is not None:
            clubs.setdefault(player.league_id, {})[player.club_name] = player.club_reputation or 0
    return {
        league: ", ".join(sorted(found, key=lambda club: found[club], reverse=True)[:CLUBS_IN_LEAGUE_NAME])
        for league, found in clubs.items()
    }


def club_leagues(players: Iterable[Player]) -> dict[int, int]:
    counts: dict[int, Counter[int]] = {}
    for player in players:
        if player.club_uid is not None and player.league_id is not None and player.first_team:
            counts.setdefault(player.club_uid, Counter())[player.league_id] += 1
    return {club: found.most_common(1)[0][0] for club, found in counts.items()}


def club_league(snapshot: Snapshot) -> int | None:
    return club_leagues(snapshot.players).get(snapshot.club_uid)
