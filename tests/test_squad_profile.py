from dataclasses import replace

from factory import MY_LEAGUE, eleven, player, snapshot

SHAPE = [("gk",), ("dc",), ("dc",), ("dl",), ("dr",), ("dm",), ("mc",), ("mc",), ("aml",), ("amr",), ("stc",)]


def rival(club, attributes):
    return [
        player(f"Rival {club}-{n}", club=club, league_id=MY_LEAGUE, positions=positions, attributes=attributes)
        for n, positions in enumerate(SHAPE)
    ]


def test_strengths_and_weaknesses_are_measured_against_the_league(mezzala):
    ours = eleven(attributes={"pace": 16, "acceleration": 16, "heading": 6, "jumping_reach": 6})
    rivals = rival(2, {})
    result = mezzala(snapshot([*ours, *rivals])).result("squad_profile")
    groups = {g["group"]: g for g in result["groups"]}
    assert (groups["pace"]["yours"], groups["pace"]["league_median"], groups["pace"]["difference"]) == (16.0, 10.0, 6.0)
    assert result["strengths"][0] == "pace"
    assert result["weaknesses"][0] == "aerial"


def test_without_a_known_league_only_the_squads_own_profile_is_shown(mezzala):
    ours = [replace(p, league_id=None) for p in eleven()]
    result = mezzala(snapshot(ours)).result("squad_profile")
    assert all(g["league_median"] is None for g in result["groups"]) and result["strengths"] == []
