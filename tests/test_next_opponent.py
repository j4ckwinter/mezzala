from dataclasses import replace
from datetime import date

from factory import MY_CLUB, eleven, player, snapshot

from mezzala.core.players import Match

RIVAL, OTHER = 2, 3
SHAPE = [("gk",), ("dc",), ("dc",), ("dl",), ("dr",), ("dm",), ("mc",), ("mc",), ("aml",), ("amr",), ("stc",)]


def rival_squad(attributes):
    return [
        player(f"Rival {n}", club=RIVAL, club_name="Rival FC", positions=positions, ca=110 + n, attributes=attributes)
        for n, positions in enumerate(SHAPE)
    ]


def match(day, home, away, played=False, home_goals=None, away_goals=None):
    names = {MY_CLUB: "Paisley", RIVAL: "Rival FC", OTHER: "Other FC"}
    return Match(day, 33, home, names[home], away, names[away], played, home_goals, away_goals, False, 0, 0)


def test_the_next_opponent_is_analysed(mezzala):
    fixtures = (
        match(date(2026, 8, 8), RIVAL, MY_CLUB),
        match(date(2026, 8, 1), MY_CLUB, OTHER, played=True, home_goals=2, away_goals=0),
        match(date(2026, 7, 25), RIVAL, OTHER, played=True, home_goals=1, away_goals=3),
        match(date(2026, 8, 15), MY_CLUB, OTHER),
    )
    squad = [*eleven(), *rival_squad({"pace": 17, "acceleration": 17})]
    result = mezzala(snapshot(squad, game_date=date(2026, 8, 2), matches=fixtures)).result("next_opponent")
    assert (result["date"], result["opponent"], result["venue"]) == ("2026-08-08", "Rival FC", "away")
    assert result["their_key_players"][0]["name"] == "Rival 10"
    assert len([s for s in result["their_eleven"] if s["name"]]) == 11
    pace = {g["group"]: g for g in result["attributes"]}["pace"]
    assert pace["difference"] == -7.0
    assert result["their_recent_results"] == ["2026-07-25 L 1-3 v Other FC"]


def test_no_upcoming_fixture_is_explained(mezzala):
    result = mezzala(snapshot(eleven())).result("next_opponent")
    assert result["opponent"] is None and "No upcoming" in result["explanation"]


def test_fixtures_survive_a_restart(mezzala):
    app = mezzala(snapshot(eleven(), matches=(match(date(2026, 8, 8), MY_CLUB, RIVAL),)))
    app.call("snapshot")
    assert app.another_server().result("next_opponent")["opponent"] == "Rival FC"


def test_a_neutral_cup_tie_is_labelled_and_the_next_unplayed_match_on_the_save_date_counts(mezzala):
    cup = Match(date(2026, 8, 2), 666, MY_CLUB, "Paisley", RIVAL, "Rival FC", False, None, None, True, 0, 0)
    played_today = match(date(2026, 8, 2), MY_CLUB, OTHER, played=True, home_goals=1, away_goals=1)
    elsewhere = match(date(2026, 8, 2), RIVAL, OTHER)
    squad = [*eleven(), *rival_squad({})]
    result = mezzala(snapshot(squad, game_date=date(2026, 8, 2), matches=(played_today, elsewhere, cup))).result(
        "next_opponent"
    )
    assert (result["opponent"], result["venue"], result["competition"]) == (
        "Rival FC",
        "neutral",
        "cup or other competition",
    )


def test_recent_results_are_the_last_five_and_away_results_read_from_their_side(mezzala):
    fixtures = [match(date(2026, 8, 20), MY_CLUB, RIVAL)]
    fixtures += [
        match(date(2026, 7, day), OTHER, RIVAL, played=True, home_goals=1, away_goals=2) for day in range(1, 8)
    ]
    result = mezzala(
        snapshot([*eleven(), *rival_squad({})], game_date=date(2026, 8, 1), matches=tuple(fixtures))
    ).result("next_opponent")
    assert result["their_recent_results"][0] == "2026-07-07 W 2-1 at Other FC"
    assert len(result["their_recent_results"]) == 5


