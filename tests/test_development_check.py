from dataclasses import replace
from datetime import date

from factory import OTHER_CLUB, eleven, mine, player, snapshot

A_SEASON_LATER = date(2027, 6, 29)


def check(app, **arguments):
    return app.result("development_check", **arguments)


def named(entries):
    return [entry["player"]["name"] for entry in entries]


def test_a_wonderkid_gaining_far_less_than_projected_is_flagged(mezzala):
    squad = eleven()
    stalled = mine("Stalled", age=17, ca=80, pa=170)
    thriving = mine("Thriving", age=17, ca=80, pa=170)
    app = mezzala(snapshot([*squad, stalled, thriving]))
    app.call("snapshot")
    app.play_to(snapshot([*squad, replace(stalled, current_ability=82, age=18),
                          replace(thriving, current_ability=105, age=18)], game_date=A_SEASON_LATER))  # fmt: skip
    result = check(app)
    assert named(result["not_developing"]) == ["Stalled"]
    assert result["not_developing"][0]["ability_change"] == 2


def test_players_losing_ability_are_declining(mezzala):
    squad = eleven()
    fading = mine("Fading", age=33, ca=120, pa=120)
    app = mezzala(snapshot([*squad, fading]))
    app.call("snapshot")
    app.play_to(snapshot([*squad, replace(fading, current_ability=112, age=34)], game_date=A_SEASON_LATER))
    assert [(e["player"]["name"], e["ability_change"]) for e in check(app)["declining"]] == [("Fading", -8)]


def test_own_scope_leaves_out_other_clubs_unless_everyone_is_asked(mezzala):
    squad = eleven()
    elsewhere = player("Elsewhere Kid", club=OTHER_CLUB, age=17, ca=80, pa=170)
    app = mezzala(snapshot([*squad, elsewhere]))
    app.call("snapshot")
    app.play_to(snapshot([*squad, replace(elsewhere, age=18)], game_date=A_SEASON_LATER))
    assert check(app)["not_developing"] == []
    assert named(check(app, scope="everyone")["not_developing"]) == ["Elsewhere Kid"]


def test_too_little_time_between_snapshots_is_explained(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    app.play_to(snapshot(squad, game_date=date(2026, 8, 1)))
    result = check(app)
    assert result["compared_with"] is None and "at least 90 days" in result["explanation"]


def test_over_several_seasons_the_expectation_never_exceeds_headroom(mezzala):
    squad = eleven()
    kid = mine("Kid", age=17, ca=80, pa=170, professionalism=20, ambition=20, attributes={"determination": 20})
    app = mezzala(snapshot([*squad, kid]))
    app.call("snapshot")
    app.play_to(snapshot([*squad, replace(kid, current_ability=120, age=20)], game_date=date(2029, 6, 29)))
    assert check(app)["not_developing"] == []


def test_the_too_soon_message_names_the_snapshot_it_compared_with(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    app.play_to(snapshot(squad, game_date=date(2027, 1, 1)))
    app.play_to(snapshot(squad, game_date=date(2027, 2, 1)))
    result = check(app, since="2027-01-10")
    assert "(2027-01-01) is only 31 days earlier" in result["explanation"]
