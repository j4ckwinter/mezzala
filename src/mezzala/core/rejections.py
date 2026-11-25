from dataclasses import replace

from mezzala.core.players import Player, RejectedPlayer, Snapshot
from mezzala.core.squad import is_outside_club


def is_rejected(player: Player, rejected: list[RejectedPlayer]) -> bool:
    return any(entry.uid == player.uid and entry.birth_date == player.birth_date for entry in rejected)


def without_rejected(snapshot: Snapshot, rejected: list[RejectedPlayer]) -> Snapshot:
    if not rejected:
        return snapshot
    kept = (
        player
        for player in snapshot.players
        if not (is_outside_club(player, snapshot.club_uid) and is_rejected(player, rejected))
    )
    return replace(snapshot, players=tuple(kept))
