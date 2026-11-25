from factory import OTHER_CLUB, eleven, mine, player, snapshot


def review(app, **arguments):
    return app.result("wage_review", **arguments)


def peers(count, **fields):
    return [player(f"Peer {n}", **fields) for n in range(count)]


def test_players_paid_well_above_similar_players_are_overpaid(mezzala):
    squad = [*eleven(), *peers(25, ca=100, age=25, wage=2_000), mine("Fat Cat", ca=100, age=25, wage=6_000)]
    overpaid = review(mezzala(snapshot(squad)))["overpaid"]
    assert [(e["name"], e["wage_vs_similar_players"]) for e in overpaid] == [("Fat Cat", "3.00x")]


def test_a_player_not_needed_anywhere_is_surplus_and_counts_towards_the_saving(mezzala):
    squad = eleven() + eleven()
    squad.append(mine("Spare Striker", positions=("stc",), ca=60, wage=1_500))
    result = review(mezzala(snapshot(squad)))
    assert [(e["name"], e["role"]) for e in result["surplus"]] == [("Spare Striker", "surplus")]
    assert result["weekly_saving_without_surplus"] == "£1,500 p/w"


def test_a_backup_who_is_the_only_cover_is_needed_for_depth(mezzala):
    squad = [*eleven(), mine("Only Backup Keeper", positions=("gk",), ca=60)]
    result = review(mezzala(snapshot(squad)))
    assert "Only Backup Keeper" not in [e["name"] for e in result["surplus"]]


def test_the_wage_bill_counts_what_the_club_pays_loan_players(mezzala):
    starters = [*[mine(f"Paid {n}", wage=1_000) for n in range(10)]]
    loanee = mine("Loanee", positions=("stc",), wage=9_000, on_loan=True, loan_parent_club_uid=9, loan_wage=500)
    away = player("Away", club=OTHER_CLUB, wage=800, on_loan=True, loan_parent_club_uid=1, loan_wage=300)
    result = review(mezzala(snapshot([*starters, loanee, away])))
    assert result["weekly_wage_bill"] == "£11,000 p/w"


def test_a_young_player_with_first_team_potential_is_a_prospect_not_surplus(mezzala):
    squad = eleven() + eleven()
    squad.append(mine("Prospect", positions=("stc",), age=19, ca=70, pa=140))
    squad.append(mine("Going Nowhere", positions=("stc",), age=19, ca=70, pa=90))
    result = review(mezzala(snapshot(squad)))
    surplus = [e["name"] for e in result["surplus"]]
    assert "Going Nowhere" in surplus
    assert "Prospect" not in surplus
