import unicodedata
from dataclasses import dataclass

from mezzala.core.players import Player, Snapshot
from mezzala.core.squad import belongs_to_club, plays_for_club

MAX_LISTED_MATCHES = 8


class PlayerNotFound(LookupError):
    pass


@dataclass(frozen=True)
class AmbiguousPlayer(LookupError):
    query: str
    matches: tuple[str, ...]

    def __str__(self) -> str:
        return (
            f"'{self.query}' matches several players: {', '.join(self.matches)}. "
            "Use a fuller name or say which club he plays for."
        )


def folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def describe(player: Player) -> str:
    return f"{player.name} ({player.age}, {player.club_name or 'free agent'})"


def at_named_club(player: Player, club: str | None) -> bool:
    if club is None:
        return True
    return folded(club.strip()) in folded(player.club_name or "free agent")


def likeliness(player: Player) -> tuple[bool, int, int, int]:
    return (player.first_team is True, player.club_reputation or 0, player.reputation, player.current_ability)


@dataclass(frozen=True)
class FoundPlayer:
    player: Player
    notes: list[str]


def likeliest(query: str, namesakes: list[Player]) -> FoundPlayer:
    ranked = sorted(namesakes, key=likeliness, reverse=True)
    chosen, others = ranked[0], ranked[1:]
    if not others:
        return FoundPlayer(chosen, [])
    if likeliness(others[0]) == likeliness(chosen):
        raise AmbiguousPlayer(query, tuple(describe(player) for player in ranked[:MAX_LISTED_MATCHES]))
    passed_over = ", ".join(describe(player) for player in others[:MAX_LISTED_MATCHES])
    note = (
        f"'{query}' matches {len(ranked)} players with the same name; this answer is about {describe(chosen)}, "
        f"the likeliest (first team, bigger club, higher reputation). Also called that: {passed_over}. "
        "Pass club to choose another."
    )
    return FoundPlayer(chosen, [note])


def find_player(snapshot: Snapshot, query: str, club: str | None = None, guess: bool = True) -> FoundPlayer:
    wanted = folded(query.strip())
    matches = [player for player in snapshot.players if wanted in folded(player.name) and at_named_club(player, club)]
    exact = [player for player in matches if folded(player.name) == wanted]
    at_club = [
        player
        for player in exact or matches
        if plays_for_club(player, snapshot.club_uid) or belongs_to_club(player, snapshot.club_uid)
    ]
    for shortlist in (at_club, exact, matches):
        if not shortlist:
            continue
        if len(shortlist) == 1 or (guess and len({folded(player.name) for player in shortlist}) == 1):
            return likeliest(query, shortlist)
        names = tuple(describe(player) for player in shortlist[:MAX_LISTED_MATCHES])
        raise AmbiguousPlayer(query, names)
    if club is not None:
        raise PlayerNotFound(f"No player called '{query}' at a club matching '{club}' in this save.")
    raise PlayerNotFound(f"No player called '{query}' in this save.")
