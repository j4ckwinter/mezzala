from factory import eleven, mine, snapshot


def summaries(mezzala, *players):
    found = mezzala(snapshot([*eleven(), *players])).result("squad")["available"]
    return {member["player"]["name"]: member["player"] for member in found}


def test_summaries_give_the_stronger_foot_and_how_good_the_weaker_one_is(mezzala):
    shown = summaries(mezzala, mine("Lefty", left_foot=20, right_foot=6), mine("Righty", left_foot=11, right_foot=20))
    assert (shown["Lefty"]["preferred_foot"], shown["Lefty"]["weak_foot"]) == ("left", 6)
    assert (shown["Righty"]["preferred_foot"], shown["Righty"]["weak_foot"]) == ("right", 11)


def test_two_strong_feet_read_as_either(mezzala):
    shown = summaries(mezzala, mine("Both", left_foot=15, right_foot=19), mine("Almost", left_foot=14, right_foot=19))
    assert shown["Both"]["preferred_foot"] == "either" and shown["Almost"]["preferred_foot"] == "right"


def test_unknown_feet_stay_unknown(mezzala):
    shown = summaries(mezzala, mine("Mystery"))
    assert (shown["Mystery"]["preferred_foot"], shown["Mystery"]["weak_foot"]) == (None, None)
