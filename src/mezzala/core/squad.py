from datetime import date
from statistics import median

from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers, group_rating


def plays_for_club(player: Player, club_uid: int) -> bool:
    return player.club_uid == club_uid


def belongs_to_club(player: Player, club_uid: int) -> bool:
    if player.on_loan:
        return player.loan_parent_club_uid == club_uid
    return player.club_uid == club_uid


def is_outside_club(player: Player, club_uid: int) -> bool:
    return not plays_for_club(player, club_uid) and not belongs_to_club(player, club_uid)


def available_squad(snapshot: Snapshot) -> list[Player]:
    return [player for player in snapshot.players if plays_for_club(player, snapshot.club_uid)]


def owned_players(snapshot: Snapshot) -> list[Player]:
    return [player for player in snapshot.players if belongs_to_club(player, snapshot.club_uid)]


def wage_paid_by_club(player: Player, club_uid: int) -> int | None:
    if not player.on_loan or player.loan_wage is None:
        return player.wage
    if plays_for_club(player, club_uid):
        return player.loan_wage
    if player.wage is None:
        return None
    return max(player.wage - player.loan_wage, 0)


def depth_chart(squad: list[Player], group: PositionGroup) -> list[Player]:
    cover = [player for player in squad if covers(player, group)]
    return sorted(cover, key=lambda player: (player.current_ability, group_rating(player, group)), reverse=True)


def months_until(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def leaving_date(player: Player, club_uid: int) -> date | None:
    if player.on_loan and not belongs_to_club(player, club_uid):
        return player.loan_end
    return player.contract_end


def contract_ends_within(player: Player, today: date, months: int) -> date | None:
    end = player.contract_end
    if end is not None and months_until(today, end) <= months:
        return end
    return None


def leaves_within(player: Player, club_uid: int, today: date, months: int) -> date | None:
    leaving = leaving_date(player, club_uid)
    if leaving is not None and months_until(today, leaving) <= months:
        return leaving
    return None


FIRST_ELEVEN = 11
YOUNG_PLAYER_MAX_AGE = 21


def squad_level(snapshot: Snapshot) -> float:
    best = sorted((player.current_ability for player in available_squad(snapshot)), reverse=True)[:FIRST_ELEVEN]
    return median(best) if best else 0.0


def everyone_paid(snapshot: Snapshot) -> list[Player]:
    loaned_in = [player for player in available_squad(snapshot) if player.on_loan]
    return [*owned_players(snapshot), *loaned_in]


NOT_COUNTED_ON = frozenset(
    {"surplus to requirements", "fringe player", "emergency backup", "goalkeeper emergency backup"}
)


def not_counted_on(player: Player) -> bool:
    return player.squad_status in NOT_COUNTED_ON
