from dataclasses import replace
from datetime import date

from factory import eleven, mine, player, snapshot

from mezzala.core.players import Injury, SeasonStats
from mezzala.core.view import View

SEASON = SeasonStats(900, 10, 2, 6.9, 3, 2, 2.5, 1.5, 20, 12, 40, 8, 15, 9, 30, 1)


def scouted():
    return mine(
        "Scouted", positions=("mc", "dm"), attributes={"passing": 17, "tackling": 17, "consistency": 6, "pace": 12},
        professionalism=18, ambition=9, temperament=4, controversy=15, left_foot=8, right_foot=20, height_cm=181,
        traits=("tries killer balls often",), condition=93, match_sharpness=55, banned_from=("Scottish Cup",),
        injuries=(Injury(date(2025, 11, 2), "moderate", "in match"),), season=SEASON,
    )  # fmt: skip


def test_a_profile_groups_attributes_and_shows_what_the_save_knows_about_him(mezzala):
    result = mezzala(snapshot([*eleven(), scouted()])).result("player_profile", player="Scouted")
    profile = result["profiles"][0]
    assert profile["attributes"]["technical"]["passing"] == 17
    assert set(profile["attributes"]) == {"technical", "mental", "physical"}
    assert profile["hidden_attributes"]["consistency"] == 6
    assert profile["personality"]["temperament"] == 4 and profile["personality"]["controversy"] == 15
    assert (profile["left_foot"], profile["right_foot"], profile["height_cm"]) == (8, 20, 181)
    assert profile["traits"] == ["tries killer balls often"]
    assert profile["fitness"] == {
        "condition_percent": 93, "match_sharpness_percent": 55, "injury": None, "injured_until": None,
        "banned_from": ["Scottish Cup"], "injuries_in_the_last_two_years": ["2025-11-02: moderate, in match"],
    }  # fmt: skip
    assert profile["season"]["goals"] == 3 and profile["season"]["average_rating"] == 6.9
    scores = [fit["key_attribute_score"] for fit in profile["positions"]]
    assert {fit["position"] for fit in profile["positions"]} == {"central midfield", "defensive midfield"}
    assert scores == sorted(scores, reverse=True)


def test_a_goalkeeper_gets_goalkeeping_attributes_instead_of_technical(mezzala):
    keeper = mine("Keeper", positions=("gk",), attributes={"reflexes": 16})
    profile = mezzala(snapshot([keeper])).result("player_profile", player="Keeper")["profiles"][0]
    assert "goalkeeping" in profile["attributes"] and "technical" not in profile["attributes"]
    assert profile["attributes"]["goalkeeping"]["reflexes"] == 16


def test_fog_of_war_leaves_out_hidden_attributes_and_personality(mezzala):
    result = mezzala(snapshot([*eleven(), scouted()]), view=View.SPOILER_FREE).result(
        "player_profile", player="Scouted"
    )
    profile = result["profiles"][0]
    assert profile["hidden_attributes"] is None and profile["personality"] is None
    assert profile["player"]["current_ability"] == "2.5 stars"
    assert "consistency" not in str(profile) and "Fog of war is on" in result["explanation"]


def test_compare_with_returns_both_players_side_by_side(mezzala):
    rival = player("Rival", positions=("mc",))
    result = mezzala(snapshot([*eleven(), scouted(), rival])).result(
        "player_profile", player="Scouted", compare_with="Rival"
    )
    assert [profile["player"]["name"] for profile in result["profiles"]] == ["Scouted", "Rival"]


def test_changes_since_the_first_snapshot_list_ability_and_attributes_that_moved(mezzala):
    first = snapshot([*eleven(), scouted()])
    app = mezzala(first)
    app.call("snapshot")
    grown = replace(scouted(), uid=first.players[-1].uid, current_ability=108,
                    attributes={**first.players[-1].attributes, "passing": 18})  # fmt: skip
    app.play_to(replace(first, game_date=date(2027, 1, 10), players=(*first.players[:-1], grown)))
    result = app.result("player_profile", player="Scouted")
    assert result["compared_with"] == "2026-06-29"
    assert result["profiles"][0]["changes_since_first_snapshot"] == ["CA 100 -> 108", "passing 17 -> 18"]


def test_with_one_snapshot_there_is_nothing_to_compare(mezzala):
    result = mezzala(snapshot([*eleven(), scouted()])).result("player_profile", player="Scouted")
    assert result["compared_with"] is None and result["profiles"][0]["changes_since_first_snapshot"] == []


def test_an_unknown_player_is_reported(mezzala):
    outcome = mezzala(snapshot(eleven())).call("player_profile", player="Nobody Atall")
    assert outcome.is_error and "Nobody Atall" in outcome.text
