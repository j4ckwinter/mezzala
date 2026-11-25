from dataclasses import replace
from datetime import date

from factory import eleven, player, snapshot

TOP, SECOND = 80, 81


def league_of(name, league, value, count=60, ca=110, reputation=5_000):
    return [
        player(f"{name} {n}", club=100 + league * 10 + n % 5, club_name=f"{name} FC {n % 5}", league_id=league,
               ca=ca, age=26, pa=120, value=value, club_reputation=reputation - n % 5)
        for n in range(count)
    ]  # fmt: skip


def test_a_club_that_drops_to_a_weaker_league_is_relegated(mezzala):
    top = league_of("Top", TOP, 1_000_000, ca=130)
    second = league_of("Second", SECOND, 300_000, ca=100)
    faller = [player(f"Faller {n}", club=999, club_name="Faller FC", league_id=TOP, ca=125) for n in range(3)]
    app = mezzala(snapshot([*eleven(), *top, *second, *faller]))
    app.call("snapshot")
    fallen = [replace(p, league_id=SECOND) for p in faller]
    app.play_to(snapshot([*eleven(), *top, *second, *fallen], game_date=date(2027, 7, 1)))
    clubs = app.result("relegated_clubs")["clubs"]
    assert [(club["club"], len(club["players_worth_a_look"])) for club in clubs] == [("Faller FC", 3)]


def test_relegation_needs_an_earlier_snapshot(mezzala):
    result = mezzala(snapshot(eleven())).result("relegated_clubs")
    assert result["clubs"] == [] and "before the season changed" in result["explanation"]


def test_a_promoted_club_is_not_relegated(mezzala):
    top = league_of("Top", TOP, 1_000_000, ca=130)
    second = league_of("Second", SECOND, 300_000, ca=100)
    climber = [player(f"Climber {n}", club=998, club_name="Climber FC", league_id=SECOND, ca=105) for n in range(3)]
    app = mezzala(snapshot([*eleven(), *top, *second, *climber]))
    app.call("snapshot")
    risen = [replace(p, league_id=TOP) for p in climber]
    app.play_to(snapshot([*eleven(), *top, *second, *risen], game_date=date(2027, 7, 1)))
    assert app.result("relegated_clubs")["clubs"] == []


def test_players_out_of_reach_are_not_suggested(mezzala):
    top = league_of("Top", TOP, 1_000_000, ca=130)
    second = league_of("Second", SECOND, 300_000, ca=100)
    faller = [player("Star", club=999, club_name="Faller FC", league_id=TOP, ca=150, reputation=9_000),
              player("Gettable", club=999, club_name="Faller FC", league_id=TOP, ca=120)]  # fmt: skip
    app = mezzala(snapshot([*eleven(), *top, *second, *faller]))
    app.call("snapshot")
    app.play_to(snapshot([*eleven(), *top, *second, *[replace(p, league_id=SECOND) for p in faller]],
                         game_date=date(2027, 7, 1)))  # fmt: skip
    clubs = app.result("relegated_clubs")["clubs"]
    assert [p["name"] for p in clubs[0]["players_worth_a_look"]] == ["Gettable"]


def test_an_earlier_snapshot_without_leagues_is_explained(mezzala):
    squad = eleven()
    app = mezzala(snapshot([replace(p, league_id=None) for p in squad]))
    app.call("snapshot")
    app.play_to(snapshot(squad, game_date=date(2027, 7, 1)))
    result = app.result("relegated_clubs")
    assert result["clubs"] == [] and "before mezzala recorded leagues" in result["explanation"]
