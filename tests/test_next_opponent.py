from datetime import date

from factory import MY_CLUB, eleven, player, snapshot

from mezzala.core.players import Match

RIVAL, OTHER = 2, 3
SHAPE = [("gk",), ("dc",), ("dc",), ("dl",), ("dr",), ("dm",), ("mc",), ("mc",), ("aml",), ("amr",), ("stc",)]


def rival_squad(attributes):
    return [
        player(f"Rival {n}", club=RIVAL, club_name="Rival FC", positions=positions, ca=110 + n, attributes=attributes)
        for n, positions in enumerate(SHAPE)
    ]


def match(day, home, away, played=False, home_goals=None, away_goals=None):
    names = {MY_CLUB: "Paisley", RIVAL: "Rival FC", OTHER: "Other FC"}
    return Match(day, 33, home, names[home], away, names[away], played, home_goals, away_goals)


def test_the_next_opponent_is_analysed(mezzala):
    fixtures = (
        match(date(2026, 8, 8), RIVAL, MY_CLUB),
        match(date(2026, 8, 1), MY_CLUB, OTHER, played=True, home_goals=2, away_goals=0),
        match(date(2026, 7, 25), RIVAL, OTHER, played=True, home_goals=1, away_goals=3),
        match(date(2026, 8, 15), MY_CLUB, OTHER),
    )
    squad = [*eleven(), *rival_squad({"pace": 17, "acceleration": 17})]
    result = mezzala(snapshot(squad, game_date=date(2026, 8, 2), matches=fixtures)).result("next_opponent")
    assert (result["date"], result["opponent"], result["venue"]) == ("2026-08-08", "Rival FC", "away")
    assert result["their_key_players"][0]["name"] == "Rival 10"
    assert len([s for s in result["their_eleven"] if s["name"]]) == 11
    pace = {g["group"]: g for g in result["attributes"]}["pace"]
    assert pace["difference"] == -7.0
    assert result["their_recent_results"] == ["2026-07-25 L 1-3 v Other FC"]


def test_no_upcoming_fixture_is_explained(mezzala):
    result = mezzala(snapshot(eleven())).result("next_opponent")
    assert result["opponent"] is None and "No upcoming" in result["explanation"]


def test_fixtures_survive_a_restart(mezzala):
    app = mezzala(snapshot(eleven(), matches=(match(date(2026, 8, 8), MY_CLUB, RIVAL),)))
    app.call("snapshot")
    assert app.another_server().result("next_opponent")["opponent"] == "Rival FC"
