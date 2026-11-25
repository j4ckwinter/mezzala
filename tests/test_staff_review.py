from dataclasses import replace

from factory import eleven, snapshot

from mezzala.core.players import StaffMember

COACH = StaffMember("Attack Coach", "coach", 44, {"attacking": 15, "defending": 9, "tactical": 12})
DEFENCE = StaffMember("Defence Coach", "assistant manager", 50, {"attacking": 10, "defending": 16})
SCOUT = StaffMember("Chief Scout", "chief scout", 39, {"judging_player_ability": 13, "judging_player_potential": 14})
PHYSIO = StaffMember("Physio", "head physio", 36, {"physiotherapy": 15, "sports_science": 8})
CHAIRMAN = StaffMember("Chairman", "chairperson", 70, {"attacking": 20, "judging_player_ability": 20})


def review(mezzala, *staff):
    return mezzala(replace(snapshot(eleven()), staff=staff)).result("staff_review")


def test_each_area_shows_the_best_rating_in_that_part_of_the_staff(mezzala):
    result = review(mezzala, COACH, DEFENCE, SCOUT, PHYSIO, CHAIRMAN)
    coaching = {area["area"]: (area["best"], area["by"]) for area in result["coaching"]}
    assert coaching["attacking"] == (15, "Attack Coach") and coaching["defending"] == (16, "Defence Coach")
    assert result["scouting"][1] == {"area": "judging player potential", "best": 14, "by": "Chief Scout"}
    assert result["medical"][0] == {"area": "physiotherapy", "best": 15, "by": "Physio"}


def test_board_members_do_not_count_as_coaches_or_scouts(mezzala):
    result = review(mezzala, CHAIRMAN)
    assert all(area["best"] is None for area in result["coaching"] + result["scouting"])


def test_coaching_areas_with_nobody_good_enough_are_flagged(mezzala):
    weak = review(mezzala, COACH, DEFENCE)["weak_coaching_areas"]
    assert "attacking" not in weak and "tactical" not in weak and "defending" not in weak
    assert "fitness" in weak and "goalkeeping" in weak


def test_every_staff_member_is_listed_with_their_job(mezzala):
    staff = review(mezzala, COACH, SCOUT)["staff"]
    assert staff == [
        {"name": "Attack Coach", "job": "coach", "age": 44},
        {"name": "Chief Scout", "job": "chief scout", "age": 39},
    ]
