from datetime import date

from factory import eleven, mine, player, snapshot

FOREIGN = 999
SOON = date(2026, 12, 15)


def without(position_code):
    return [p for p in eleven() if p.position_ratings[position_code] != 20]


def plan_for(app, position, **arguments):
    plans = {plan["position"]: plan for plan in app.result("recruitment_plan", **arguments)["positions"]}
    return plans[position]


def striker_market():
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad += [player(f"Paid Keeper {n}", positions=("gk",), ca=120, wage=2_000) for n in range(5)]
    squad += [
        player("Free Striker", positions=("stc",), ca=120, club=None, value=None, wage=None),
        player("Expiring Striker", positions=("stc",), ca=121, value=2_000_000, contract_end=SOON,
               club_nation_id=FOREIGN),
        player("Transfer Striker", positions=("stc",), ca=122, value=500_000),
        player("Dear Striker", positions=("stc",), ca=150, value=9_000_000),
    ]  # fmt: skip
    return snapshot(squad, transfer_budget=1_000_000)


def test_free_agents_pre_contracts_and_transfers_share_one_ranked_list(mezzala):
    striker = plan_for(mezzala(striker_market()), "striker")
    assert [(o["player"]["name"], o["route"], o["fee"]) for o in striker["options"]] == [
        ("Expiring Striker", "pre-contract", "£0"),
        ("Free Striker", "free agent", "£0"),
        ("Transfer Striker", "transfer", "£500k"),
    ]
    assert striker["pick"]["player"]["name"] == "Expiring Striker"
    assert striker["pick"]["how"] == "contract ends 2026-12-15: you can agree a pre-contract now"


def test_a_transfer_beyond_the_budget_is_left_out(mezzala):
    striker = plan_for(mezzala(striker_market()), "striker", transfer_budget=100_000)
    assert "Transfer Striker" not in [o["player"]["name"] for o in striker["options"]]


def test_each_option_says_why_he_might_refuse(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad.append(player("Domestic Striker", positions=("stc",), ca=120, contract_end=SOON))
    striker = plan_for(mezzala(snapshot(squad)), "striker")
    assert striker["pick"]["warnings"] == [
        "at a club in your own country: such players often refuse a pre-contract, so expect to wait "
        "for his contract to end or to pay a fee"
    ]


def test_the_pick_spends_the_budget_for_later_positions(mezzala):
    squad = [p for p in without("stc") if p.position_ratings["gk"] != 20]
    squad += [mine("Weak Keeper", positions=("gk",), ca=60), mine("Weak Striker", positions=("stc",), ca=60)]
    squad += [player("Keeper", positions=("gk",), ca=120, value=700_000),
              player("Striker", positions=("stc",), ca=120, value=700_000),
              player("Cheap Striker", positions=("stc",), ca=100, value=250_000)]  # fmt: skip
    result = mezzala(snapshot(squad, transfer_budget=1_000_000)).result("recruitment_plan")
    chosen = {plan["position"]: plan["pick"]["player"]["name"] for plan in result["positions"] if plan["pick"]}
    assert chosen == {"goalkeeper": "Keeper", "striker": "Cheap Striker"}
    assert result["total_fees"] == "£950k"


def test_a_transfer_carries_no_pre_contract_warning(mezzala):
    squad = [*without("stc"), mine("Weak Striker", positions=("stc",), ca=70)]
    squad.append(player("Domestic Striker", positions=("stc",), ca=120, value=300_000))
    squad.append(player("Loaned Striker", positions=("stc",), ca=119, value=300_000, on_loan=True,
                        loan_parent_club_uid=7))  # fmt: skip
    options = {o["player"]["name"]: o for o in plan_for(mezzala(snapshot(squad)), "striker")["options"]}
    assert options["Domestic Striker"]["warnings"] == []
    assert options["Loaned Striker"]["warnings"] == ["on loan at Club 2, so his parent club decides on a sale"]
