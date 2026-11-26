from datetime import date

from factory import eleven, player, snapshot

from mezzala.core.players import PendingDeal

FOREIGN = 999
SOON = date(2026, 12, 15)
LATER = date(2027, 5, 31)


def targets(app):
    return {t["player"]["name"]: t for t in app.result("contract_watch")["pre_contract_targets"]}


def keeper(name, **fields):
    return player(name, positions=("gk",), ca=120, club_nation_id=FOREIGN, **fields)


def test_a_contract_ending_within_six_months_can_be_signed_on_a_pre_contract_now(mezzala):
    found = targets(mezzala(snapshot([*eleven(), keeper("Soon", contract_end=SOON)])))
    assert found["Soon"]["reason"] == "contract ends 2026-12-15: you can agree a pre-contract now"
    assert found["Soon"]["warnings"] == []


def test_a_contract_ending_later_says_when_a_pre_contract_becomes_possible(mezzala):
    found = targets(mezzala(snapshot([*eleven(), keeper("Later", contract_end=LATER)])))
    assert found["Later"]["reason"] == (
        "contract ends 2027-05-31: a pre-contract is possible from 2026-11-30, a cut-price fee before then"
    )


def test_players_on_loan_are_targets_with_a_warning(mezzala):
    loanee = keeper("Loanee", contract_end=SOON, on_loan=True, loan_parent_club_uid=7, loan_end=date(2027, 5, 31))
    found = targets(mezzala(snapshot([*eleven(), loanee])))
    assert found["Loanee"]["warnings"] == ["on loan at Club 2: players on loan often refuse a pre-contract"]


def test_players_at_clubs_in_your_own_country_come_with_a_warning(mezzala):
    domestic = player("Domestic", positions=("gk",), ca=120, contract_end=SOON)
    assert targets(mezzala(snapshot([*eleven(), domestic])))["Domestic"]["warnings"] == [
        "at a club in your own country: such players often refuse a pre-contract, so expect to wait "
        "for his contract to end or to pay a fee"
    ]


def test_an_open_renewal_offer_and_a_move_lined_up_are_warnings(mezzala):
    offered = keeper(
        "Offered",
        contract_end=SOON,
        renewal_offer=PendingDeal(2, "Club 2", date(2026, 6, 1), date(2029, 6, 30), 3_000),
        moves_lined_up=(PendingDeal(8, "Rival FC", date(2027, 1, 1), None, None),),
    )
    assert targets(mezzala(snapshot([*eleven(), offered])))["Offered"]["warnings"] == [
        "his club has offered him a new deal until 2029-06-30, and he may sign it first",
        "a move to Rival FC is lined up from 2027-01-01",
    ]


def test_find_players_can_keep_only_players_you_can_sign_on_a_pre_contract_now(mezzala):
    squad = [*eleven(), keeper("Soon", contract_end=SOON), keeper("Later", contract_end=LATER)]
    found = mezzala(snapshot(squad)).result("find_players", pre_contract_only=True)["players"]
    assert [f["player"]["name"] for f in found] == ["Soon"]


def test_players_you_can_sign_on_a_pre_contract_now_come_first(mezzala):
    better = player("Later But Better", positions=("gk",), ca=130, club_nation_id=FOREIGN, contract_end=LATER)
    squad = [*eleven(), better, keeper("Soon", contract_end=SOON)]
    assert list(targets(mezzala(snapshot(squad)))) == ["Soon", "Later But Better"]
