from dataclasses import replace
from datetime import date

from factory import OTHER_CLUB, eleven, mine, player, snapshot

LATER = date(2027, 1, 15)


def risers(app, **arguments):
    return app.result("risers", **arguments)


def test_with_one_snapshot_gains_are_projected_from_headroom(mezzala):
    raw = player("Raw", age=17, ca=90, pa=160, professionalism=18, ambition=18)
    finished = player("Finished", age=29, ca=120, pa=121)
    report = risers(mezzala(snapshot([*eleven(), raw, finished])))
    assert report["basis"] == "projected"
    assert [entry["player"]["name"] for entry in report["risers"]] == ["Raw"]
    assert report["risers"][0]["ability_gain"] > 20


def test_players_far_below_the_first_eleven_are_left_out_by_default(mezzala):
    kid = player("Kid", age=16, ca=40, pa=170)
    report = risers(mezzala(snapshot([*eleven(ca=100), kid])))
    assert report["risers"] == []
    assert [entry["player"]["name"] for entry in risers(mezzala(snapshot([*eleven(), kid])), min_ca=0)["risers"]] == [
        "Kid"
    ]


def test_with_two_snapshots_gains_are_observed(mezzala):
    climber = player("Climber", age=20, ca=95, pa=140)
    steady = player("Steady", age=20, ca=95, pa=140)
    app = mezzala(snapshot([*eleven(), climber, steady]))
    app.call("snapshot")
    app.play_to(snapshot([*eleven(), replace(climber, current_ability=109), replace(steady, current_ability=96)],
                         game_date=LATER))  # fmt: skip
    report = risers(app)
    assert report["basis"] == "observed"
    assert report["compared_with"] == "2026-06-29"
    assert [(entry["player"]["name"], entry["ability_gain"]) for entry in report["risers"]] == [("Climber", 14.0)]


def test_former_players_who_kept_improving_after_leaving(mezzala):
    sold = mine("Sold Too Soon", age=19, ca=90, pa=150)
    app = mezzala(snapshot([*eleven(), sold]))
    app.call("snapshot")
    moved = replace(sold, club_uid=OTHER_CLUB, club_name="Club 2", current_ability=110, value=4_000_000)
    app.play_to(snapshot([*eleven(), moved], game_date=LATER))
    report = risers(app, scope="former")
    assert [entry["player"]["name"] for entry in report["risers"]] == ["Sold Too Soon"]
    assert report["risers"][0]["value_change"] == "+£3.5m"


def test_a_reused_id_is_not_counted_as_growth(mezzala):
    retired = player("Retired", age=34, ca=100, pa=100)
    app = mezzala(snapshot([*eleven(), retired]))
    app.call("snapshot")
    newcomer = replace(retired, name="Newcomer", age=16, birth_date=date(2010, 1, 1), current_ability=110)
    app.play_to(snapshot([*eleven(), newcomer], game_date=LATER))
    assert risers(app)["risers"] == []
