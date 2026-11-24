from fmsave import TransferValueState

from mezzala.reader import known_value


def test_a_player_valued_at_zero_costs_nothing_rather_than_an_unknown_fee():
    assert known_value(TransferValueState.ZERO, 0) == 0


def test_unset_and_placeholder_values_are_unknown():
    assert known_value(TransferValueState.UNSET, 0) is None
    assert known_value(TransferValueState.PLACEHOLDER, 999) is None


def test_a_real_value_is_kept():
    assert known_value(TransferValueState.OK, 450_000) == 450_000
