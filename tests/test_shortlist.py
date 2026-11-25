from factory import eleven, mine, player, snapshot


def without(position_code):
    return [p for p in eleven() if p.position_ratings[position_code] != 20]


def picks(app, **arguments):
    return {pick["position"]: pick for pick in app.result("shortlist", **arguments)["picks"]}


def test_each_weak_position_gets_the_best_affordable_player_who_beats_the_starter(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Dear Striker", positions=("stc",), ca=150, value=9_000_000),
              player("Good Striker", positions=("stc",), ca=120, value=800_000),
              player("Okay Striker", positions=("stc",), ca=110, value=300_000)]  # fmt: skip
    striker = picks(mezzala(snapshot(squad, transfer_budget=1_000_000)))["striker"]
    assert striker["target"]["name"] == "Good Striker"
    assert striker["improves_on"] == "Weak Striker (70)"
    assert [alternative["name"] for alternative in striker["alternatives"]] == ["Okay Striker"]


def test_the_budget_is_spent_down_across_positions(mezzala):
    squad = [*[p for p in without("stc") if p.position_ratings["gk"] != 20]]
    squad += [mine("Weak Keeper", positions=("gk",), ca=60), mine("Weak Striker", positions=("stc",), ca=60)]
    squad += [player("Keeper", positions=("gk",), ca=120, value=700_000),
              player("Cheap Keeper", positions=("gk",), ca=100, value=200_000),
              player("Striker", positions=("stc",), ca=120, value=700_000),
              player("Cheap Striker", positions=("stc",), ca=100, value=250_000)]  # fmt: skip
    result = mezzala(snapshot(squad, transfer_budget=1_000_000)).result("shortlist")
    chosen = {pick["position"]: pick["target"]["name"] for pick in result["picks"] if pick["target"]}
    assert chosen == {"goalkeeper": "Keeper", "striker": "Cheap Striker"}
    assert result["total_fees"] == "£950k"


def test_wages_must_fit_the_wage_room(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Expensive Wages", positions=("stc",), ca=130, value=100_000, wage=20_000),
              player("Modest Wages", positions=("stc",), ca=110, value=100_000, wage=3_000)]  # fmt: skip
    striker = picks(mezzala(snapshot(squad)), weekly_wage_budget=5_000)["striker"]
    assert (striker["target"]["name"], striker["weekly_wage"]) == ("Modest Wages", "£3,000 p/w")


def test_a_target_is_expected_to_want_the_going_rate_at_clubs_like_yours(mezzala):
    paid = [player(f"Paid {n}", positions=("gk",), ca=120, age=27, wage=4_000) for n in range(6)]
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70), *paid]
    squad += [player("Free Striker", positions=("stc",), ca=120, age=27, club=None, value=None, wage=None),
              player("Underpaid Striker", positions=("stc",), ca=119, age=27, value=50_000, wage=300)]  # fmt: skip
    app = mezzala(snapshot(squad))
    striker = picks(app, weekly_wage_budget=5_000)["striker"]
    assert striker["weekly_wage"] == "about £4,000 p/w (the going rate for his ability at clubs like yours)"
    assert picks(app, weekly_wage_budget=3_000)["striker"]["target"] is None


def test_an_ageing_position_gets_a_younger_target(mezzala):
    squad = [*without("stc"), *without("stc"), mine("Old Striker", positions=("stc",), age=31, ca=100, pa=100)]
    squad += [player("Older", positions=("stc",), age=28, ca=125, value=50_000),
              player("Younger", positions=("stc",), age=26, ca=115, value=50_000)]  # fmt: skip
    assert picks(mezzala(snapshot(squad, transfer_budget=1_000_000)))["striker"]["target"]["name"] == "Younger"


def test_the_cheapest_of_the_near_best_targets_is_picked(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Best But Dear", positions=("stc",), ca=122, value=900_000),
              player("Nearly As Good", positions=("stc",), ca=120, value=100_000)]  # fmt: skip
    assert picks(mezzala(snapshot(squad, transfer_budget=1_000_000)))["striker"]["target"]["name"] == "Nearly As Good"


def test_a_position_with_nothing_affordable_says_so(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Dear Striker", positions=("stc",), ca=150, value=9_000_000),
              player("Worse Cheap Striker", positions=("stc",), ca=65, value=50_000)]  # fmt: skip
    striker = picks(mezzala(snapshot(squad, transfer_budget=100_000)))["striker"]
    assert striker["target"] is None
    assert striker["why"]


def test_a_player_whose_wage_cannot_be_worked_out_does_not_fit_a_wage_room(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Mystery Free Agent", positions=("stc",), ca=125, club=None, value=None, wage=None),
              player("Zero Wage Amateur", positions=("stc",), ca=124, value=0, wage=0),
              player("Known Wage", positions=("stc",), ca=115, value=50_000, wage=2_000)]  # fmt: skip
    app = mezzala(snapshot(squad))
    assert picks(app, weekly_wage_budget=5_000)["striker"]["target"]["name"] == "Known Wage"
