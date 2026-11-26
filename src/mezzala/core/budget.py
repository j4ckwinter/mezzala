import calendar
from collections import Counter
from dataclasses import dataclass
from datetime import date

from mezzala.core.players import Budget, Player, Snapshot
from mezzala.core.squad import belongs_to_club, everyone_paid, leaving_date, owned_players, wage_paid_by_club


@dataclass(frozen=True)
class WageChange:
    player: Player
    weekly_wage: int | None
    reason: str


@dataclass(frozen=True)
class WageOutlook:
    after: date
    leaving: list[WageChange]
    arriving: list[WageChange]
    bill: int | None
    room: int | None


def on_or_after(today: date, month: int, day: int) -> date:
    for year in (today.year, today.year + 1):
        candidate = date(year, month, min(day, calendar.monthrange(year, month)[1]))
        if candidate >= today:
            return candidate
    raise ValueError("a date a year on is always on or after today")


def season_end(snapshot: Snapshot) -> date | None:
    ends = Counter(
        (player.contract_end.month, player.contract_end.day)
        for player in owned_players(snapshot)
        if player.contract_end is not None
    )
    if not ends:
        return None
    month, day = ends.most_common(1)[0][0]
    return on_or_after(snapshot.game_date, month, day)


def leaving_reason(player: Player, snapshot: Snapshot, by: date) -> str | None:
    leaving = leaving_date(player, snapshot.club_uid)
    if leaving is not None and leaving <= by:
        kind = "contract" if belongs_to_club(player, snapshot.club_uid) else "loan"
        unless = ", unless he signs the new deal offered" if player.renewal_offer else ""
        return f"{kind} ends {leaving.isoformat()}{unless}"
    away = [move for move in player.moves_lined_up if move.club_uid != snapshot.club_uid]
    if away:
        return f"a move to {away[0].club_name or 'another club'} is lined up"
    return None


def leavers(snapshot: Snapshot, by: date) -> list[WageChange]:
    found: list[WageChange] = []
    for player in everyone_paid(snapshot):
        reason = leaving_reason(player, snapshot, by)
        if reason is not None:
            found.append(WageChange(player, wage_paid_by_club(player, snapshot.club_uid), reason))
    return found


def arrivals(snapshot: Snapshot) -> list[WageChange]:
    found: list[WageChange] = []
    for player in snapshot.players:
        if belongs_to_club(player, snapshot.club_uid):
            continue
        for move in player.moves_lined_up:
            if move.club_uid == snapshot.club_uid:
                starts = move.starts.isoformat() if move.starts else "an unknown date"
                found.append(WageChange(player, move.wage, f"joins on {starts}"))
    return found


def total(changes: list[WageChange]) -> int:
    return sum(change.weekly_wage or 0 for change in changes)


def wage_outlook(snapshot: Snapshot) -> WageOutlook | None:
    after = season_end(snapshot)
    if after is None:
        return None
    leaving = leavers(snapshot, after)
    arriving = arrivals(snapshot)
    payroll = snapshot.budget.wage_payroll_weekly
    bill = None if payroll is None else payroll - total(leaving) + total(arriving)
    wage_budget = snapshot.budget.wage_budget_weekly
    room = None if bill is None or wage_budget is None else wage_budget - bill
    return WageOutlook(after, leaving, arriving, bill, room)


def budget_warnings(budget: Budget) -> list[str]:
    zero = [
        name
        for name, amount in (("transfer budget", budget.transfer_remaining), ("wage budget", budget.wage_budget_weekly))
        if amount == 0
    ]
    if not zero:
        return []
    record = f"the one for {budget.month:%B %Y}" if budget.month else "the latest"
    return [
        f"The {' and '.join(zero)} read £0. mezzala reads budgets from FM's monthly finance records, and this save's "
        f"is {record}, so budgets the board has set since then do not show yet. Check FM's finances screen "
        "before relying on them."
    ]
