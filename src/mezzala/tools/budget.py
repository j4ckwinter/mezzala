from dataclasses import dataclass

from mezzala.core.budget import WageChange, wage_outlook
from mezzala.core.money import format_money, format_weekly_wage
from mezzala.core.players import Snapshot

PENDING_NOTE = (
    "Moves lined up come from deals the save holds, which may still be offers waiting for an answer: the save "
    "does not tell them apart."
)


@dataclass(frozen=True)
class WageMove:
    name: str
    club: str
    weekly_wage: str
    reason: str


@dataclass(frozen=True)
class BudgetPicture:
    finance_month: str
    transfer_budget: str
    wage_budget: str
    wage_bill: str
    wage_room: str
    after: str | None
    leaving: list[WageMove]
    arriving: list[WageMove]
    wage_bill_after: str
    wage_room_after: str
    notes: list[str]


def wage_move(change: WageChange) -> WageMove:
    player = change.player
    return WageMove(
        player.name, player.club_name or "free agent", format_weekly_wage(change.weekly_wage), change.reason
    )


def budget_picture(snapshot: Snapshot) -> BudgetPicture:
    budget = snapshot.budget
    outlook = wage_outlook(snapshot)
    notes = [PENDING_NOTE]
    if outlook is not None:
        notes.append(
            f"The wage room after {outlook.after.isoformat()} assumes the board keeps the wage budget at "
            f"{format_weekly_wage(budget.wage_budget_weekly)}; it may set a new one for next season."
        )
    return BudgetPicture(
        finance_month=f"{budget.month:%B %Y}" if budget.month else "unknown",
        transfer_budget=format_money(budget.transfer_remaining),
        wage_budget=format_weekly_wage(budget.wage_budget_weekly),
        wage_bill=format_weekly_wage(budget.wage_payroll_weekly),
        wage_room=format_weekly_wage(budget.wage_headroom_weekly),
        after=outlook.after.isoformat() if outlook else None,
        leaving=[wage_move(change) for change in outlook.leaving] if outlook else [],
        arriving=[wage_move(change) for change in outlook.arriving] if outlook else [],
        wage_bill_after=format_weekly_wage(outlook.bill if outlook else None),
        wage_room_after=format_weekly_wage(outlook.room if outlook else None),
        notes=notes,
    )
