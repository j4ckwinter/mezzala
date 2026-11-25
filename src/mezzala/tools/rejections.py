from dataclasses import dataclass

from mezzala.core.lookup import folded
from mezzala.core.players import Player, RejectedPlayer, Snapshot


class NotRejected(LookupError):
    pass


@dataclass(frozen=True)
class RejectedEntry:
    name: str
    note: str
    rejected_on: str


@dataclass(frozen=True)
class RejectedList:
    explanation: str
    players: list[RejectedEntry]


EXPLANATION = (
    "Rejected players are left out of find_players, shortlist, find_replacement, contract_watch, risers, "
    "performance and relegated_clubs until they are taken off this list."
)


def rejected_record(player: Player, snapshot: Snapshot, note: str) -> RejectedPlayer:
    return RejectedPlayer(player.uid, player.birth_date, player.name, snapshot.game_date, note)


def find_rejected_entry(entries: list[RejectedPlayer], query: str) -> RejectedPlayer:
    wanted = folded(query.strip())
    exact = [entry for entry in entries if folded(entry.name) == wanted]
    partial = [entry for entry in entries if wanted in folded(entry.name)]
    for found in (exact, partial):
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise NotRejected(f"'{query}' matches several rejected players: {', '.join(e.name for e in found)}.")
    raise NotRejected(f"No player called '{query}' is on the rejected list.")


def rejected_list(entries: list[RejectedPlayer]) -> RejectedList:
    return RejectedList(
        EXPLANATION, [RejectedEntry(entry.name, entry.note, entry.added_on.isoformat()) for entry in entries]
    )
