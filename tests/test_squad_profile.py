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


def test_goalkeepers_do_not_count_and_the_league_median_uses_every_rival(mezzala):
    ours = eleven()
    ours[0] = replace(ours[0], attributes={**ours[0].attributes, "pace": 1, "acceleration": 1})
    rivals = [*rival(2, {"pace": 12, "acceleration": 12}), *rival(3, {"pace": 14, "acceleration": 14}),
              *rival(4, {"pace": 20, "acceleration": 20})]  # fmt: skip
    groups = {g["group"]: g for g in mezzala(snapshot([*ours, *rivals])).result("squad_profile")["groups"]}
    assert (groups["pace"]["yours"], groups["pace"]["league_median"]) == (10.0, 14.0)


def test_small_differences_are_neither_strengths_nor_weaknesses(mezzala):
    ours = eleven(attributes={"strength": 11})
    result = mezzala(snapshot([*ours, *rival(2, {})])).result("squad_profile")
    assert {g["group"]: g["difference"] for g in result["groups"]}["physical"] == 0.2
    assert "physical" not in result["strengths"]
