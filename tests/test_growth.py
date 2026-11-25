from factory import player

from mezzala.core.growth import expected_gain_over


def test_expected_growth_never_exceeds_the_players_headroom():
    nearly_there = player("Nearly There", age=15, ca=149, pa=150, professionalism=20, ambition=20,
                          attributes={"determination": 20})  # fmt: skip
    assert expected_gain_over(nearly_there, 365 * 4) <= 1
