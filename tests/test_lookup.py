from factory import eleven, player, snapshot


def namesakes():
    senior = player("Matthew Anderson", age=23, club=3, club_name="KV Kortrijk", club_reputation=6_000)
    youth = player(
        "Matthew Anderson", age=16, club=4, club_name="Annagh United", club_reputation=1_000, first_team=False
    )
    return snapshot([*eleven(), youth, senior])


def test_players_with_the_same_name_resolve_to_the_likeliest_with_a_note(mezzala):
    outcome = mezzala(namesakes()).call("player_profile", player="Matthew Anderson")
    assert not outcome.is_error, outcome.text
    assert outcome.data["result"]["profiles"][0]["player"]["club"] == "KV Kortrijk"
    assert outcome.data["context"]["notes"] == [
        "'Matthew Anderson' matches 2 players with the same name; this answer is about Matthew Anderson "
        "(23, KV Kortrijk), the likeliest (first team, bigger club, higher reputation). Also called that: "
        "Matthew Anderson (16, Annagh United). Pass club to choose another."
    ]


def test_naming_the_club_still_picks_the_other_namesake(mezzala):
    outcome = mezzala(namesakes()).call("player_profile", player="Matthew Anderson", club="Annagh")
    assert outcome.data["result"]["profiles"][0]["player"]["club"] == "Annagh United"
    assert outcome.data["context"]["notes"] == []


def test_namesakes_nothing_tells_apart_are_still_ambiguous(mezzala):
    twins = snapshot([*eleven(), player("João Silva", club=2), player("João Silva", club=3)])
    outcome = mezzala(twins).call("player_profile", player="João Silva")
    assert outcome.is_error and "matches several players" in outcome.text
