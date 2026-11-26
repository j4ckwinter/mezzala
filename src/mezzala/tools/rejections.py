from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from mezzala.core.lookup import folded
from mezzala.core.players import Player, RejectedPlayer, Snapshot
from mezzala.core.rejections import reasons_to_try_again


class NotRejected(LookupError):
    pass


@dataclass(frozen=True)
class RejectedEntry:
    name: str
    note: str
    rejected_on: str
    worth_another_try: list[str]


@dataclass(frozen=True)
class RejectedList:
    explanation: str
    players: list[RejectedEntry]


EXPLANATION = (
    "Rejected players are left out of find_players, shortlist, find_replacement, contract_watch, risers, "
    "performance and relegated_clubs until they are taken off this list. worth_another_try says what has changed "
    "since a player said no that makes him worth asking again (take him off with unreject_player)."
)


def rejected_record(player: Player, snapshot: Snapshot, note: str) -> RejectedPlayer:
    return RejectedPlayer(player.uid, player.birth_date, player.name, snapshot.game_date, note)


def at_club(entry: RejectedPlayer, club: str | None, clubs: dict[int, str]) -> bool:
    return club is None or folded(club.strip()) in folded(clubs.get(entry.uid, "free agent"))


def find_rejected_entry(
    entries: list[RejectedPlayer], query: str, club: str | None, snapshot: Snapshot
) -> RejectedPlayer:
    wanted = folded(query.strip())
    clubs = {player.uid: player.club_name or "free agent" for player in snapshot.players}
    matching = [entry for entry in entries if at_club(entry, club, clubs)]
    exact = [entry for entry in matching if folded(entry.name) == wanted]
    partial = [entry for entry in matching if wanted in folded(entry.name)]
    for found in (exact, partial):
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            named = ", ".join(f"{entry.name} ({clubs.get(entry.uid, 'free agent')})" for entry in found)
            raise NotRejected(f"'{query}' matches several rejected players: {named}. Say which club he is at.")
    raise NotRejected(f"No player called '{query}' is on the rejected list.")


def entry_now(entry: RejectedPlayer, snapshot: Snapshot, then: Mapping[date, Snapshot]) -> RejectedEntry:
    earlier = then.get(entry.added_on)
    reasons = [] if earlier is None else reasons_to_try_again(entry, earlier, snapshot)
    return RejectedEntry(entry.name, entry.note, entry.added_on.isoformat(), reasons)


def rejected_list(entries: list[RejectedPlayer], snapshot: Snapshot, then: Mapping[date, Snapshot]) -> RejectedList:
    return RejectedList(EXPLANATION, [entry_now(entry, snapshot, then) for entry in entries])
