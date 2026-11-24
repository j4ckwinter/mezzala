import unicodedata
from dataclasses import dataclass

from mezzala.players import Player, Snapshot
from mezzala.squad import belongs_to_club, plays_for_club

MAX_LISTED_MATCHES = 8


class PlayerNotFound(LookupError):
    pass


@dataclass(frozen=True)
class AmbiguousPlayer(LookupError):
    query: str
    matches: tuple[str, ...]

    def __str__(self) -> str:
        return f"'{self.query}' matches several players: {', '.join(self.matches)}. Use a fuller name."


def folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def describe(player: Player) -> str:
    return f"{player.name} ({player.age}, {player.club_name or 'free agent'})"


def find_player(snapshot: Snapshot, query: str) -> Player:
    wanted = folded(query.strip())
    matches = [player for player in snapshot.players if wanted in folded(player.name)]
    exact = [player for player in matches if folded(player.name) == wanted]
    at_club = [
        player
        for player in exact or matches
        if plays_for_club(player, snapshot.club_uid) or belongs_to_club(player, snapshot.club_uid)
    ]
    for shortlist in (at_club, exact, matches):
        if len(shortlist) == 1:
            return shortlist[0]
        if len(shortlist) > 1:
            names = tuple(describe(player) for player in shortlist[:MAX_LISTED_MATCHES])
            raise AmbiguousPlayer(query, names)
    raise PlayerNotFound(f"No player called '{query}' in this save.")
