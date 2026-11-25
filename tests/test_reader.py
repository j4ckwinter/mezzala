from types import SimpleNamespace
from typing import cast

from fmsave import ClauseKind, Contract, ContractType, Fixture, TransferValueState
from fmsave import Player as FmPlayer

from mezzala.core.players import ReleaseClause, ReleaseScope
from mezzala.save.reader import (
    first_team_leagues,
    known_value,
    release_clauses,
    wage_paid_by_current_club,
    youth_contract,
)


def test_a_player_valued_at_zero_costs_nothing_rather_than_an_unknown_fee():
    assert known_value(TransferValueState.ZERO, 0) == 0


def test_unset_and_placeholder_values_are_unknown():
    assert known_value(TransferValueState.UNSET, 0) is None
    assert known_value(TransferValueState.PLACEHOLDER, 999) is None


def test_a_real_value_is_kept():
    assert known_value(TransferValueState.OK, 450_000) == 450_000


def clause(kind, value):
    return SimpleNamespace(kind=SimpleNamespace(label=kind), value=value, parameter=None)


def test_release_clauses_keep_their_scope_and_ignore_other_clauses():
    contract = SimpleNamespace(clauses=(
        clause(ClauseKind.MINIMUM_FEE_RELEASE, 2_000_000),
        clause(ClauseKind.MINIMUM_FEE_RELEASE_FOREIGN, 500_000),
        clause(ClauseKind.APPEARANCE_FEE, 3_000),
    ))  # fmt: skip
    assert release_clauses(cast(Contract, contract)) == (
        ReleaseClause(ReleaseScope.ANY, 2_000_000),
        ReleaseClause(ReleaseScope.FOREIGN, 500_000),
    )


def test_a_youth_contract_is_recognised():
    youth = SimpleNamespace(kind=SimpleNamespace(label=ContractType.YOUTH))
    professional = SimpleNamespace(kind=SimpleNamespace(label=ContractType.FULL_TIME))
    assert youth_contract(cast(Contract, youth)) is True
    assert youth_contract(cast(Contract, professional)) is False
    assert youth_contract(None) is None


def fixture(competition, home, away, home_slot=0, away_slot=0):
    return SimpleNamespace(competition_id=competition, home_club_uid=home, away_club_uid=away,
                           home_team_slot=home_slot, away_team_slot=away_slot)  # fmt: skip


def test_a_clubs_league_is_where_its_first_team_plays_most():
    fixtures = [fixture(33, 1, 2), fixture(33, 2, 1), fixture(33, 1, 3), fixture(90, 1, 4), fixture(77, 1, 5, 1, 1),
                fixture(77, 5, 1, 1, 1), fixture(77, 1, 6, 1, 1)]  # fmt: skip
    leagues = first_team_leagues(cast(list[Fixture], fixtures))
    assert leagues[1] == 33
    assert leagues[4] == 90


def loanee(on_loan: bool):
    chain = (SimpleNamespace(club_uid=676, wage=12_500), SimpleNamespace(club_uid=1597, wage=2_500))
    contract = SimpleNamespace(wage=12_500, chain=chain)
    return cast(FmPlayer, SimpleNamespace(on_loan=on_loan, club_uid=1597, contract=contract))


def test_a_loan_players_wage_is_what_his_current_club_pays():
    assert wage_paid_by_current_club(loanee(on_loan=True)) == 2_500


def test_a_permanent_players_wage_is_his_contract_wage():
    assert wage_paid_by_current_club(loanee(on_loan=False)) == 12_500
