import argparse
import asyncio
import json
import re
from dataclasses import replace

import pytest
from factory import eleven, mine, player, snapshot
from mcp import Client

from mezzala.__main__ import fog_of_war, parse_arguments
from mezzala.core.view import View
from mezzala.server import create_server

HIDDEN_NUMBERS = re.compile(r"\b(143|151|187)\b")
ARGUMENTS = {
    "find_replacement": {"player": "Prospect"},
    "player_profile": {"player": "Prospect", "compare_with": "Rival Target"},
    "training_plan": {"player": "Prospect"},
    "watch_player": {"player": "Rival Target"},
    "unwatch_player": {"player": "Rival Target"},
    "reject_player": {"player": "Free Man"},
    "unreject_player": {"player": "Free Man"},
}


def distinctive_save():
    squad = [replace(p, current_ability=143, potential_ability=187) for p in eleven()]
    squad.append(mine("Prospect", age=18, ca=143, pa=187, positions=("mc",)))
    rivals = [player("Rival Target", ca=151, pa=187, positions=("mc",)),
              player("Free Man", ca=151, pa=187, club=None, value=None)]  # fmt: skip
    return snapshot([*squad, *rivals])


def tool_names(mezzala_server) -> list[str]:
    async def run() -> list[str]:
        async with Client(
            create_server(mezzala_server.career, mezzala_server.watched, mezzala_server.rejections)
        ) as client:
            return [tool.name for tool in (await client.list_tools()).tools]

    return asyncio.run(run())


def every_answer(mezzala_server) -> str:
    mezzala_server.call("snapshot")
    first = distinctive_save()
    grown = tuple(replace(p, current_ability=151) if p.name == "Prospect" else p for p in first.players)
    later = replace(first, game_date=first.game_date.replace(year=2027), players=grown)
    mezzala_server.play_to(later)
    answers = []
    for name in tool_names(mezzala_server):
        outcome = mezzala_server.call(name, **ARGUMENTS.get(name, {}))
        assert not outcome.is_error, (name, outcome.text)
        answers.append(json.dumps(outcome.data))
    return "\n".join(answers)


def test_fog_of_war_never_shows_current_or_potential_ability(mezzala):
    answers = every_answer(mezzala(distinctive_save(), view=View.SPOILER_FREE))
    assert HIDDEN_NUMBERS.findall(answers) == []
    assert re.findall(r"\b(?:CA|PA) \d", answers) == []
    assert "3.5 stars" in answers


def test_without_fog_of_war_the_same_answers_show_the_numbers(mezzala):
    answers = every_answer(mezzala(distinctive_save()))
    assert "143" in answers and "187" in answers


def test_fog_of_war_tells_claude_not_to_reveal_ability_numbers(mezzala):
    server = mezzala(distinctive_save(), view=View.SPOILER_FREE)

    async def instructions() -> str:
        async with Client(create_server(server.career, server.watched, server.rejections, View.SPOILER_FREE)) as client:
            return client.instructions or ""

    assert "Fog of war is on" in asyncio.run(instructions())


def test_the_fog_of_war_switch_reads_the_words_a_settings_screen_sends():
    assert [fog_of_war(text) for text in ("true", "On", "1", "yes")] == [View.SPOILER_FREE] * 4
    assert [fog_of_war(text) for text in ("false", "off", "0", "")] == [View.FULL] * 4


def test_an_unclear_fog_of_war_switch_is_refused():
    with pytest.raises(argparse.ArgumentTypeError):
        fog_of_war("maybe")


def test_fog_of_war_is_off_unless_the_option_is_given():
    assert parse_arguments([]).fog_of_war is View.FULL
    assert parse_arguments(["--fog-of-war"]).fog_of_war is View.SPOILER_FREE
    assert parse_arguments(["--fog-of-war", "false"]).fog_of_war is View.FULL
    assert parse_arguments(["--fog-of-war", "on"]).fog_of_war is View.SPOILER_FREE


