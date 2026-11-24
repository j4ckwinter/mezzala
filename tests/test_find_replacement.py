from factory import OTHER_CLUB, eleven, mine, player, snapshot

PASSER = {"passing": 18, "vision": 17, "technique": 16, "tackling": 6, "heading": 5}
DESTROYER = {"tackling": 18, "heading": 17, "strength": 16, "passing": 5, "vision": 6}


def names(app, **arguments):
    return [candidate["player"]["name"] for candidate in app.result("find_replacement", **arguments)["candidates"]]


def test_a_player_who_plays_like_the_target_ranks_first(mezzala):
    target = mine("Old Regista", positions=("dm",), age=33, ca=110, attributes=PASSER)
    alike = player("Young Regista", positions=("dm",), ca=110, attributes=PASSER)
    unlike = player("Enforcer", positions=("dm",), ca=110, attributes=DESTROYER)
    app = mezzala(snapshot([*eleven(), target, unlike, alike]))
    assert names(app, player="Old Regista") == ["Young Regista", "Enforcer"]


def test_reasons_name_the_candidates_strongest_attributes_in_words(mezzala):
    target = mine("Old Regista", positions=("dm",), ca=110, attributes=PASSER)
    alike = player("Set Piece Man", positions=("dm",), ca=110, attributes=PASSER | {"free_kick_taking": 19})
    reasons = mezzala(snapshot([target, alike])).result("find_replacement", player="Old Regista")["candidates"][0]
    assert "strongest in free kick taking, passing, vision, technique" in reasons["reasons"][0]


def test_players_at_the_club_or_too_weak_are_left_out(mezzala):
    target = mine("Captain", positions=("dc",), ca=120)
    teammate = mine("Teammate", positions=("dc",), ca=125)
    weak = player("Weak", positions=("dc",), ca=100, age=28)
    young = player("Prospect", positions=("dc",), ca=100, pa=130, age=19)
    app = mezzala(snapshot([target, teammate, weak, young]))
    assert names(app, player="Captain") == ["Prospect"]


def test_the_fee_defaults_to_the_transfer_budget_but_free_agents_always_fit(mezzala):
    target = mine("Captain", positions=("dc",), ca=120)
    cheap = player("Cheap", positions=("dc",), ca=120, value=400_000)
    dear = player("Dear", positions=("dc",), ca=120, value=3_000_000)
    free = player("Free", positions=("dc",), ca=120, club=None, value=None)
    app = mezzala(snapshot([target, cheap, dear, free], transfer_budget=500_000))
    assert sorted(names(app, player="Captain")) == ["Cheap", "Free"]
    assert sorted(names(app, player="Captain", max_fee=5_000_000)) == ["Cheap", "Dear", "Free"]


def test_players_too_famous_to_join_are_left_out_unless_asked(mezzala):
    target = mine("Captain", positions=("dc",), ca=120)
    star = player("Star", positions=("dc",), ca=150, reputation=8_000)
    app = mezzala(snapshot([target, star], club_reputation=5_000))
    assert names(app, player="Captain") == []
    assert names(app, player="Captain", within_reach=False) == ["Star"]


def test_a_name_is_matched_without_accents_and_prefers_the_club(mezzala):
    ours = mine("Alex Gogić", positions=("dc",), ca=120)
    namesake = player("Alex Gogic Jr", positions=("dc",), ca=121, club=OTHER_CLUB)
    report = mezzala(snapshot([ours, namesake])).result("find_replacement", player="alex gogic")
    assert report["target"]["name"] == "Alex Gogić"
    assert report["target"]["club"] == "Paisley"


def test_an_ambiguous_name_lists_the_matches(mezzala):
    app = mezzala(snapshot([player("John Smith", age=24), player("John Smithson", age=29)]))
    outcome = app.call("find_replacement", player="John Smi")
    assert outcome.is_error
    assert "John Smith (24, Club 2)" in outcome.text and "John Smithson (29, Club 2)" in outcome.text


def test_an_unknown_name_is_an_error(mezzala):
    outcome = mezzala(snapshot(eleven())).call("find_replacement", player="Nobody")
    assert outcome.is_error and "No player called 'Nobody'" in outcome.text
