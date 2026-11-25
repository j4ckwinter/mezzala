import argparse
import asyncio
import json
import re
from dataclasses import replace

import pytest
from factory import eleven, mine, player, snapshot
from mcp import Client

from mezzala.__main__ import fog_of_war
from mezzala.core.view import View
from mezzala.server import create_server

HIDDEN_NUMBERS = re.compile(r"\b(143|151|187)\b")
ARGUMENTS = {
    "find_replacement": {"player": "Prospect"},
    "player_profile": {"player": "Prospect", "compare_with": "Rival Target"},
    "watch_player": {"player": "Rival Target"},
    "unwatch_player": {"player": "Rival Target"},
}


def distinctive_save():
    squad = [replace(p, current_ability=143, potential_ability=187) for p in eleven()]
    squad.append(mine("Prospect", age=18, ca=143, pa=187, positions=("mc",)))
    rivals = [player("Rival Target", ca=151, pa=187, positions=("mc",)),
              player("Free Man", ca=151, pa=187, club=None, value=None)]  # fmt: skip
    return snapshot([*squad, *rivals])


def tool_names(mezzala_server) -> list[str]:
    async def run() -> list[str]:
        async with Client(create_server(mezzala_server.career, mezzala_server.watched)) as client:
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
        async with Client(create_server(server.career, server.watched, View.SPOILER_FREE)) as client:
            return client.instructions or ""

    assert "Fog of war is on" in asyncio.run(instructions())


def test_the_fog_of_war_switch_reads_the_words_a_settings_screen_sends():
    assert [fog_of_war(text) for text in ("true", "On", "1", "yes")] == [View.SPOILER_FREE] * 4
    assert [fog_of_war(text) for text in ("false", "off", "0", "")] == [View.FULL] * 4


def test_an_unclear_fog_of_war_switch_is_refused():
    with pytest.raises(argparse.ArgumentTypeError):
        fog_of_war("maybe")
