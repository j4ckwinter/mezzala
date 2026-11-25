from dataclasses import replace
from datetime import date

from factory import SEASON_START, eleven, mine, snapshot

from mezzala.core.players import Injury


def test_injured_and_banned_players_are_listed_as_unavailable(mezzala):
    hurt = mine("Hurt", injury="Twisted Ankle", injured_until=date(2026, 7, 10))
    healed = mine("Healed", injury="Bruised Ribs", injured_until=date(2026, 6, 1))
    banned = mine("Banned", banned_from=("Scottish Cup",))
    result = mezzala(snapshot([*eleven(), hurt, healed, banned])).result("fitness")
    assert result["unavailable"] == ["Hurt: Twisted Ankle, back 2026-07-10", "Banned: banned from Scottish Cup"]


def test_a_player_back_on_the_day_is_still_unavailable_that_day(mezzala):
    hurt = mine("Back Today", injury="Dead Leg", injured_until=SEASON_START)
    assert mezzala(snapshot([*eleven(), hurt])).result("fitness")["unavailable"] == [
        "Back Today: Dead Leg, back 2026-06-29"
    ]


def test_injury_prone_starters_are_flagged(mezzala):
    squad = eleven()
    injuries = (Injury(date(2025, 9, 1), "minor", "in match"), Injury(date(2026, 2, 1), "major", None))
    squad[1] = replace(squad[1], attributes={**squad[1].attributes, "injury_proneness": 16}, injuries=injuries)
    risks = mezzala(snapshot(squad)).result("fitness")["injury_risks_in_the_eleven"]
    assert risks == [{"name": "Starter 1", "detail": "prone to injury, 2 injuries in the last two years"}]


def test_low_condition_and_sharpness_are_listed_worst_first(mezzala):
    tired = [mine("Tired", condition=84), mine("Exhausted", condition=72), mine("Rusty", match_sharpness=40)]
    fine = [mine("Fine", condition=95, match_sharpness=90), mine("Edge", condition=90, match_sharpness=70)]
    squad = [*eleven(), *tired, *fine]
    result = mezzala(snapshot(squad)).result("fitness")
    assert result["low_condition"] == [{"name": "Exhausted", "detail": "72%"}, {"name": "Tired", "detail": "84%"}]
    assert result["low_match_sharpness"] == [{"name": "Rusty", "detail": "40%"}]
