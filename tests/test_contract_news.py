from datetime import date

from factory import MY_CLUB, eleven, player, snapshot

from mezzala.core.players import PendingDeal


def profile_of(app, name):
    return app.result("player_profile", player=name)["profiles"][0]


def test_a_renewal_offer_is_shown_as_an_offer_not_a_contract(mezzala):
    offered = player(
        "Will Ferry",
        contract_end=date(2027, 5, 31),
        renewal_offer=PendingDeal(2, "Club 2", date(2027, 5, 20), date(2030, 5, 31), 2_975),
    )
    summary = profile_of(mezzala(snapshot([*eleven(), offered])), "Will Ferry")["player"]
    assert summary["contract_end"] == "2027-05-31"
    assert summary["contract_news"] == ["Club 2 have offered a new deal until 2030-05-31 at £2,975 p/w, not signed yet"]


def test_a_move_lined_up_says_it_may_still_be_an_offer(mezzala):
    leaving = player("Leaving", moves_lined_up=(PendingDeal(MY_CLUB, "Paisley", date(2027, 7, 1), None, 3_400),))
    news = profile_of(mezzala(snapshot([*eleven(), leaving])), "Leaving")["player"]["contract_news"]
    assert news == [
        "a move to Paisley from 2027-07-01 is lined up "
        "(agreed, or an offer he has not answered: the save does not tell them apart)"
    ]


def test_a_player_with_nothing_pending_has_no_contract_news(mezzala):
    settled = player("Settled")
    assert profile_of(mezzala(snapshot([*eleven(), settled])), "Settled")["player"]["contract_news"] == []
