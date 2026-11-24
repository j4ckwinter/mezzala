from datetime import date

from factory import eleven, mine, snapshot


def gaps_by_group(app, **arguments):
    return {gap["group"]: gap["issues"] for gap in app.result("squad_gaps", **arguments)["gaps"]}


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
