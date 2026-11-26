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
    assert result["players"] == [
        {"name": "Refuser", "note": "refused to talk", "rejected_on": "2026-06-29", "worth_another_try": []}
    ]
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


def test_a_rejected_player_who_later_signs_counts_as_yours_again(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    signed = replace(next(p for p in first.players if p.name == "Refuser"), club_uid=1, club_name="Paisley")
    app.play_to(replace(first, game_date=date(2027, 1, 1), players=(*eleven(), signed)))
    own = {found["player"]["name"] for found in app.result("find_players", scope="own")["players"]}
    assert "Refuser" in own


def test_your_own_player_out_on_loan_cannot_be_rejected(mezzala):
    loanee = player("Our Loanee", on_loan=True, loan_parent_club_uid=1)
    outcome = mezzala(save(loanee)).call("reject_player", player="Our Loanee")
    assert outcome.is_error and "only other clubs' players" in outcome.text


def test_namesakes_on_the_list_are_told_apart_by_club(mezzala):
    twins = [player("John Smith", club=2, club_name="Club 2"), player("John Smith", club=3, club_name="Club 3")]
    app = mezzala(save(*twins))
    app.call("reject_player", player="John Smith", club="Club 2")
    app.call("reject_player", player="John Smith", club="Club 3")
    assert "Say which club he is at" in app.call("unreject_player", player="John Smith").text
    left = app.result("unreject_player", player="John Smith", club="Club 3")["players"]
    assert [entry["name"] for entry in left] == ["John Smith"]


def test_shortlist_and_contract_watch_leave_rejected_players_out(mezzala):
    squad = [p for p in eleven() if p.position_ratings["stc"] != 20]
    squad += [player("Refusing Striker", positions=("stc",), ca=130, value=100_000),
              player("Free Refuser", positions=("stc",), ca=130, club=None, value=None)]  # fmt: skip
    app = mezzala(snapshot(squad))
    app.call("reject_player", player="Refusing Striker")
    app.call("reject_player", player="Free Refuser")
    striker = {pick["position"]: pick for pick in app.result("shortlist")["picks"]}["striker"]
    assert striker["target"] is None
    assert app.result("contract_watch")["free_agents"] == []


def later(first, refuser, **changes):
    moved = replace(refuser, **changes)
    others = [p for p in first.players if p.uid != refuser.uid]
    return replace(first, game_date=date(2027, 1, 1), players=(*others, moved))


def test_a_rejected_player_whose_contract_is_nearly_up_and_whose_suitor_has_grown_is_worth_another_try(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    refuser = next(p for p in first.players if p.name == "Refuser")
    app.play_to(replace(later(first, refuser, contract_end=date(2027, 5, 31)), club_reputation=5_300))
    assert app.result("rejected_players")["players"][0]["worth_another_try"] == [
        "his contract ends 2027-05-31, so you can agree a pre-contract now",
        "your club's reputation has risen from 5000 to 5300 since he said no",
    ]


def test_a_rejected_player_released_by_his_club_is_worth_another_try(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    refuser = next(p for p in first.players if p.name == "Refuser")
    app.play_to(later(first, refuser, club_uid=None, club_name=None, contract_end=None))
    assert app.result("rejected_players")["players"][0]["worth_another_try"] == ["he is a free agent now"]


def test_nothing_changed_means_nothing_to_try_again(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    refuser = next(p for p in first.players if p.name == "Refuser")
    app.play_to(later(first, refuser))
    assert app.result("rejected_players")["players"][0]["worth_another_try"] == []


def test_a_rejected_free_agent_who_signs_elsewhere_is_not_worth_another_try_for_that(mezzala):
    free = player("Free Refuser", positions=("mc",), ca=110, club=None, club_name=None, contract_end=None)
    first = save(free)
    app = mezzala(first)
    app.call("reject_player", player="Free Refuser")
    app.play_to(later(first, free, club_uid=5, club_name="Club 5", contract_end=date(2029, 6, 30)))
    entry = next(e for e in app.result("rejected_players")["players"] if e["name"] == "Free Refuser")
    assert entry["worth_another_try"] == []


def test_a_rejected_player_who_moves_between_clubs_is_worth_another_try(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    refuser = next(p for p in first.players if p.name == "Refuser")
    app.play_to(later(first, refuser, club_uid=5, club_name="Club 5"))
    assert app.result("rejected_players")["players"][0]["worth_another_try"] == ["he has moved from Club 2 to Club 5"]


def test_a_loan_move_is_not_a_reason_to_try_again(mezzala):
    first = save()
    app = mezzala(first)
    app.call("reject_player", player="Refuser")
    refuser = next(p for p in first.players if p.name == "Refuser")
    app.play_to(later(first, refuser, club_uid=5, club_name="Club 5", on_loan=True, loan_parent_club_uid=2))
    assert app.result("rejected_players")["players"][0]["worth_another_try"] == []