def test_formations_their_squad_fits_equally_well_are_all_listed(mezzala):
    fixtures = (match(date(2026, 8, 8), MY_CLUB, RIVAL),)
    squad = [
        *eleven(),
        *rival_squad({}),
        player("Rival AM", club=RIVAL, club_name="Rival FC", positions=("amc",), ca=115),
    ]
    result = mezzala(snapshot(squad, matches=fixtures)).result("next_opponent")
    assert len(result["their_likely_formations"]) >= 2


def test_a_match_against_a_reserve_side_is_analysed_as_that_side(mezzala):
    reserves = [player(f"Rival Kid {n}", club=RIVAL, club_name="Rival FC", positions=p, ca=80, first_team=False)
                for n, p in enumerate(SHAPE)]  # fmt: skip
    friendly = Match(date(2026, 7, 10), 131, MY_CLUB, "Paisley", RIVAL, "Rival FC", False, None, None, False, 0, 1)
    squad = [*eleven(), *rival_squad({}), *reserves]
    result = mezzala(snapshot(squad, matches=(friendly,))).result("next_opponent")
    assert result["opponent"] == "Rival FC (reserve or youth side)"
    assert result["their_key_players"][0]["name"].startswith("Rival Kid")


def test_a_neutral_venue_and_reserve_side_survive_a_restart(mezzala):
    reserves = [player(f"Rival Kid {n}", club=RIVAL, club_name="Rival FC", positions=p, first_team=False)
                for n, p in enumerate(SHAPE)]  # fmt: skip
    final = Match(date(2026, 8, 2), 666, MY_CLUB, "Paisley", RIVAL, "Rival FC", False, None, None, True, 0, 1)
    app = mezzala(snapshot([*eleven(), *reserves], matches=(final,)))
    app.call("snapshot")
    result = app.another_server().result("next_opponent")
    assert (result["venue"], result["opponent"]) == ("neutral", "Rival FC (reserve or youth side)")


def test_injured_players_are_left_out_of_both_elevens_and_listed(mezzala):
    fixtures = (match(date(2026, 8, 8), RIVAL, MY_CLUB),)
    rivals = rival_squad({})
    rivals[10] = replace(rivals[10], injury="Broken Leg", injured_until=date(2026, 9, 1))
    mine = eleven()
    mine[5] = replace(mine[5], injury="Hamstring", injured_until=date(2026, 8, 20))
    mine[6] = replace(mine[6], banned_from=("Premiership",))
    result = mezzala(snapshot([*mine, *rivals], game_date=date(2026, 8, 2), matches=fixtures)).result("next_opponent")
    assert "Rival 10" not in [starter["name"] for starter in result["their_eleven"]]
    assert result["their_key_players"][0]["name"] == "Rival 9"
    assert result["their_missing"] == ["Rival 10: Broken Leg, back 2026-09-01"]
    assert result["your_missing"] == ["Starter 5: Hamstring, back 2026-08-20", "Starter 6: banned from Premiership"]


def test_a_player_fit_again_by_match_day_is_not_missing(mezzala):
    fixtures = (match(date(2026, 8, 8), RIVAL, MY_CLUB),)
    rivals = rival_squad({})
    rivals[10] = replace(rivals[10], injury="Knock", injured_until=date(2026, 8, 5))
    result = mezzala(snapshot([*eleven(), *rivals], game_date=date(2026, 8, 2), matches=fixtures)).result(
        "next_opponent"
    )
    assert result["their_missing"] == [] and result["their_key_players"][0]["name"] == "Rival 10"


def test_your_injured_players_do_not_count_in_the_attribute_comparison(mezzala):
    fixtures = (match(date(2026, 8, 8), RIVAL, MY_CLUB),)
    mine = eleven()
    flyer = replace(mine[10], name="Injured Flyer", attributes={**mine[10].attributes, "pace": 20, "acceleration": 20},
                    injury="Hamstring", injured_until=date(2026, 8, 20))  # fmt: skip
    cover = replace(mine[10], uid=mine[10].uid + 5000, name="Cover Striker", current_ability=60)
    save = snapshot([*mine[:10], flyer, cover, *rival_squad({})], game_date=date(2026, 8, 2), matches=fixtures)
    pace = {g["group"]: g for g in mezzala(save).result("next_opponent")["attributes"]}["pace"]
    assert pace["yours"] == 10.0
