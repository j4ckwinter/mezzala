from dataclasses import replace

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
    assert striker["weekly_wage"] == "about £4,000 p/w (the going rate at clubs like yours in your country)"
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


def test_a_player_is_shortlisted_for_one_position_only(mezzala):
    squad = [*[p for p in without("stc") if p.position_ratings["amc"] != 20]]
    squad += [mine("Weak Striker", positions=("stc",), ca=60), mine("Weak Wide", positions=("aml",), ca=60)]
    squad = [p for p in squad if p.position_ratings["aml"] != 20 or p.name == "Weak Wide"]
    squad.append(player("Two Way", positions=("stc", "aml"), ca=130, value=50_000))
    result = mezzala(snapshot(squad, transfer_budget=1_000_000)).result("shortlist")
    chosen = [pick["target"]["name"] for pick in result["picks"] if pick["target"]]
    assert chosen.count("Two Way") == 1


def test_positions_without_issues_are_left_off(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad.append(player("Great Keeper", positions=("gk",), ca=150, value=50_000))
    assert mezzala(snapshot(squad)).result("shortlist")["picks"] == []


def test_targets_out_of_reach_are_not_shortlisted(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad.append(player("Star", positions=("stc",), ca=150, value=50_000, reputation=9_000))
    assert picks(mezzala(snapshot(squad)))["striker"]["target"] is None


def test_each_picks_wage_comes_off_the_wage_room(mezzala):
    squad = [p for p in without("stc") if p.position_ratings["gk"] != 20]
    squad += [mine("Weak Keeper", positions=("gk",), ca=60), mine("Weak Striker", positions=("stc",), ca=60)]
    squad += [player("Keeper", positions=("gk",), ca=120, value=50_000, wage=3_000),
              player("Striker", positions=("stc",), ca=120, value=50_000, wage=3_000)]  # fmt: skip
    result = mezzala(snapshot(squad)).result("shortlist", weekly_wage_budget=5_000)
    assert len([pick for pick in result["picks"] if pick["target"]]) == 1


def test_among_near_equals_the_one_lighter_on_the_tighter_budget_wins(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Cheap Fee Big Wage", positions=("stc",), ca=120, value=10_000, wage=4_800),
              player("Dear Fee Small Wage", positions=("stc",), ca=119, value=50_000, wage=1_000)]  # fmt: skip
    striker = picks(mezzala(snapshot(squad, transfer_budget=1_000_000)), weekly_wage_budget=5_000)["striker"]
    assert striker["target"]["name"] == "Dear Fee Small Wage"


def test_the_going_rate_comes_from_clubs_in_your_country_first(mezzala):
    home = [player(f"Home {n}", positions=("gk",), ca=120, age=27, wage=3_000) for n in range(6)]
    abroad = [player(f"Abroad {n}", positions=("gk",), ca=120, age=27, wage=9_000, club_nation_id=139)
              for n in range(10)]  # fmt: skip
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70), *home, *abroad]
    squad.append(player("Free Striker", positions=("stc",), ca=120, age=27, club=None, value=None, wage=None))
    striker = picks(mezzala(snapshot(squad)), weekly_wage_budget=5_000)["striker"]
    assert striker["weekly_wage"] == "about £3,000 p/w (the going rate at clubs like yours in your country)"


def test_a_worldwide_estimate_is_labelled_as_one(mezzala):
    peers = [player(f"Peer {n}", positions=("gk",), ca=120, age=27, wage=2_000, club_reputation=9_000)
             for n in range(25)]  # fmt: skip
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70), *peers]
    squad.append(player("Free Striker", positions=("stc",), ca=120, age=27, club=None, value=None, wage=None))
    striker = picks(mezzala(snapshot(squad)), weekly_wage_budget=5_000)["striker"]
    assert striker["weekly_wage"] == "about £2,000 p/w (similar players worldwide)"


def test_no_target_is_old_enough_to_be_ageing_within_two_seasons(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player("Twenty Eight", positions=("stc",), age=28, ca=125, value=50_000),
              player("Twenty Seven", positions=("stc",), age=27, ca=115, value=50_000)]  # fmt: skip
    assert picks(mezzala(snapshot(squad, transfer_budget=1_000_000)))["striker"]["target"]["name"] == "Twenty Seven"


def test_reserve_team_wages_do_not_set_the_going_rate(mezzala):
    first_team = [player(f"Regular {n}", positions=("gk",), ca=120, age=27, wage=3_000) for n in range(6)]
    reserves = [player(f"Reserve {n}", positions=("gk",), ca=120, age=27, wage=9_000, first_team=False)
                for n in range(10)]  # fmt: skip
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70), *first_team, *reserves]
    squad.append(player("Free Striker", positions=("stc",), ca=120, age=27, club=None, value=None, wage=None))
    striker = picks(mezzala(snapshot(squad)), weekly_wage_budget=5_000)["striker"]
    assert striker["weekly_wage"].startswith("about £3,000 p/w")


def test_a_wider_domestic_band_is_tried_before_clubs_abroad(mezzala):
    home = [player(f"Home {n}", positions=("gk",), ca=112, age=27, wage=3_000) for n in range(6)]
    abroad = [player(f"Abroad {n}", positions=("gk",), ca=120, age=27, wage=9_000, club_nation_id=139)
              for n in range(10)]  # fmt: skip
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70), *home, *abroad]
    squad.append(player("Free Striker", positions=("stc",), ca=120, age=27, club=None, value=None, wage=None))
    striker = picks(mezzala(snapshot(squad)), weekly_wage_budget=5_000)["striker"]
    assert striker["weekly_wage"] == "about £3,000 p/w (the going rate at clubs like yours in your country)"


def out_of_position_right_winger():
    ramos = mine("Ramos", positions=("aml",), ca=100)
    return replace(ramos, position_ratings={**ramos.position_ratings, "amr": 16})


def test_a_starter_out_of_position_makes_his_place_a_target(mezzala):
    squad = [*without("amr"), out_of_position_right_winger()]
    squad += [player("Right Winger", positions=("amr",), ca=98, value=200_000)]
    right = picks(mezzala(snapshot(squad)))["right wing"]
    assert right["target"]["name"] == "Right Winger"
    assert right["improves_on"] == "Ramos (100, out of position)"


def test_the_bar_is_the_starter_with_the_lowest_level_in_the_place_not_the_lowest_ability(mezzala):
    squad = [p for p in eleven() if p.position_ratings["dc"] != 20]
    stretched = mine("Stretched", positions=("dl",), ca=103)
    squad += [mine("Natural Centre Back", positions=("dc",), ca=100), mine("Left Back", positions=("dl",), ca=104),
              replace(stretched, position_ratings={**stretched.position_ratings, "dc": 16}),
              player("Centre Back Target", positions=("dc",), ca=99, value=200_000)]  # fmt: skip
    centre = picks(mezzala(snapshot(squad)))["centre back"]
    assert centre["improves_on"] == "Stretched (103, out of position)"
    assert centre["target"]["name"] == "Centre Back Target"
