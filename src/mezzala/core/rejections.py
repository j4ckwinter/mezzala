from dataclasses import replace

from mezzala.core.players import Player, RejectedPlayer, Snapshot, is_same_person
from mezzala.core.signing import can_sign_on_pre_contract
from mezzala.core.squad import is_outside_club

REPUTATION_RISE_WORTH_ANOTHER_TRY = 250


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


def player_in(snapshot: Snapshot, entry: RejectedPlayer) -> Player | None:
    return next(
        (player for player in snapshot.players if player.uid == entry.uid and player.birth_date == entry.birth_date),
        None,
    )


def reasons_to_try_again(entry: RejectedPlayer, then: Snapshot, now: Snapshot) -> list[str]:
    before, after = player_in(then, entry), player_in(now, entry)
    if before is None or after is None or not is_same_person(before, after):
        return []
    reasons: list[str] = []
    if after.is_free_agent and not before.is_free_agent:
        reasons.append("he is a free agent now")
    elif after.club_uid != before.club_uid and not (before.is_free_agent or before.on_loan or after.on_loan):
        reasons.append(f"he has moved from {before.club_name or 'no club'} to {after.club_name or 'no club'}")
    if can_sign_on_pre_contract(after, now.game_date) and not can_sign_on_pre_contract(before, then.game_date):
        end = after.contract_end.isoformat() if after.contract_end else "soon"
        reasons.append(f"his contract ends {end}, so you can agree a pre-contract now")
    if now.club_reputation - then.club_reputation >= REPUTATION_RISE_WORTH_ANOTHER_TRY:
        reasons.append(
            f"your club's reputation has risen from {then.club_reputation} to {now.club_reputation} since he said no"
        )
    return reasons
