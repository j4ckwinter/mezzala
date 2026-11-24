import asyncio

from mcp import Client

from mezzala.server import INSTRUCTIONS, create_server


def schemas() -> dict[str, dict]:
    async def run() -> dict[str, dict]:
        async with Client(create_server(None)) as client:  # type: ignore[arg-type]
            return {tool.name: tool.input_schema for tool in (await client.list_tools()).tools}

    return asyncio.run(run())


def test_formation_parameters_list_every_formation_in_their_description():
    for tool in ("squad_gaps", "contract_watch"):
        description = schemas()[tool]["properties"]["formation"]["description"]
        assert description == 'One of: "4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "4-4-2 diamond", "3-4-3"'


def test_position_and_scope_parameters_list_their_choices():
    risers = schemas()["risers"]["properties"]
    assert risers["scope"]["description"] == 'One of: "elsewhere", "own", "former"'
    assert '"centre back"' in risers["position"]["description"]


def test_the_instructions_state_the_position_thresholds_and_default_formation():
    assert "natural (FM rating 18+) or accomplished\n(15-17)" in INSTRUCTIONS
    assert "default to 4-3-3" in INSTRUCTIONS
