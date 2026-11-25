from factory import eleven, mine, snapshot


def leader(name, age=29, **fields):
    return mine(name, age=age, attributes={"leadership": 18, "determination": 17}, professionalism=16,
                temperament=16, pressure=15, **fields)  # fmt: skip


def test_the_best_leaders_staying_at_the_club_are_captain_candidates(mezzala):
    result = mezzala(snapshot([*eleven(), leader("Skipper")])).result("dressing_room")
    best = result["captain_candidates"][0]
    assert best["name"] == "Skipper"
    assert best["why"] == ["leadership 18", "determination 17", "very professional", "keeps his head",
                           "handles pressure well"]  # fmt: skip


def test_young_players_leaving_players_and_loanees_are_not_captain_candidates(mezzala):
    from datetime import date

    squad = [*eleven(), leader("Kid Leader", age=21), leader("Leaving Leader", contract_end=date(2027, 1, 1)),
             leader("Loanee Leader", on_loan=True, loan_parent_club_uid=9)]  # fmt: skip
    names = [member["name"] for member in mezzala(snapshot(squad)).result("dressing_room")["captain_candidates"]]
    assert not {"Kid Leader", "Leaving Leader", "Loanee Leader"} & set(names)


def test_volatile_and_unprofessional_players_are_concerns(mezzala):
    troublemaker = mine("Troublemaker", controversy=17, temperament=4, professionalism=5)
    result = mezzala(snapshot([*eleven(), troublemaker])).result("dressing_room")
    assert result["concerns"] == [{"name": "Troublemaker", "age": 25, "why": [
        "likely to speak out and stir up trouble", "loses his temper", "unprofessional"]}]  # fmt: skip


def test_an_ambitious_disloyal_star_may_push_to_leave(mezzala):
    star = mine("Star", ca=140, ambition=18, loyalty=5)
    benchwarmer = mine("Benchwarmer", ca=60, ambition=18, loyalty=5)
    concerns = mezzala(snapshot([*eleven(), star, benchwarmer])).result("dressing_room")["concerns"]
    assert concerns == [{"name": "Star", "age": 25, "why": [
        "ambitious, not loyal, and good enough to push for a bigger club"]}]  # fmt: skip


def test_leadership_counts_for_more_than_the_other_qualities(mezzala):
    natural = mine("Natural Leader", age=28, attributes={"leadership": 20, "determination": 10}, professionalism=10,
                   temperament=10, pressure=10)  # fmt: skip
    steady = mine("Steady Pro", age=28, attributes={"leadership": 10, "determination": 14}, professionalism=14,
                  temperament=14, pressure=14)  # fmt: skip
    names = [
        m["name"] for m in mezzala(snapshot([*eleven(), steady, natural])).result("dressing_room")["captain_candidates"]
    ]
    assert names.index("Natural Leader") < names.index("Steady Pro")
