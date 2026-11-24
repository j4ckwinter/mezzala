from datetime import date

from factory import eleven, mine, snapshot


def gaps_by_group(app, **arguments):
    positions = app.result("squad_gaps", **arguments)["positions"]
    return {position["group"]: position["issues"] for position in positions if position["issues"]}


def test_a_full_young_squad_with_cover_has_no_gaps(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    assert gaps_by_group(mezzala(snapshot(squad))) == {}


def test_a_position_without_enough_players_is_thin(mezzala):
    squad = eleven(age=22, pa=130) + [p for p in eleven(age=21, pa=130) if p.position_ratings["stc"] != 20]
    issues = gaps_by_group(mezzala(snapshot(squad)))["striker"]
    assert "thin: 1 of 2 players who can play here" in issues


def test_an_ageing_starter_and_an_ending_contract_are_flagged(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad.append(mine("Old Keeper", positions=("gk",), age=31, ca=150, contract_end=date(2027, 5, 31)))
    issues = gaps_by_group(mezzala(snapshot(squad)))["goalkeeper"]
    assert "ageing: Old Keeper is 31, 33 in two seasons" in issues
    assert "leaving: Old Keeper's contract ends 2027-05-31" in issues


def test_a_starter_on_loan_is_flagged_as_leaving(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad.append(mine("Loanee", positions=("dr",), ca=150, on_loan=True, loan_parent_club_uid=9,
                      loan_end=date(2027, 5, 31)))  # fmt: skip
    issues = gaps_by_group(mezzala(snapshot(squad)))["right back"]
    assert "leaving: Loanee's loan ends 2027-05-31" in issues


def test_a_position_with_no_young_successor_is_flagged(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad = [p for p in squad if p.position_ratings["stc"] != 20]
    squad += [mine("Striker", positions=("stc",), age=26, ca=100), mine("Backup", positions=("stc",), age=27, ca=90)]
    issues = gaps_by_group(mezzala(snapshot(squad)))["striker"]
    assert issues == ["no successor: nobody 23 or under can reach Striker's level"]


def test_each_player_starts_in_only_one_position(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad.append(mine("Utility", positions=("dc", "dm", "mc"), age=33, ca=160))
    gaps = gaps_by_group(mezzala(snapshot(squad)))
    flagged = [group for group, issues in gaps.items() if any("Utility" in issue for issue in issues)]
    assert flagged == ["centre back"]


def test_formation_changes_how_many_starters_a_position_needs(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    gaps = gaps_by_group(mezzala(snapshot(squad)), formation="4-4-2")
    assert "thin: 2 of 4 players who can play here" in gaps["striker"]
    assert "striker" not in gaps_by_group(mezzala(snapshot(squad)), formation="4-3-3")


def test_a_diamond_needs_an_attacking_midfielder_and_two_strikers(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    gaps = gaps_by_group(mezzala(snapshot(squad)), formation="4-4-2 diamond")
    assert "thin: 0 of 2 players who can play here" in gaps["attacking midfield"]
    assert "thin: 2 of 4 players who can play here" in gaps["striker"]


def test_the_eleven_is_returned_with_each_player_once_and_how_well_he_fits(mezzala):
    squad = eleven(age=22, pa=130)
    squad.append(mine("Makeshift", positions=("dc", "dm"), ca=160))
    squad[5] = mine("Natural DM", positions=("dm",), ca=90)
    result = mezzala(snapshot(squad)).result("squad_gaps")
    names = [starter["name"] for starter in result["eleven"]]
    assert len(names) == 11 and len(set(names)) == 11
    by_name = {starter["name"]: (starter["position"], starter["fit"]) for starter in result["eleven"]}
    assert by_name["Makeshift"] == ("centre back", "natural")
    assert by_name["Natural DM"] == ("defensive midfield", "natural")


def test_an_empty_place_in_the_eleven_is_shown_as_nobody(mezzala):
    squad = [p for p in eleven() if p.position_ratings["gk"] != 20]
    starters = mezzala(snapshot(squad)).result("squad_gaps")["eleven"]
    assert {"position": "goalkeeper", "name": None, "age": None, "current_ability": None, "fit": None} in starters


def test_covered_positions_still_list_their_depth_with_fit(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad.append(
        mine("Accomplished Keeper", positions=(), ca=60, position_ratings={**squad[0].position_ratings, "gk": 15})
    )
    positions = {p["group"]: p for p in mezzala(snapshot(squad)).result("squad_gaps")["positions"]}
    keeper = positions["goalkeeper"]
    assert keeper["issues"] == []
    assert [(d["name"], d["fit"], d["starts_here"]) for d in keeper["depth"]][-1] == (
        "Accomplished Keeper",
        "accomplished",
        False,
    )
    assert sum(d["starts_here"] for d in keeper["depth"]) == 1