def test_stars_round_half_up_in_half_star_steps(mezzala):
    squad = [mine(f"Ability {ca}", ca=ca) for ca in (130, 150, 70, 5)]
    found = mezzala(snapshot(squad), view=View.SPOILER_FREE).result("squad")["available"]
    shown = {member["player"]["name"]: member["player"]["current_ability"] for member in found}
    assert shown == {"Ability 130": "3.5 stars", "Ability 150": "4 stars", "Ability 70": "2 stars",
                     "Ability 5": "0.5 stars"}  # fmt: skip


def test_a_profile_under_fog_of_war_mentions_ability_only_when_the_stars_move(mezzala):
    first = snapshot([*eleven(), mine("Grower", ca=143)])
    app = mezzala(first, view=View.SPOILER_FREE)
    app.call("snapshot")
    grower = first.players[-1]
    app.play_to(replace(first, game_date=first.game_date.replace(year=2027),
                        players=(*first.players[:-1], replace(grower, current_ability=145))))  # fmt: skip
    assert app.result("player_profile", player="Grower")["profiles"][0]["changes_since_first_snapshot"] == []
    app.play_to(replace(first, game_date=first.game_date.replace(year=2028),
                        players=(*first.players[:-1], replace(grower, current_ability=152))))  # fmt: skip
    changes = app.result("player_profile", player="Grower")["profiles"][0]["changes_since_first_snapshot"]
    assert changes == ["3.5 stars -> 4 stars"]


def test_fog_of_war_refuses_filters_that_would_reveal_hidden_ability(mezzala):
    app = mezzala(distinctive_save(), view=View.SPOILER_FREE)
    refused = [("find_players", {"min_pa": 187}), ("find_players", {"max_ca": 150}), ("find_players", {"min_ca": 151}),
               ("development_check", {"min_pa": 160}), ("regen_intake", {"min_pa": 140}), ("risers", {"min_ca": 120}),
               ("risers", {"min_ca_gain": 5})]  # fmt: skip
    for tool, arguments in refused:
        outcome = app.call(tool, **arguments)
        assert outcome.is_error and "Fog of war is on" in outcome.text, (tool, arguments)


def test_without_fog_of_war_the_ability_filters_work(mezzala):
    assert mezzala(distinctive_save()).result("find_players", min_pa=187, within_reach=False)["matched"] == 2


def test_fog_of_war_judges_injury_risk_only_on_injuries_the_game_shows(mezzala):
    squad = eleven()
    squad[1] = replace(squad[1], attributes={**squad[1].attributes, "injury_proneness": 18})
    kid = mine("Prone Kid", age=19, attributes={"injury_proneness": 18, "natural_fitness": 15})
    fogged = mezzala(snapshot([*squad, kid]), view=View.SPOILER_FREE)
    fitness = fogged.result("fitness")
    assert fitness["injury_risks_in_the_eleven"] == [] and "prone" not in fitness["explanation"]
    assert fogged.result("training_plan", player="Prone Kid")["why_this_intensity"] == []
    assert mezzala(snapshot(squad)).result("fitness")["injury_risks_in_the_eleven"] != []


def test_fog_of_war_compares_ratings_within_his_league_not_his_hidden_ability(mezzala):
    from mezzala.core.players import SeasonStats

    def played(rating):
        return SeasonStats(900, 10, 0, rating, 0, 0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, None, 0)

    league_mates = [player(f"Mate {n}", ca=60 + 8 * n, season=played(6.6)) for n in range(10)]
    elsewhere = [player(f"Abroad {n}", ca=100, league_id=99, season=played(7.2)) for n in range(10)]
    star = mine("Star", ca=100, season=played(7.4))
    save = snapshot([*eleven(), star, *league_mates, *elsewhere])
    fogged = mezzala(save, view=View.SPOILER_FREE).result("performance")
    assert fogged["players"][0]["rating_above_similar_players"] == 0.8
    assert "fog of war hides ability" in fogged["explanation"]
    assert mezzala(save).result("performance")["players"][0]["rating_above_similar_players"] == 0.2


def test_compact_rows_use_stars_under_fog_of_war(mezzala):
    rows = mezzala(distinctive_save(), view=View.SPOILER_FREE).result("find_players", compact=True, within_reach=False)
    assert {row["current_ability"] for row in rows["compact_players"]} == {"4 stars"}
