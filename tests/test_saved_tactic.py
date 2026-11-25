from dataclasses import replace

from factory import eleven, mine, snapshot

from mezzala.core.players import Tactic

FOUR_FOUR_TWO = ("gk", "dl", "dc", "dc", "dr", "ml", "mc", "mc", "mr", "stc", "stc")
WITH_WING_BACKS = ("gk", None, "dc", "dc", "dc", None, "mc", "mc", "dm", "stc", "stc")


def squad_with(*tactics):
    strikers = [mine("Second Striker", positions=("stc",)), mine("Wide Man", positions=("ml", "mr"))]
    return replace(snapshot([*eleven(), *strikers]), tactics=tactics)


def test_tools_use_the_shape_of_the_saved_tactic_and_say_so(mezzala):
    outcome = mezzala(squad_with(Tactic("Route One", "balanced", FOUR_FOUR_TWO))).call("squad_gaps")
    assert outcome.data["result"]["formation"] == "4-4-2"
    assert "Formation 4-4-2, from your saved tactic 'Route One'." in outcome.data["context"]["notes"]


def test_a_formation_asked_for_beats_the_saved_tactic(mezzala):
    app = mezzala(squad_with(Tactic("Route One", "balanced", FOUR_FOUR_TWO)))
    outcome = app.call("squad_gaps", formation="4-2-3-1")
    assert outcome.data["result"]["formation"] == "4-2-3-1"
    assert not any("saved tactic" in note for note in outcome.data["context"]["notes"])


def test_a_tactic_with_positions_fmsave_cannot_name_falls_back_to_the_default_and_says_so(mezzala):
    outcome = mezzala(squad_with(Tactic("Wing Backs", "positive", WITH_WING_BACKS))).call("squad_gaps")
    assert outcome.data["result"]["formation"] == "4-3-3"
    assert outcome.data["context"]["notes"] == [
        "Your saved tactic 'Wing Backs' has a shape mezzala does not model, so 4-3-3 is used; say which formation "
        "you play for a closer answer."
    ]


def test_a_four_two_three_one_with_two_central_midfielders_is_recognised(mezzala):
    double_pivot = ("gk", "dl", "dc", "dc", "dr", "mc", "mc", "aml", "amc", "amr", "stc")
    outcome = mezzala(squad_with(Tactic("Double Pivot", "balanced", double_pivot))).call("squad_gaps")
    assert outcome.data["result"]["formation"] == "4-2-3-1"


def test_a_three_man_midfield_with_two_holders_is_still_four_three_three(mezzala):
    two_holders = ("gk", "dl", "dc", "dc", "dr", "dm", "dm", "mc", "aml", "amr", "stc")
    assert mezzala(squad_with(Tactic("Holders", "cautious", two_holders))).result("squad_gaps")["formation"] == "4-3-3"


def test_the_first_readable_saved_tactic_is_used(mezzala):
    tactics = (Tactic("Wing Backs", "positive", WITH_WING_BACKS), Tactic("Route One", "balanced", FOUR_FOUR_TWO))
    assert mezzala(squad_with(*tactics)).result("wage_review")["formation"] == "4-4-2"


def test_without_a_saved_tactic_tools_use_four_three_three(mezzala):
    assert mezzala(squad_with()).result("squad_profile")["formation"] == "4-3-3"
