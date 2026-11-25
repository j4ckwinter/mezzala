from factory import eleven, mine, player, snapshot

GOING_RATE = "about £2,000 p/w (the going rate at clubs like yours in your country)"


def save():
    free = player("Free Agent", positions=("mc",), club=None, value=None, wage=None)
    paid = player("Well Paid", positions=("mc",), wage=9_000)
    return snapshot([*eleven(), free, paid])


def test_find_players_gives_free_agents_the_going_rate_and_others_their_wage(mezzala):
    found = {
        f["player"]["name"]: f for f in mezzala(save()).result("find_players", position="central midfield")["players"]
    }
    assert found["Free Agent"]["expected_wage"] == GOING_RATE
    assert found["Well Paid"]["expected_wage"] == "£9,000 p/w"


def test_contract_watch_free_agents_carry_the_estimate_too(mezzala):
    squad = [p for p in eleven() if p.position_ratings["mc"] != 20]
    squad += [mine("Weak Mid", positions=("mc",), ca=60), mine("Weak Mid 2", positions=("mc",), ca=60)]
    squad.append(player("Free Agent", positions=("mc",), club=None, value=None, wage=None))
    free = mezzala(snapshot([*squad, *eleven()[:5]])).result("contract_watch")["free_agents"]
    assert free[0]["expected_wage"] == GOING_RATE


def test_replacement_candidates_carry_the_estimate(mezzala):
    squad = [*eleven(), mine("Leaving Mid", positions=("mc",), ca=100)]
    squad.append(player("Free Agent", positions=("mc",), club=None, value=None, wage=None))
    candidates = mezzala(snapshot(squad)).result("find_replacement", player="Leaving Mid")["candidates"]
    assert candidates[0]["expected_wage"] == GOING_RATE
