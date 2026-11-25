from dataclasses import replace
from datetime import date

from factory import eleven, mine, player, snapshot

ENDING = date(2027, 5, 31)


def watch(app, **arguments):
    return app.result("contract_watch", **arguments)


def test_own_expiring_contracts_come_with_advice(mezzala):
    key = mine("Key Man", positions=("stc",), ca=130, contract_end=ENDING)
    spare = mine("Spare", positions=("stc",), ca=80, contract_end=ENDING)
    loanee = mine("Loanee", positions=("dr",), ca=110, on_loan=True, loan_parent_club_uid=9, loan_end=ENDING)
    report = watch(mezzala(snapshot([*eleven(), key, spare, loanee])))
    advice = {entry["player"]["name"]: entry["advice"] for entry in report["own_expiring"]}
    assert advice == {
        "Key Man": "first-team level: renew, or sell before he can leave for free",
        "Loanee": "loan player returning to his parent club; replace or extend the loan",
        "Spare": "squad player: let him run down or sell for what you can get",
    }


def test_free_agents_and_expiring_players_who_beat_a_starter_are_targets(mezzala):
    free = player("Free Striker", positions=("stc",), ca=120, club=None, value=None)
    expiring = player("Expiring Keeper", positions=("gk",), ca=115, contract_end=ENDING)
    settled = player("Settled Keeper", positions=("gk",), ca=140)
    worse = player("Worse Free", positions=("stc",), ca=90, club=None)
    report = watch(mezzala(snapshot([*eleven(), free, expiring, settled, worse])))
    assert [(t["player"]["name"], t["position"], t["improves_on"]) for t in report["free_agents"]] == [
        ("Free Striker", "striker", "Starter 10 (100)")
    ]
    assert [t["player"]["name"] for t in report["pre_contract_targets"]] == ["Expiring Keeper"]


def test_targets_out_of_reach_are_left_out(mezzala):
    famous = player("Famous", positions=("stc",), ca=170, club=None, reputation=9_000)
    report = watch(mezzala(snapshot([*eleven(), famous])))
    assert report["free_agents"] == []
    assert [
        t["player"]["name"] for t in watch(mezzala(snapshot([*eleven(), famous])), within_reach=False)["free_agents"]
    ] == ["Famous"]


def test_targets_are_measured_against_the_weakest_starter_in_a_position(mezzala):
    squad = [p for p in eleven() if p.position_ratings["dc"] != 20]
    squad += [mine("Strong Centre Back", positions=("dc",), ca=130), mine("Weak Centre Back", positions=("dc",), ca=90)]
    squad.append(player("Free Defender", positions=("dc",), ca=110, club=None, value=None))
    report = watch(mezzala(snapshot(squad)))
    assert [(t["player"]["name"], t["improves_on"]) for t in report["free_agents"]] == [
        ("Free Defender", "Weak Centre Back (90)")
    ]


def test_a_free_agent_who_beats_an_out_of_position_starters_level_is_a_target(mezzala):
    squad = [p for p in eleven() if p.position_ratings["amr"] != 20]
    ramos = mine("Ramos", positions=("aml",), ca=100)
    squad.append(replace(ramos, position_ratings={**ramos.position_ratings, "amr": 16}))
    squad.append(player("Free Winger", positions=("amr",), ca=98, club=None, value=None))
    free = mezzala(snapshot(squad)).result("contract_watch")["free_agents"]
    assert [(target["player"]["name"], target["improves_on"]) for target in free] == [
        ("Free Winger", "Ramos (100, out of position)")]  # fmt: skip
