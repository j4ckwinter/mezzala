from dataclasses import replace

from factory import eleven, mine, snapshot

FORWARD = {"dribbling": 15, "finishing": 15, "first_touch": 15, "technique": 15, "off_the_ball": 15,
           "acceleration": 15, "agility": 15}  # fmt: skip


def fit(mezzala, squad, *slots):
    return mezzala(snapshot(squad)).result("tactic_fit", slots=list(slots))


def by_slot(result):
    return {entry["slot"]: entry for entry in result["slots"]}


def test_an_inside_forward_on_the_left_favours_a_right_footed_player(mezzala):
    squad = [mine("Lefty", positions=("aml",), attributes=FORWARD, left_foot=20, right_foot=5),
             mine("Righty", positions=("aml",), attributes=FORWARD, left_foot=5, right_foot=20)]  # fmt: skip
    left = by_slot(fit(mezzala, squad, "AML: inside forward"))["AML"]
    assert (left["player"], left["preferred_foot"]) == ("Righty", "right")
    assert left["alternatives"] == ["Lefty (12)"]
    assert left["role_score"] == 14.0


def test_a_winger_on_the_left_favours_a_left_footed_player(mezzala):
    squad = [mine("Lefty", positions=("aml",), attributes=FORWARD, left_foot=20, right_foot=5),
             mine("Righty", positions=("aml",), attributes=FORWARD, left_foot=5, right_foot=20)]  # fmt: skip
    assert by_slot(fit(mezzala, squad, "AML: winger"))["AML"]["player"] == "Lefty"


def test_roles_pick_different_players_for_the_same_position(mezzala):
    target_man = mine("Big Man", positions=("stc",), attributes={"heading": 18, "jumping_reach": 18, "strength": 18,
                                                                  "bravery": 16, "balance": 14})  # fmt: skip
    finisher = mine("Finisher", positions=("stc",), attributes=FORWARD)
    assert by_slot(fit(mezzala, [target_man, finisher], "STC: target forward"))["STC"]["player"] == "Big Man"
    assert by_slot(fit(mezzala, [target_man, finisher], "STC: advanced forward"))["STC"]["player"] == "Finisher"


def test_each_player_fills_one_slot_and_an_accomplished_player_pays_a_point(mezzala):
    natural = mine("Natural", positions=("dc",))
    stretched = mine("Stretched", positions=("dl",))
    stretched = replace(stretched, position_ratings={**stretched.position_ratings, "dc": 16})
    slots = by_slot(fit(mezzala, [natural, stretched], "DCL: centre-back", "DCR: centre-back"))
    assert {slots["DCL"]["player"], slots["DCR"]["player"]} == {"Natural", "Stretched"}
    assert sorted(entry["role_score"] for entry in slots.values()) == [9.0, 10.0]


def test_the_weakest_slots_are_listed_and_empty_slots_say_nobody(mezzala):
    result = fit(mezzala, eleven(), "GK: goalkeeper", "WBR: wing-back", "AMC: shadow striker")
    assert result["weakest_slots"][0] == "AMC shadow striker: nobody"


def test_short_names_and_spellings_of_roles_are_understood(mezzala):
    result = fit(mezzala, eleven(), "aml: IF", "WBL : wing back", "DC: ball playing defender")
    assert [entry["role"] for entry in result["slots"]] == [
        "inside forward (opposite side foot)", "wing-back (same side foot)", "ball-playing centre-back"]  # fmt: skip


def test_an_unknown_slot_or_role_is_explained(mezzala):
    app = mezzala(snapshot(eleven()))
    slot = app.call("tactic_fit", slots=["LW: winger"])
    role = app.call("tactic_fit", slots=["AML: luxury player"])
    assert slot.is_error and "Use FM's position codes" in slot.text
    assert role.is_error and "is not a role mezzala knows" in role.text


def test_every_fm_slot_code_is_understood(mezzala):
    codes = ["GK", "DL", "DCL", "DC", "DCR", "DR", "WBL", "WBR", "DM", "DMCL", "DMCR", "ML", "MCL", "MC", "MCR", "MR",
             "AML", "AMCL", "AMC", "AMCR", "AMR", "STCL", "STC", "STCR", "ST"]  # fmt: skip
    result = fit(mezzala, eleven(), *(f"{code}: centre-back" for code in codes))
    assert [entry["slot"] for entry in result["slots"]] == codes
