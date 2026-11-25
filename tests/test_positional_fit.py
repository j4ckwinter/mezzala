from dataclasses import replace

from factory import eleven, mine, snapshot

WINGER_ATTRIBUTES = {"crossing": 17, "dribbling": 17, "pace": 17, "acceleration": 17, "technique": 16, "flair": 16,
                     "off_the_ball": 15, "agility": 15, "finishing": 8, "composure": 8}  # fmt: skip


def test_a_starter_whose_attributes_suit_another_position_is_flagged(mezzala):
    squad = [p for p in eleven() if p.position_ratings["stc"] != 20]
    striker = mine("Winger Up Front", positions=("stc",), ca=130, attributes=WINGER_ATTRIBUTES)
    striker = replace(striker, position_ratings={**striker.position_ratings, "aml": 16})
    result = mezzala(snapshot([*squad, striker])).result("positional_fit")
    assert result["misplaced"] == ["Winger Up Front: picked at striker (11.9) but better suited to left wing (16.2)"]


def test_a_well_placed_eleven_has_nobody_misplaced(mezzala):
    result = mezzala(snapshot(eleven())).result("positional_fit")
    assert result["misplaced"] == [] and len(result["starters"]) == 11


def test_a_position_he_cannot_play_does_not_count(mezzala):
    squad = [p for p in eleven() if p.position_ratings["stc"] != 20]
    squad.append(mine("Winger Up Front", positions=("stc",), ca=130, attributes=WINGER_ATTRIBUTES))
    assert mezzala(snapshot(squad)).result("positional_fit")["misplaced"] == []
