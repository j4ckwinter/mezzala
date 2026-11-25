from factory import eleven, player, snapshot


def league(prefix, league_id, ca, country="England", clubs=5, size=12):
    return [
        player(f"{prefix} {n}", club=1000 + league_id * 10 + n % clubs, club_name=f"{prefix} FC {n % clubs}",
               league_id=league_id, ca=ca, club_country=country)
        for n in range(clubs * size)
    ]  # fmt: skip


def save():
    return snapshot([*eleven(), *league("Top", 1, 140), *league("Second", 2, 115), *league("Third", 3, 95),
                     *league("Scots", 4, 120, country="Scotland")])  # fmt: skip


def found(mezzala, **arguments):
    result = mezzala(save()).result("find_players", within_reach=False, limit=500, **arguments)
    return result["players"]


def test_each_player_comes_with_his_league_country_and_estimated_division(mezzala):
    second = next(p for p in found(mezzala) if p["player"]["name"] == "Second 0")
    assert (second["country"], second["division_level"]) == ("England", 2)
    assert second["league"].startswith("England division 2 (")


def test_divisions_are_ranked_within_each_country_by_strength(mezzala):
    levels = {p["player"]["name"].split()[0]: p["division_level"] for p in found(mezzala)}
    assert (levels["Top"], levels["Second"], levels["Third"], levels["Scots"]) == (1, 2, 3, 1)


def test_find_players_filters_by_country_division_and_league(mezzala):
    names = {p["player"]["name"].split()[0] for p in found(mezzala, country="england", division_level=2)}
    assert names == {"Second"}
    assert {p["player"]["name"].split()[0] for p in found(mezzala, league="Third FC 2")} == {"Third"}
    assert {p["player"]["name"].split()[0] for p in found(mezzala, country="england")} == {"Top", "Second", "Third"}
