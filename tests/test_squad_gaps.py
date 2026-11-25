from dataclasses import replace
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
    assert by_name["Makeshift"] == ("defensive midfield", "natural")
    assert "Natural DM" not in by_name


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


def test_a_starting_place_nobody_can_fill_is_reported(mezzala):
    squad = [p for p in eleven() if p.position_ratings["gk"] != 20]
    issues = gaps_by_group(mezzala(snapshot(squad)))["goalkeeper"]
    assert "empty: 1 of 1 starting places with nobody to fill them" in issues


def test_each_issue_is_labelled_with_its_kind(mezzala):
    squad = eleven(age=22, pa=130) + eleven(age=21, pa=130)
    squad.append(mine("Old Keeper", positions=("gk",), age=31, ca=150, contract_end=date(2027, 5, 31)))
    keeper = {p["group"]: p for p in mezzala(snapshot(squad)).result("squad_gaps")["positions"]}["goalkeeper"]
    assert keeper["issue_kinds"] == ["ageing", "leaving", "no successor"]


def test_a_starter_who_is_not_a_natural_in_his_place_is_flagged(mezzala):
    squad = [p for p in eleven() if p.position_ratings["amr"] != 20]
    ramos = mine("Ramos", positions=("aml",), ca=100)
    squad.append(replace(ramos, position_ratings={**ramos.position_ratings, "amr": 16}))
    right = next(p for p in mezzala(snapshot(squad)).result("squad_gaps")["positions"] if p["group"] == "right wing")
    assert "out of position" in right["issue_kinds"]
    assert "out of position: Ramos is not a natural here and plays 5 below his level" in right["issues"]


def test_an_out_of_position_starter_close_to_the_median_is_not_also_called_weak(mezzala):
    squad = [replace(p, current_ability=120) for p in eleven() if p.position_ratings["dc"] != 20]
    squad.append(mine("Natural", positions=("dc",), ca=120))
    stretched = mine("Stretched", positions=("dl",), ca=116)
    squad.append(replace(stretched, position_ratings={**stretched.position_ratings, "dc": 15}))
    squad.append(mine("Left Back", positions=("dl",), ca=121))
    centre = next(p for p in mezzala(snapshot(squad)).result("squad_gaps")["positions"] if p["group"] == "centre back")
    assert "out of position" in centre["issue_kinds"] and "weak" not in centre["issue_kinds"]
