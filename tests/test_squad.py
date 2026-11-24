from datetime import date

from factory import OTHER_CLUB, eleven, mine, player, snapshot


def test_the_squad_lists_everyone_available_best_first_with_their_positions(mezzala):
    star = mine("Star", positions=("dc", "dm"), ca=150)
    loanee = player("Loanee", positions=("dr",), ca=120, club=1, on_loan=True, loan_parent_club_uid=OTHER_CLUB,
                    loan_end=date(2027, 5, 31))  # fmt: skip
    result = mezzala(snapshot([*eleven(), star, loanee])).result("squad")
    first, second = result["available"][:2]
    assert (first["player"]["name"], first["natural_positions"], first["status"]) == (
        "Star",
        ["centre back", "defensive midfield"],
        "permanent",
    )
    assert (second["player"]["name"], second["status"]) == ("Loanee", "loaned in until 2027-05-31")
    assert len(result["available"]) == 13


def test_players_out_on_loan_are_listed_separately(mezzala):
    away = player("Away", positions=("stc",), ca=90, club=OTHER_CLUB, on_loan=True, loan_parent_club_uid=1,
                  loan_end=date(2027, 1, 1))  # fmt: skip
    result = mezzala(snapshot([*eleven(), away])).result("squad")
    assert [(m["player"]["name"], m["status"]) for m in result["loaned_out"]] == [
        ("Away", "loaned out to Club 2 until 2027-01-01")
    ]
    assert "Away" not in [m["player"]["name"] for m in result["available"]]
