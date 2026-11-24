from dataclasses import replace

from factory import eleven, mine, snapshot

from mezzala.players import Player


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
