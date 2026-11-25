from dataclasses import replace

from factory import MY_LEAGUE, eleven, player, snapshot

RIVAL, MINNOW, OTHER_LEAGUE_CLUB = 2, 3, 4


def club_eleven(club, ca, league=MY_LEAGUE, name=None):
    return [
        player(f"{name or club} {index}", positions=places, ca=ca, club=club, league_id=league, club_name=name)
        for index, places in enumerate([("gk",), ("dc",), ("dc",), ("dl",), ("dr",), ("dm",), ("mc",), ("mc",),
                                        ("aml",), ("amr",), ("stc",)])
    ]  # fmt: skip


def test_clubs_in_the_league_are_ranked_by_their_best_eleven(mezzala):
    squad = [*eleven(ca=100), *club_eleven(RIVAL, 120, name="Rival"), *club_eleven(MINNOW, 80, name="Minnow"),
             *club_eleven(OTHER_LEAGUE_CLUB, 150, league=99, name="Elsewhere")]  # fmt: skip
    result = mezzala(snapshot(squad)).result("league_comparison")
    assert [(row["club"], row["eleven_average_ability"]) for row in result["clubs"]] == [
        ("Rival", 120.0),
        ("Paisley", 100.0),
        ("Minnow", 80.0),
    ]
    assert result["your_rank"] == 2


def test_positions_compare_the_clubs_starters_with_the_league(mezzala):
    squad = [*eleven(ca=100), *club_eleven(RIVAL, 120, name="Rival"), *club_eleven(MINNOW, 80, name="Minnow")]
    positions = {row["position"]: row for row in mezzala(snapshot(squad)).result("league_comparison")["positions"]}
    striker = positions["striker"]
    assert (striker["yours"], striker["league_median"], striker["best_club"], striker["best"]) == (
        100.0,
        100.0,
        "Rival",
        120.0,
    )


def test_a_club_whose_league_is_unknown_gets_an_explanation(mezzala):
    squad = [replace(p, league_id=None) for p in eleven()]
    result = mezzala(snapshot(squad)).result("league_comparison")
    assert result["clubs"] == [] and "could not be identified" in result["explanation"]


def test_squad_value_counts_only_the_first_team(mezzala):
    reserve = player("Reserve", club=RIVAL, league_id=MY_LEAGUE, first_team=False, value=9_000_000, club_name="Rival")
    rival = [*club_eleven(RIVAL, 120, name="Rival"), reserve]
    rows = {row["club"]: row for row in mezzala(snapshot([*eleven(), *rival])).result("league_comparison")["clubs"]}
    assert rows["Rival"]["squad_value"] == "£5.5m"
