from datetime import date

from factory import MY_NATION, eleven, mine, player, snapshot

from mezzala.core.players import ReleaseClause, ReleaseScope

OTHER_NATION = 139


def names(app, **arguments):
    return [found["player"]["name"] for found in app.result("find_players", **arguments)["players"]]


def peers(count, **fields):
    return [player(f"Peer {n}", **fields) for n in range(count)]


def test_the_best_players_elsewhere_come_first_and_the_club_is_left_out(mezzala):
    squad = [*eleven(), mine("Our Star", ca=170), player("Their Star", ca=160), player("Decent", ca=130)]
    assert names(mezzala(snapshot(squad)), limit=2) == ["Their Star", "Decent"]


def test_own_scope_searches_the_club(mezzala):
    squad = [*eleven(), mine("Our Star", ca=170), player("Their Star", ca=160)]
    assert names(mezzala(snapshot(squad)), scope="own", limit=1) == ["Our Star"]


def test_free_agents_only(mezzala):
    squad = [*eleven(), player("Free", club=None, value=None), player("Signed")]
    assert names(mezzala(snapshot(squad)), free_agents_only=True) == ["Free"]


def test_a_fee_cap_keeps_free_and_zero_valued_players(mezzala):
    squad = [player("Dear", value=3_000_000), player("Cheap", value=400_000), player("Free", club=None, value=None),
             player("Amateur", value=0)]  # fmt: skip
    assert sorted(names(mezzala(snapshot(squad)), max_fee=500_000)) == ["Amateur", "Cheap", "Free"]


def test_value_for_money_puts_the_undervalued_first(mezzala):
    squad = [*peers(25, ca=120, age=24, value=1_000_000), player("Bargain", ca=120, age=24, value=200_000)]
    found = mezzala(snapshot(squad)).result("find_players", sort_by="value for money")["players"][0]
    assert (found["player"]["name"], found["value_vs_similar_players"]) == ("Bargain", "0.2x")


def test_above_league_level_finds_players_too_good_for_their_division(mezzala):
    lower = [player(f"Lower {n}", ca=100, league_id=7) for n in range(50)]
    upper = [player(f"Upper {n}", ca=150, league_id=8) for n in range(50)]
    squad = [*lower, *upper, player("Big Fish", ca=140, league_id=7), player("Upper Star", ca=155, league_id=8)]
    found = mezzala(snapshot(squad)).result("find_players", sort_by="above league level", limit=1)["players"][0]
    assert (found["player"]["name"], found["above_league_level"]) == ("Big Fish", 40.0)


def test_position_attributes_find_strong_attributes_behind_low_ability(mezzala):
    finisher = {"finishing": 18, "off_the_ball": 17, "composure": 16, "first_touch": 16, "anticipation": 16}
    squad = [
        player("Raw Finisher", positions=("stc",), ca=95, attributes=finisher),
        player("Average Striker", positions=("stc",), ca=95),
        player("Good Striker", positions=("stc",), ca=150),
    ]
    found = names(mezzala(snapshot(squad)), position="striker", max_ca=100, sort_by="position attributes")
    assert found == ["Raw Finisher", "Average Striker"]


def clause(scope, fee):
    return (ReleaseClause(scope, fee),)


def test_only_release_clauses_that_apply_to_the_club_count(mezzala):
    squad = [
        player("Domestic Clause", club_nation_id=MY_NATION, release_clauses=clause(ReleaseScope.DOMESTIC, 300_000)),
        player(
            "Foreign Clause Abroad", club_nation_id=OTHER_NATION, release_clauses=clause(ReleaseScope.FOREIGN, 400_000)
        ),
        player(
            "Foreign Clause At Home", club_nation_id=MY_NATION, release_clauses=clause(ReleaseScope.FOREIGN, 100_000)
        ),
        player("Big Clause", release_clauses=clause(ReleaseScope.ANY, 9_000_000)),
        player(
            "Domestic Clause Abroad", club_nation_id=OTHER_NATION, release_clauses=clause(ReleaseScope.DOMESTIC, 50_000)
        ),
    ]
    found = names(mezzala(snapshot(squad)), max_release_clause=1_000_000, sort_by="lowest release clause")
    assert found == ["Domestic Clause", "Foreign Clause Abroad"]


