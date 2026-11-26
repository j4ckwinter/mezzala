from factory import eleven, mine, player, snapshot

GOING_RATE = "about £2,000 p/w (the going rate at clubs like yours in your country)"


def save():
    free = player("Free Agent", positions=("mc",), club=None, value=None, wage=None)
    paid = player("Well Paid", positions=("mc",), wage=9_000)
    return snapshot([*eleven(), free, paid])


def test_find_players_gives_free_agents_the_going_rate(mezzala):
    found = {
        f["player"]["name"]: f for f in mezzala(save()).result("find_players", position="central midfield")["players"]
    }
    assert found["Free Agent"]["expected_wage"] == GOING_RATE


def paid_at_clubs_like_yours(other):
    mids = [mine(f"Mid {wage}", positions=("mc",), wage=wage) for wage in (1_000, 2_000, 3_000, 4_000, 5_000)]
    return snapshot([*eleven(ca=60), *mids, other])


def expected_wage(app, name):
    return {f["player"]["name"]: f for f in app.result("find_players")["players"]}[name]["expected_wage"]


def test_a_player_paid_more_than_clubs_like_yours_pay_is_expected_to_ask_for_the_top_of_their_range(mezzala):
    app = mezzala(paid_at_clubs_like_yours(player("Well Paid", positions=("mc",), wage=20_000, club_reputation=9_000)))
    assert expected_wage(app, "Well Paid") == (
        "about £4,000 p/w (the top of the going rate at clubs like yours in your country; he earns £20,000 p/w now)"
    )


def test_a_player_paid_within_the_range_at_clubs_like_yours_is_expected_to_want_his_wage(mezzala):
    app = mezzala(paid_at_clubs_like_yours(player("Fairly Paid", positions=("mc",), wage=3_500, club_reputation=9_000)))
    assert expected_wage(app, "Fairly Paid") == "£3,500 p/w"


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
