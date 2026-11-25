from dataclasses import replace

from factory import eleven, player, snapshot

CHEAP_LEAGUE, DEAR_LEAGUE = 70, 71


def league_of(name, league, value, count=60, ca=110, reputation=5_000):
    return [
        player(f"{name} {n}", club=100 + league * 10 + n % 5, club_name=f"{name} FC {n % 5}", league_id=league,
               ca=ca, age=26, pa=120, value=value, club_reputation=reputation - n % 5)
        for n in range(count)
    ]  # fmt: skip


def test_leagues_whose_players_cost_less_than_similar_players_come_first(mezzala):
    squad = [*eleven(), *league_of("Bargain", CHEAP_LEAGUE, 500_000), *league_of("Pricey", DEAR_LEAGUE, 2_000_000)]
    rows = mezzala(snapshot(squad)).result("league_values")["leagues"]
    assert [row["league"].split("(")[1].split(" FC")[0] for row in rows[:2]] == ["Bargain", "Pricey"]
    assert rows[0]["value_vs_similar_players"] < rows[1]["value_vs_similar_players"]


def test_a_cheap_league_is_judged_on_all_its_priced_players(mezzala):
    squad = [*eleven(), *league_of("Lower", CHEAP_LEAGUE, 30_000), *league_of("Upper", DEAR_LEAGUE, 2_000_000)]
    rows = {
        row["league"].split("(")[1].split(" FC")[0]: row
        for row in mezzala(snapshot(squad)).result("league_values")["leagues"]
    }
    assert rows["Lower"]["priced_players"] == 60


def test_the_clubs_own_league_is_marked(mezzala):
    squad = [*eleven(), *league_of("Bargain", CHEAP_LEAGUE, 500_000)]
    squad = [replace(p, league_id=CHEAP_LEAGUE) if p.club_uid == 1 else p for p in squad]
    rows = mezzala(snapshot(squad)).result("league_values")["leagues"]
    assert [row["yours"] for row in rows] == [True]
