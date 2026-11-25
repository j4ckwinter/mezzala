from dataclasses import replace

from factory import eleven, mine, snapshot

from mezzala.core.players import Player


def starter_at(app, position):
    return [s["name"] for s in app.result("squad_gaps")["eleven"] if s["position"] == position]


def also_plays(player: Player, code: str, rating: int) -> Player:
    return replace(player, position_ratings={**player.position_ratings, code: rating})


def without_left_winger() -> list[Player]:
    return [p for p in eleven() if p.position_ratings["aml"] != 20]


def test_a_much_better_accomplished_player_starts_over_a_weak_natural(mezzala):
    squad = [*without_left_winger(), mine("Weak Winger", positions=("aml",), ca=88)]
    squad.append(also_plays(mine("Playmaker", positions=("amc",), ca=101), "aml", 15))
    assert starter_at(mezzala(snapshot(squad)), "left wing") == ["Playmaker"]


def test_a_natural_starts_over_a_slightly_better_accomplished_player(mezzala):
    squad = [*without_left_winger(), mine("Natural Winger", positions=("aml",), ca=100)]
    squad.append(also_plays(mine("Playmaker", positions=("amc",), ca=103), "aml", 15))
    assert starter_at(mezzala(snapshot(squad)), "left wing") == ["Natural Winger"]


def test_a_versatile_player_goes_where_nobody_else_can_play(mezzala):
    squad = [p for p in eleven() if p.position_ratings["dm"] != 20]
    squad.append(mine("Versatile", positions=("dc", "dm"), ca=150))
    starters = mezzala(snapshot(squad)).result("squad_gaps")["eleven"]
    assert [s["name"] for s in starters if s["position"] == "defensive midfield"] == ["Versatile"]
    assert all(s["name"] is not None for s in starters)


def test_two_versatile_players_still_fill_every_place(mezzala):
    squad = [p for p in eleven() if p.position_ratings["dm"] != 20]
    squad += [
        mine("Versatile One", positions=("dc", "dm"), ca=150),
        mine("Versatile Two", positions=("dc", "dm"), ca=149),
    ]
    ranking = mezzala(snapshot(squad)).result("compare_formations", formations=["4-3-3"])["ranking"]
    assert ranking[0]["empty_places"] == 0