def test_youth_contracts_reserves_and_bigger_clubs_can_be_required(mezzala):
    squad = [
        player("Youth Deal", youth_contract=True),
        player("Reserve At Big Club", first_team=False, club_reputation=8_000),
        player("Starter At Big Club", first_team=True, club_reputation=8_000),
        player("Reserve At Small Club", first_team=False, club_reputation=3_000),
    ]
    app = mezzala(snapshot(squad, club_reputation=5_000))
    assert names(app, youth_contract_only=True) == ["Youth Deal"]
    assert names(app, reserves_only=True, bigger_clubs_only=True) == ["Reserve At Big Club"]


def test_famous_players_appear_only_when_reach_is_off(mezzala):
    squad = [player("World Star", ca=190, reputation=9_500), player("Local", ca=110)]
    app = mezzala(snapshot(squad))
    assert names(app) == ["Local"]
    assert names(app, within_reach=False, limit=1) == ["World Star"]


def test_contracts_ending_soon(mezzala):
    squad = [player("Ending", contract_end=date(2027, 5, 31)), player("Settled", contract_end=date(2030, 6, 30))]
    assert names(mezzala(snapshot(squad)), contract_ending_within_months=12) == ["Ending"]


def test_most_overpaid_ranks_wages_against_similar_players(mezzala):
    squad = [*peers(25, ca=110, age=27, wage=2_000), player("Fat Cat", ca=110, age=27, wage=9_000)]
    assert names(mezzala(snapshot(squad)), sort_by="most overpaid", limit=1) == ["Fat Cat"]


def test_age_and_potential_filters_find_young_high_potential_players(mezzala):
    squad = [player("Wonderkid", age=17, ca=90, pa=175), player("Old Pro", age=31, ca=140, pa=141),
             player("Ordinary Kid", age=17, ca=80, pa=120)]  # fmt: skip
    assert names(mezzala(snapshot(squad)), max_age=18, min_pa=160) == ["Wonderkid"]


def test_players_without_a_market_value_are_not_called_good_value(mezzala):
    squad = [
        *peers(25, ca=120, age=24, value=1_000_000),
        player("Bargain", ca=120, age=24, value=500_000),
        player("Free Agent", ca=120, age=24, club=None, value=None),
        player("Amateur", ca=120, age=24, value=0),
    ]
    found = mezzala(snapshot(squad)).result("find_players", sort_by="value for money", limit=30)["players"]
    assert found[0]["player"]["name"] == "Bargain"
    assert {f["player"]["name"]: f["value_vs_similar_players"] for f in found}["Amateur"] == "unknown"


def test_a_player_elsewhere_whose_loan_ends_is_not_a_contract_ending(mezzala):
    squad = [
        player(
            "Loan Ending",
            on_loan=True,
            loan_parent_club_uid=9,
            loan_end=date(2027, 5, 31),
            contract_end=date(2030, 6, 30),
        ),
        player("Contract Ending", contract_end=date(2027, 5, 31)),
        mine(
            "Our Loanee",
            on_loan=True,
            loan_parent_club_uid=9,
            loan_end=date(2027, 5, 31),
            contract_end=date(2030, 6, 30),
        ),
    ]
    app = mezzala(snapshot(squad))
    assert names(app, contract_ending_within_months=12) == ["Contract Ending"]
    assert names(app, scope="own", contract_ending_within_months=12) == ["Our Loanee"]


def test_a_wage_cap_judges_players_elsewhere_by_their_contract_not_their_loan_deal(mezzala):
    squad = [
        player("Loaned Star", wage=20_000, on_loan=True, loan_parent_club_uid=9, loan_wage=0),
        player("Affordable", wage=3_000),
        player("Unknown Wage", wage=None),
    ]
    assert names(mezzala(snapshot(squad)), max_wage=5_000) == ["Affordable"]


def test_our_loan_players_are_judged_on_what_we_pay_them(mezzala):
    loanee = mine("Our Loanee", ca=110, age=27, wage=12_500, on_loan=True, loan_parent_club_uid=9, loan_wage=2_000)
    squad = [*peers(25, ca=110, age=27, wage=2_000), loanee]
    found = mezzala(snapshot(squad)).result("find_players", scope="own")["players"][0]
    assert found["wage_vs_similar_players"] == "1.0x"
    assert (found["player"]["wage"], found["player"]["wage_while_on_loan"]) == ("£12,500 p/w", "£2,000 p/w")
