from dataclasses import replace

from factory import eleven, mine, snapshot


def ranking(app, **arguments):
    return app.result("compare_formations", **arguments)["ranking"]


def back_four_squad():
    return [
        mine("Keeper", positions=("gk",), ca=120),
        *[mine(f"Centre Back {n}", positions=("dc",), ca=120) for n in range(2)],
        mine("Left Back", positions=("dl",), ca=120),
        mine("Right Back", positions=("dr",), ca=120),
        mine("Holder", positions=("dm",), ca=120),
        *[mine(f"Midfielder {n}", positions=("mc",), ca=120) for n in range(2)],
        mine("Left Winger", positions=("aml",), ca=120),
        mine("Right Winger", positions=("amr",), ca=120),
        mine("Striker", positions=("stc",), ca=120),
    ]


def test_the_shape_the_squad_was_built_for_ranks_first(mezzala):
    first = ranking(mezzala(snapshot(back_four_squad())))[0]
    assert (first["formation"], first["rank"], first["score"], first["empty_places"]) == ("4-3-3", 1, 120.0, 0)


def test_empty_places_lower_the_score(mezzala):
    by_formation = {f["formation"]: f for f in ranking(mezzala(snapshot(back_four_squad())))}
    three_at_the_back = by_formation["3-5-2"]
    assert three_at_the_back["empty_places"] == 2
    assert three_at_the_back["weakest_place"] == "centre back: nobody"
    assert three_at_the_back["score"] < by_formation["4-3-3"]["score"]


def test_each_player_appears_once_in_each_eleven(mezzala):
    squad = [*eleven(), mine("Everywhere", positions=("dc", "dm", "mc", "stc"), ca=170)]
    for formation in ranking(mezzala(snapshot(squad))):
        names = [starter["name"] for starter in formation["eleven"] if starter["name"]]
        assert len(names) == len(set(names))
        assert names.count("Everywhere") == 1


def test_only_the_formations_asked_for_are_compared(mezzala):
    formations = ranking(mezzala(snapshot(back_four_squad())), formations=["4-4-2", "4-4-2 diamond"])
    assert sorted(f["formation"] for f in formations) == ["4-4-2", "4-4-2 diamond"]


def test_an_accomplished_starter_is_counted_and_lowers_the_score(mezzala):
    converted = mine("Converted", positions=("amc",), ca=120)
    converted = replace(converted, position_ratings={**converted.position_ratings, "aml": 15})
    squad = [*[p for p in back_four_squad() if p.name != "Left Winger"], converted]
    by_formation = {f["formation"]: f for f in ranking(mezzala(snapshot(squad)))}
    assert by_formation["4-3-3"]["accomplished_starters"] == 1
    assert by_formation["4-3-3"]["score"] == round((120 * 10 + 115) / 11, 1)


def test_formations_within_the_margin_of_the_best_are_marked_tied(mezzala):
    squad = [*back_four_squad(), mine("Playmaker", positions=("amc",), ca=120)]
    by_formation = {f["formation"]: f for f in ranking(mezzala(snapshot(squad)))}
    assert by_formation["4-3-3"]["tied_with_best"] and by_formation["4-2-3-1"]["tied_with_best"]
    assert not by_formation["3-5-2"]["tied_with_best"]


def test_a_formation_asked_for_twice_is_ranked_once(mezzala):
    formations = ranking(mezzala(snapshot(back_four_squad())), formations=["4-3-3", "4-3-3"])
    assert [f["formation"] for f in formations] == ["4-3-3"]


def playmaker_squad(ability: int):
    return [*back_four_squad(), mine("Playmaker", positions=("amc",), ca=ability)]


def test_a_formation_shown_half_a_point_behind_the_best_is_tied(mezzala):
    by_formation = {f["formation"]: f for f in ranking(mezzala(snapshot(playmaker_squad(115))))}
    assert (by_formation["4-3-3"]["score"], by_formation["4-2-3-1"]["score"]) == (120.0, 119.5)
    assert by_formation["4-2-3-1"]["tied_with_best"]


def test_a_formation_more_than_half_a_point_behind_the_best_is_not_tied(mezzala):
    by_formation = {f["formation"]: f for f in ranking(mezzala(snapshot(playmaker_squad(113))))}
    assert by_formation["4-2-3-1"]["score"] == 119.4
    assert not by_formation["4-2-3-1"]["tied_with_best"]
