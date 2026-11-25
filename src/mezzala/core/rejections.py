from dataclasses import replace

from mezzala.core.players import Player, RejectedPlayer, Snapshot


def is_rejected(player: Player, rejected: list[RejectedPlayer]) -> bool:
    return any(entry.uid == player.uid and entry.birth_date == player.birth_date for entry in rejected)


def without_rejected(snapshot: Snapshot, rejected: list[RejectedPlayer]) -> Snapshot:
    if not rejected:
        return snapshot
    return replace(snapshot, players=tuple(player for player in snapshot.players if not is_rejected(player, rejected)))
