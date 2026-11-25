from collections.abc import Iterable

from mezzala.core.players import Player

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
