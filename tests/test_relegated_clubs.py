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
