from dataclasses import replace
from datetime import date

from factory import OTHER_CLUB, eleven, player, snapshot

from mezzala.core.players import ReleaseClause, ReleaseScope

LATER = date(2027, 1, 15)


def entries(result):
    return {entry["name"]: entry for entry in result["players"]}


def test_a_watched_player_shows_how_he_has_changed_and_why_he_is_cheaper(mezzala):
    squad = eleven()
    target = player("Target", club=OTHER_CLUB, ca=110, value=2_000_000, contract_end=date(2029, 6, 30))
    app = mezzala(snapshot([*squad, target]))
    app.result("watch_player", player="Target", note="left back cover")
    later = replace(target, current_ability=114, value=1_200_000, contract_end=date(2027, 6, 30))
    app.play_to(snapshot([*squad, later], game_date=LATER))
    watched = entries(app.result("watchlist"))["Target"]
    assert watched["note"] == "left back cover"
    assert watched["since_added"] == ["CA 110 -> 114", "value £2.0m -> £1.2m"]
    assert watched["cheaper_because"] == ["value down from £2.0m to £1.2m", "contract ends 2027-06-30"]


def test_a_free_agent_or_an_applicable_release_clause_makes_a_target_cheaper(mezzala):
    squad = eleven()
    released = player("Released", club=OTHER_CLUB, value=1_000_000)
    clause = player("Clause", club=OTHER_CLUB, release_clauses=(ReleaseClause(ReleaseScope.ANY, 400_000, None),))
    app = mezzala(snapshot([*squad, released, clause]))
    app.result("watch_player", player="Released")
    app.result("watch_player", player="Clause")
    app.play_to(snapshot([*squad, replace(released, club_uid=None, club_name=None, value=None), clause],
                         game_date=LATER))  # fmt: skip
    watched = entries(app.result("watchlist"))
    assert "now a free agent" in watched["Released"]["cheaper_because"]
    assert watched["Clause"]["cheaper_because"] == ["release clause of £400k applies to your club"]


def test_a_player_can_be_removed_and_removing_one_not_watched_is_an_error(mezzala):
    app = mezzala(snapshot([*eleven(), player("Target", club=OTHER_CLUB)]))
    app.result("watch_player", player="Target")
    assert app.result("unwatch_player", player="Target")["players"] == []
    assert app.call("unwatch_player", player="Target").is_error


def test_the_watchlist_survives_a_restart(mezzala):
    app = mezzala(snapshot([*eleven(), player("Target", club=OTHER_CLUB)]))
    app.result("watch_player", player="Target")
    assert list(entries(app.another_server().result("watchlist"))) == ["Target"]


def test_a_player_who_has_left_the_save_is_reported(mezzala):
    squad = eleven()
    app = mezzala(snapshot([*squad, player("Veteran", club=OTHER_CLUB, age=38)]))
    app.result("watch_player", player="Veteran")
    app.play_to(snapshot(squad, game_date=LATER))
    assert entries(app.result("watchlist"))["Veteran"]["now"] is None


def test_a_new_player_given_a_watched_players_id_is_not_mistaken_for_him(mezzala):
    squad = eleven()
    veteran = player("Veteran", club=OTHER_CLUB, age=38)
    app = mezzala(snapshot([*squad, veteran]))
    app.result("watch_player", player="Veteran")
    newcomer = replace(veteran, name="Newcomer", age=15, birth_date=date(2011, 3, 3))
    app.play_to(snapshot([*squad, newcomer], game_date=LATER))
    assert entries(app.result("watchlist"))["Veteran"]["now"] is None
