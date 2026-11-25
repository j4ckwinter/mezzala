from factory import eleven, mine, player, snapshot

from mezzala.core.players import SeasonStats


def season(minutes=900, rating=6.8, goals=0, xg=0.0, assists=0, key_passes=0, tackles=0, interceptions=0):
    return SeasonStats(minutes, 10, 0, rating, goals, assists, xg, 0.0, 10, key_passes, 0, 0, tackles,
                       interceptions, None, 0)  # fmt: skip


def peers(count=10):
    return [player(f"Peer {n}", ca=100, season=season()) for n in range(count)]


def test_own_players_are_ranked_by_how_far_their_rating_beats_similar_players(mezzala):
    star = mine("Star", ca=100, season=season(rating=7.4))
    flop = mine("Flop", ca=100, season=season(rating=6.5))
    result = mezzala(snapshot([*eleven(), star, flop, *peers()])).result("performance")
    assert [(p["player"]["name"], p["rating_above_similar_players"]) for p in result["players"]] == [
        ("Star", 0.6), ("Flop", -0.3)]  # fmt: skip


def test_players_without_enough_minutes_are_left_out(mezzala):
    cameo = mine("Cameo", ca=100, season=season(minutes=200, rating=9.0))
    result = mezzala(snapshot([*eleven(), cameo, *peers()])).result("performance")
    assert result["players"] == []
    assert mezzala(snapshot([*eleven(), cameo, *peers()])).result("performance", min_minutes=100)["matched"] == 1


def test_wasteful_finishers_sort_first_by_goals_below_xg(mezzala):
    wasteful = mine("Wasteful", positions=("stc",), season=season(goals=3, xg=9.5))
    clinical = mine("Clinical", positions=("stc",), season=season(goals=10, xg=6.0))
    result = mezzala(snapshot([*eleven(), wasteful, clinical])).result("performance", sort_by="goals below xg")
    assert [p["player"]["name"] for p in result["players"]] == ["Wasteful", "Clinical"]
    assert result["players"][0]["goals_above_xg"] == -6.5


def test_output_is_shown_per_90_minutes(mezzala):
    creator = mine("Creator", season=season(minutes=900, goals=5, assists=3, key_passes=18, tackles=9, interceptions=9))
    entry = mezzala(snapshot([*eleven(), creator])).result("performance", sort_by="key passes per 90")["players"][0]
    assert (entry["goals_per_90"], entry["assists_per_90"], entry["key_passes_per_90"]) == (0.5, 0.3, 1.8)
    assert entry["tackles_and_interceptions_per_90"] == 1.8


def test_scouting_elsewhere_keeps_realistic_targets_unless_asked(mezzala):
    reachable = player("Reachable", season=season(goals=8))
    superstar = player("Superstar", reputation=9_900, club_reputation=9_900, season=season(goals=20))
    save = snapshot([*eleven(), reachable, superstar])
    found = mezzala(save).result("performance", scope="elsewhere", sort_by="goals per 90")["players"]
    assert [p["player"]["name"] for p in found] == ["Reachable"]
    everyone = mezzala(save).result("performance", scope="elsewhere", sort_by="goals per 90", within_reach=False)
    assert [p["player"]["name"] for p in everyone["players"]] == ["Superstar", "Reachable"]


def test_without_enough_similar_players_there_is_no_rating_comparison(mezzala):
    lonely = mine("Lonely", ca=100, season=season(rating=7.5))
    result = mezzala(snapshot([*eleven(), lonely, *peers(5)])).result("performance")
    assert result["players"] == [] and result["matched"] == 0
    assert mezzala(snapshot([*eleven(), lonely])).result("performance", sort_by="average rating")["matched"] == 1


def test_only_players_of_similar_ability_set_the_comparison(mezzala):
    stronger = [player(f"Stronger {n}", ca=150, season=season(rating=7.6)) for n in range(10)]
    star = mine("Star", ca=100, season=season(rating=7.4))
    result = mezzala(snapshot([*eleven(), star, *peers(), *stronger])).result("performance")
    assert result["players"][0]["rating_above_similar_players"] == 0.6
