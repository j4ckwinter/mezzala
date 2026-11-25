from dataclasses import replace
from datetime import date

from factory import eleven, player, snapshot


def save(*extra):
    target = player("Refuser", positions=("mc",), ca=110)
    return snapshot([*eleven(), target, player("Willing", positions=("mc",), ca=105), *extra])


def names(app, tool="find_players", **arguments):
    return {found["player"]["name"] for found in app.result(tool, **arguments)["players"]}


def test_a_rejected_player_stops_coming_back_in_searches(mezzala):
    app = mezzala(save())
    result = app.result("reject_player", player="Refuser", note="refused to talk")
    assert result["players"] == [{"name": "Refuser", "note": "refused to talk", "rejected_on": "2026-06-29"}]
    assert names(app) == {"Willing"}
    candidates = app.result("find_replacement", player="Starter 6")["candidates"]
    assert "Refuser" not in {candidate["player"]["name"] for candidate in candidates}


def test_unrejecting_brings_him_back(mezzala):
    app = mezzala(save())
    app.call("reject_player", player="Refuser")
    assert app.result("unreject_player", player="refuser")["players"] == []
    assert names(app) == {"Refuser", "Willing"}


def test_the_rejected_list_survives_a_restart(mezzala):
    app = mezzala(save())
    app.call("reject_player", player="Refuser")
    assert [entry["name"] for entry in app.another_server().result("rejected_players")["players"]] == ["Refuser"]


def test_a_new_person_given_the_same_id_is_not_hidden(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    refuser = next(p for p in first.players if p.name == "Refuser")
    newcomer = replace(refuser, name="Newcomer", birth_date=date(2008, 1, 1))
    app.play_to(replace(first, game_date=date(2027, 1, 1), players=(*eleven(), newcomer)))
    assert names(app) == {"Newcomer"}


def test_your_own_players_cannot_be_rejected(mezzala):
    outcome = mezzala(save()).call("reject_player", player="Starter 3")
    assert outcome.is_error and "only other clubs' players" in outcome.text


def test_unrejecting_someone_not_on_the_list_is_reported(mezzala):
    outcome = mezzala(save()).call("unreject_player", player="Nobody")
    assert outcome.is_error and "No player called 'Nobody'" in outcome.text
