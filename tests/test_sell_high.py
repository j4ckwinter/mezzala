from dataclasses import replace
from datetime import date, timedelta

from factory import eleven, mine, player, snapshot


def signals(app):
    return {entry["name"]: entry["signals"] for entry in app.result("sell_high")["candidates"]}


def test_an_old_player_at_his_ceiling_with_a_contract_ending_is_a_sale(mezzala):
    veteran = mine("Veteran", age=31, ca=120, pa=121, contract_end=date(2027, 5, 31))
    found = signals(mezzala(snapshot([*eleven(age=24, pa=140), veteran])))["Veteran"]
    assert found == [
        "past peak age at 31, value tends to fall from here",
        "at his ceiling: CA 120 of PA 121",
        "contract ends 2027-05-31, sell now or lose him for free",
    ]


def test_a_player_valued_well_above_similar_players_is_flagged(mezzala):
    peers = [player(f"Peer {n}", age=26, ca=110, pa=130, value=1_000_000) for n in range(25)]
    hyped = mine("Hyped", age=26, ca=110, pa=130, value=2_000_000)
    found = signals(mezzala(snapshot([*eleven(age=24, pa=140), *peers, hyped])))["Hyped"]
    assert found == ["valued at 2.0x similar players (£1.0m)"]


def test_young_players_are_not_called_overvalued_for_their_potential(mezzala):
    peers = [player(f"Peer {n}", age=19, ca=100, pa=110, value=200_000) for n in range(25)]
    prospect = mine("Prospect", age=19, ca=100, pa=160, value=2_000_000)
    assert "Prospect" not in signals(mezzala(snapshot([*eleven(age=24, pa=140), *peers, prospect])))


def test_history_shows_a_value_that_has_already_fallen(mezzala):
    star = mine("Fading", age=27, ca=130, pa=140, value=3_000_000)
    app = mezzala(snapshot([*eleven(age=24, pa=140), star]))
    app.call("snapshot")
    app.play_to(snapshot([*eleven(age=24, pa=140), replace(star, value=2_000_000)], game_date=date(2026, 12, 1)))
    assert signals(app)["Fading"] == ["value already down from a high of £3.0m"]


def test_history_shows_ability_stalled_while_value_rose(mezzala):
    star = mine("Stalled", age=25, ca=120, pa=140, value=1_000_000)
    app = mezzala(snapshot([*eleven(age=24, pa=140), star]))
    app.call("snapshot")
    later = replace(star, current_ability=121, value=1_500_000)
    app.play_to(snapshot([*eleven(age=24, pa=140), later], game_date=date(2027, 2, 1)))
    assert signals(app)["Stalled"] == ["CA moved +1 since 2026-06-29 while value rose from £1.0m"]


def test_a_long_career_still_remembers_the_oldest_high_value(mezzala):
    star = mine("Long Faded", age=27, ca=130, pa=140, value=5_000_000)
    squad = eleven(age=24, pa=140)
    app = mezzala(snapshot([*squad, star]))
    app.call("snapshot")
    for month in range(1, 16):
        later = replace(star, value=2_000_000)
        app.play_to(snapshot([*squad, later], game_date=date(2026, 6, 29) + timedelta(days=30 * month)))
    assert signals(app)["Long Faded"] == ["value already down from a high of £5.0m"]
