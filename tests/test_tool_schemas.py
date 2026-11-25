import asyncio

from mcp import Client

from mezzala.server import INSTRUCTIONS, create_server


def schemas() -> dict[str, dict]:
    async def run() -> dict[str, dict]:
        async with Client(create_server(None, None, None)) as client:  # type: ignore[arg-type]
            return {tool.name: tool.input_schema for tool in (await client.list_tools()).tools}

    return asyncio.run(run())


def test_formation_parameters_list_every_formation_in_their_description():
    for tool in ("squad_gaps", "contract_watch"):
        description = schemas()[tool]["properties"]["formation"]["description"]
        assert description == (
            "Defaults to the saved first-team tactic's shape, else 4-3-3. "
            'One of: "4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "4-4-2 diamond", "3-4-3"'
        )


def test_position_and_scope_parameters_list_their_choices():
    risers = schemas()["risers"]["properties"]
    assert risers["scope"]["description"] == 'One of: "elsewhere", "own", "former"'
    assert '"centre back"' in risers["position"]["description"]


def test_the_instructions_state_the_position_thresholds_and_default_formation():
    assert "natural (FM rating 18+) or accomplished\n(15-17)" in INSTRUCTIONS
    assert "saved in the game, and to\n4-3-3 when no saved tactic can be read" in INSTRUCTIONS


def test_find_players_states_the_reach_rule_with_its_number():
    async def run() -> str:
        async with Client(create_server(None, None, None)) as client:  # type: ignore[arg-type]
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            return tools["find_players"].description or ""

    assert "at most your club's plus 750" in asyncio.run(run())


def test_every_club_parameter_explains_it_is_only_for_telling_players_apart():
    for tool, parameter in (("find_replacement", "club"), ("player_profile", "compare_club"), ("training_plan", "club"),
                            ("watch_player", "club")):  # fmt: skip
        description = schemas()[tool]["properties"][parameter]["description"]
        assert description.startswith("The club the player is at now, to tell apart players who share a name")
