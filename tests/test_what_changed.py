from dataclasses import replace
from datetime import date

from factory import OTHER_CLUB, eleven, mine, player, snapshot

LATER = date(2026, 9, 1)


def changes(app):
    return app.result("what_changed")


def test_the_first_snapshot_has_nothing_to_compare_with(mezzala):
    result = changes(mezzala(snapshot(eleven())))
    assert result["compared_with"] is None and "nothing to compare" in result["explanation"]


def test_arrivals_departures_and_the_budget_are_reported(mezzala):
    squad = eleven()
    leaver = mine("Leaver")
    signing = player("Signing", club=OTHER_CLUB)
    app = mezzala(snapshot([*squad, leaver, signing], transfer_budget=1_000_000))
    app.call("snapshot")
    moved_out = replace(leaver, club_uid=OTHER_CLUB, club_name="Club 2")
    moved_in = replace(signing, club_uid=1, club_name="Paisley")
    app.play_to(snapshot([*squad, moved_out, moved_in], game_date=LATER, transfer_budget=600_000))
    result = changes(app)
    assert [(c["player"]["name"], c["detail"]) for c in result["joined"]] == [("Signing", "from Club 2")]
    assert [(c["player"]["name"], c["detail"]) for c in result["left"]] == [("Leaver", "now at Club 2")]
    assert result["budget"] == ["transfer budget £1.0m -> £600k"]


def test_ability_contract_and_value_moves_in_the_squad_are_reported(mezzala):
    squad = eleven()
    riser = mine("Riser", ca=100, value=500_000)
    renewed = mine("Renewed", contract_end=date(2027, 5, 31))
    steady = mine("Steady", ca=100)
    app = mezzala(snapshot([*squad, riser, renewed, steady]))
    app.call("snapshot")
    app.play_to(snapshot([*squad, replace(riser, current_ability=108, value=900_000),
                          replace(renewed, contract_end=date(2030, 5, 31)), replace(steady, current_ability=101)],
                         game_date=LATER))  # fmt: skip
    result = changes(app)
    assert [(c["player"]["name"], c["detail"]) for c in result["ability"]] == [("Riser", "CA 100 -> 108")]
    assert [(c["player"]["name"], c["detail"]) for c in result["contracts"]] == [
        ("Renewed", "contract 2027-05-31 -> 2030-05-31")
    ]
    assert [(c["player"]["name"], c["detail"]) for c in result["values"]] == [("Riser", "value £500k -> £900k")]


def test_new_regens_and_big_transfers_elsewhere_are_reported(mezzala):
    squad = eleven()
    star = player("Star", club=OTHER_CLUB, value=20_000_000)
    app = mezzala(snapshot([*squad, star]))
    app.call("snapshot")
    regen = player("Regen", age=15, ca=50, pa=170)
    app.play_to(snapshot([*squad, replace(star, club_uid=3, club_name="Club 3"), regen], game_date=LATER))
    result = changes(app)
    assert result["new_regens"] == 1 and result["best_new_regens"][0]["name"] == "Regen"
    assert [(c["player"]["name"], c["detail"]) for c in result["notable_transfers"]] == [("Star", "Club 2 -> Club 3")]


def test_changes_are_measured_from_the_previous_snapshot_not_the_first(mezzala):
    squad = eleven()
    riser = mine("Riser", ca=100)
    app = mezzala(snapshot([*squad, riser]))
    app.call("snapshot")
    app.play_to(snapshot([*squad, replace(riser, current_ability=110)], game_date=LATER))
    app.play_to(snapshot([*squad, replace(riser, current_ability=112)], game_date=date(2026, 12, 1)))
    result = changes(app)
    assert result["compared_with"] == "2026-09-01"
    assert [c["detail"] for c in result["ability"]] == ["CA 110 -> 112"]


def test_a_loan_is_not_reported_as_a_transfer_and_loan_arrivals_say_so(mezzala):
    squad = eleven()
    star = player("Star", club=OTHER_CLUB, value=20_000_000)
    borrowed = player("Borrowed", club=3)
    app = mezzala(snapshot([*squad, star, borrowed]))
    app.call("snapshot")
    loaned_star = replace(star, club_uid=3, club_name="Club 3", on_loan=True, loan_parent_club_uid=OTHER_CLUB)
    arrived = replace(borrowed, club_uid=1, club_name="Paisley", on_loan=True, loan_parent_club_uid=3)
    app.play_to(snapshot([*squad, loaned_star, arrived], game_date=LATER))
    result = changes(app)
    assert result["notable_transfers"] == []
    assert [c["detail"] for c in result["joined"]] == ["from Club 3 (on loan)"]


def test_a_departed_player_whose_id_was_reused_is_not_placed_at_the_new_persons_club(mezzala):
    squad = eleven()
    leaver = mine("Leaver", age=34)
    app = mezzala(snapshot([*squad, leaver]))
    app.call("snapshot")
    newcomer = replace(leaver, name="Newcomer", age=15, birth_date=date(2011, 1, 1), club_uid=3, club_name="Club 3")
    app.play_to(snapshot([*squad, newcomer], game_date=LATER))
    assert [c["detail"] for c in changes(app)["left"]] == ["no longer in the save"]


def test_a_change_of_club_is_explained_instead_of_compared(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    moved = snapshot([replace(p, club_uid=OTHER_CLUB) for p in squad], game_date=LATER)
    app.play_to(replace(moved, club_uid=OTHER_CLUB, club_name="New Club"))
    result = changes(app)
    assert "You moved from Paisley to New Club" in result["explanation"] and result["left"] == []
