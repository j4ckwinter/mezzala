from dataclasses import replace
from datetime import date

from factory import eleven, mine, player, snapshot

from mezzala.core.players import Injury, MentoringGroup


def plan(mezzala, *extra, **arguments):
    return mezzala(snapshot([*eleven(), *extra])).result("training_plan", **arguments)


def test_he_trains_for_the_position_his_key_attributes_suit_best(mezzala):
    youngster = mine("Youngster", age=19, positions=("mc",), attributes={"tackling": 16, "positioning": 16})
    youngster = replace(youngster, position_ratings={**youngster.position_ratings, "dm": 16})
    result = plan(mezzala, youngster, player="Youngster")
    assert (result["train_for"], result["fit_there"]) == ("defensive midfield", "accomplished")


def test_a_position_asked_for_is_used_instead(mezzala):
    youngster = mine("Youngster", age=19, positions=("mc", "dm"), attributes={"tackling": 16, "positioning": 16})
    assert plan(mezzala, youngster, player="Youngster", position="central midfield")["train_for"] == "central midfield"


def test_the_additional_focus_is_his_weakest_key_attributes_with_room_to_grow(mezzala):
    striker = mine("Striker", positions=("stc",), attributes={
        "finishing": 20, "off_the_ball": 15, "composure": 6, "first_touch": 15, "anticipation": 15, "pace": 15,
        "acceleration": 15, "heading": 8})  # fmt: skip
    focus = plan(mezzala, striker, player="Striker")["additional_focus"]
    assert focus == [{"attribute": "composure", "now": 6}, {"attribute": "heading", "now": 8},
                     {"attribute": "off the ball", "now": 15}]  # fmt: skip


def test_key_attributes_already_at_twenty_are_never_the_focus(mezzala):
    names = ("finishing", "off_the_ball", "first_touch", "anticipation", "pace", "acceleration", "heading")
    striker = mine("Complete", positions=("stc",), attributes={**dict.fromkeys(names, 20), "composure": 18})
    assert plan(mezzala, striker, player="Complete")["additional_focus"] == [{"attribute": "composure", "now": 18}]


def test_an_injury_prone_veteran_trains_at_lower_intensity(mezzala):
    injuries = (Injury(date(2025, 9, 1), "minor", "in match"), Injury(date(2026, 2, 1), "major", None))
    veteran = mine("Veteran", age=32, positions=("dc",), attributes={"injury_proneness": 15, "natural_fitness": 15},
                   injuries=injuries)  # fmt: skip
    result = plan(mezzala, veteran, player="Veteran")
    assert result["intensity"] == "lower intensity"
    assert result["why_this_intensity"] == ["he is prone to injury", "he is 32", "2 injuries in the last two years"]


def test_low_natural_fitness_alone_lowers_his_intensity(mezzala):
    result = plan(mezzala, mine("Unfit", age=22, attributes={"natural_fitness": 10}), player="Unfit")
    assert result["why_this_intensity"] == ["his natural fitness is low"]


def test_a_fit_young_player_trains_at_normal_intensity(mezzala):
    result = plan(mezzala, mine("Fit", age=20, attributes={"natural_fitness": 15}), player="Fit")
    assert (result["intensity"], result["why_this_intensity"]) == ("normal intensity", [])


def test_traits_he_lacks_the_attributes_for_are_to_unlearn_and_fitting_ones_to_learn(mezzala):
    playmaker = mine("Playmaker", positions=("mc",), traits=("shoots from distance", "tries killer balls often"),
                     attributes={"long_shots": 9, "passing": 17, "vision": 16, "decisions": 15})  # fmt: skip
    result = plan(mezzala, playmaker, player="Playmaker")
    assert result["traits_to_unlearn"] == ["shoots from distance (needs better long shots)"]
    assert result["traits_to_learn"] == ["dictates tempo"]


def test_a_young_player_is_offered_professional_seniors_as_mentors(mezzala):
    pro = mine("Old Pro", age=30, positions=("mc",), professionalism=18, attributes={"determination": 17})
    lazy = mine("Lazy Senior", age=31, positions=("mc",), professionalism=6, attributes={"determination": 17})
    result = plan(mezzala, pro, lazy, mine("Kid", age=18, positions=("mc",)), player="Kid")
    assert result["suggested_mentors"] == ["Old Pro"]


def test_an_established_player_gets_no_mentor_suggestions(mezzala):
    pro = mine("Old Pro", age=30, positions=("mc",), professionalism=18, attributes={"determination": 17})
    assert plan(mezzala, pro, mine("Grown Up", age=27, positions=("mc",)), player="Grown Up")["suggested_mentors"] == []


def test_his_current_mentoring_group_is_listed(mezzala):
    kid, pro = mine("Kid", age=18), mine("Old Pro", age=30)
    save = replace(snapshot([*eleven(), kid, pro]), mentoring=(MentoringGroup("Group 1", (pro.uid, kid.uid)),))
    assert mezzala(save).result("training_plan", player="Kid")["current_mentoring_group"] == ["Old Pro"]


def test_a_player_at_another_club_gets_no_plan(mezzala):
    outcome = mezzala(snapshot([*eleven(), player("Elsewhere")])).call("training_plan", player="Elsewhere")
    assert outcome.is_error and "is not at Paisley" in outcome.text
