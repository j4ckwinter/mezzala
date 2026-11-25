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


def test_a_player_who_has_left_the_save_can_still_be_unwatched(mezzala):
    squad = eleven()
    app = mezzala(snapshot([*squad, player("Veteran", club=OTHER_CLUB, age=38)]))
    app.result("watch_player", player="Veteran")
    app.play_to(snapshot(squad, game_date=LATER))
    assert app.result("unwatch_player", player="Veteran")["players"] == []


def test_players_who_share_a_name_are_told_apart_by_club(mezzala):
    squad = [
        *eleven(),
        player("João Silva", club=2, club_name="Porto B"),
        player("João Silva", club=3, club_name="Braga"),
    ]
    app = mezzala(snapshot(squad))
    assert app.call("watch_player", player="João Silva").is_error
    watched = app.result("watch_player", player="João Silva", club="braga")["players"]
    assert [(w["name"], w["now"]["club"]) for w in watched] == [("João Silva", "Braga")]


def test_watching_a_player_again_keeps_his_baseline_and_updates_the_note(mezzala):
    squad = eleven()
    target = player("Target", club=OTHER_CLUB, value=2_000_000)
    app = mezzala(snapshot([*squad, target]))
    app.result("watch_player", player="Target", note="first look")
    app.play_to(snapshot([*squad, replace(target, value=1_000_000)], game_date=LATER))
    watched = entries(app.result("watch_player", player="Target", note="still keen"))["Target"]
    assert watched["note"] == "still keen"
    assert watched["added_on"] == "2026-06-29"
    assert "value down from £2.0m to £1.0m" in watched["cheaper_because"]


def test_a_player_who_was_already_a_free_agent_is_not_newly_free(mezzala):
    app = mezzala(snapshot([*eleven(), player("Free", club=None, value=None)]))
    watched = entries(app.result("watch_player", player="Free"))["Free"]
    assert "now a free agent" not in watched["cheaper_because"]


def test_namesakes_on_the_watchlist_are_unwatched_by_club(mezzala):
    squad = [
        *eleven(),
        player("João Silva", club=2, club_name="Porto B"),
        player("João Silva", club=3, club_name="Braga"),
    ]
    app = mezzala(snapshot(squad))
    app.result("watch_player", player="João Silva", club="braga")
    app.result("watch_player", player="João Silva", club="porto")
    assert app.call("unwatch_player", player="João Silva").is_error
    remaining = app.result("unwatch_player", player="João Silva", club="braga")["players"]
    assert [w["now"]["club"] for w in remaining] == ["Porto B"]


def test_watching_again_without_a_note_keeps_the_note(mezzala):
    app = mezzala(snapshot([*eleven(), player("Target", club=OTHER_CLUB)]))
    app.result("watch_player", player="Target", note="buy in January")
    assert entries(app.result("watch_player", player="Target"))["Target"]["note"] == "buy in January"


def test_a_club_that_matches_nobody_is_named_in_the_error(mezzala):
    outcome = mezzala(snapshot([*eleven(), player("Target", club=OTHER_CLUB)])).call(
        "watch_player", player="Target", club="Real Madrid"
    )
    assert outcome.is_error and "at a club matching 'Real Madrid'" in outcome.text
