from dataclasses import replace
from datetime import date
from pathlib import Path

from factory import MY_CLUB, eleven, mine, player, snapshot

from mezzala.core.players import Budget, PendingDeal

SEASON_END = date(2026, 6, 30)
APRIL = date(2026, 4, 1)


def season_with_moves():
    leaver = mine("Leaver", contract_end=SEASON_END, wage=2_000)
    offered = mine(
        "Offered",
        contract_end=SEASON_END,
        wage=1_000,
        renewal_offer=PendingDeal(MY_CLUB, "Paisley", date(2026, 6, 1), date(2028, 6, 30), 1_200),
    )
    joiner = player("Joiner", moves_lined_up=(PendingDeal(MY_CLUB, "Paisley", date(2026, 7, 1), None, 3_000),))
    return snapshot([*eleven(), leaver, offered, joiner])


def test_the_budget_shows_the_wage_bill_and_room_now_and_after_the_season_ends(mezzala):
    picture = mezzala(season_with_moves()).result("budget")
    assert (picture["wage_budget"], picture["wage_bill"], picture["wage_room"]) == (
        "£60,000 p/w",
        "£55,000 p/w",
        "£5,000 p/w",
    )
    assert picture["after"] == "2026-06-30"
    assert [(m["name"], m["reason"]) for m in picture["leaving"]] == [
        ("Leaver", "contract ends 2026-06-30"),
        ("Offered", "contract ends 2026-06-30, unless he signs the new deal offered"),
    ]
    assert [(m["name"], m["weekly_wage"], m["reason"]) for m in picture["arriving"]] == [
        ("Joiner", "£3,000 p/w", "joins on 2026-07-01")
    ]
    assert (picture["wage_bill_after"], picture["wage_room_after"]) == ("£55,000 p/w", "£5,000 p/w")


def test_a_zero_budget_warns_on_every_answer_that_the_board_may_have_set_one_since(mezzala):
    broke = replace(snapshot(eleven()), budget=Budget(0, 60_000, 55_000, APRIL))
    notes = mezzala(broke).call("squad").data["context"]["notes"]
    assert notes == [
        "The transfer budget read £0. mezzala reads budgets from FM's monthly finance records, and this save's is "
        "the one for April 2026, so budgets the board has set since then do not show yet. Check FM's finances "
        "screen before relying on them."
    ]


def test_a_budget_with_money_left_carries_no_warning(mezzala):
    assert mezzala(snapshot(eleven())).call("squad").data["context"]["notes"] == []


def test_the_finance_month_survives_a_restart(mezzala):
    from mezzala.save.store import SnapshotStore

    first = replace(snapshot(eleven()), budget=Budget(100_000, 60_000, 55_000, APRIL))
    app = mezzala(first)
    app.call("snapshot")
    stored = SnapshotStore(app.database).load(str(Path("career.fm").resolve()), first.game_date)
    assert stored.budget == first.budget
