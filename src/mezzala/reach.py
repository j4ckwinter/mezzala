from mezzala.players import Player, Snapshot

REPUTATION_REACH = 750


def within_reach(player: Player, snapshot: Snapshot) -> bool:
    return player.reputation <= snapshot.club_reputation + REPUTATION_REACH
