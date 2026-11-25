from datetime import date
from types import SimpleNamespace
from typing import cast

from fmsave import ClauseKind, Contract, ContractType, Fixture, JobVacancy, StaffJob, TransferValueState
from fmsave import Player as FmPlayer

from mezzala.core.players import ReleaseClause, ReleaseScope
from mezzala.save.reader import (
    first_team_leagues,
    is_manager_job,
    known_value,
    loan_wage,
    release_clauses,
    youth_contract,
)


def test_a_player_valued_at_zero_costs_nothing_rather_than_an_unknown_fee():
    assert known_value(TransferValueState.ZERO, 0) == 0


def test_unset_and_placeholder_values_are_unknown():
    assert known_value(TransferValueState.UNSET, 0) is None
    assert known_value(TransferValueState.PLACEHOLDER, 999) is None


def test_a_real_value_is_kept():
    assert known_value(TransferValueState.OK, 450_000) == 450_000


def clause(kind, value, parameter=None):
    return SimpleNamespace(kind=SimpleNamespace(label=kind), value=value, parameter=parameter)


def test_release_clauses_keep_their_scope_and_ignore_other_clauses():
    contract = SimpleNamespace(start=date(2025, 7, 1), clauses=(
        clause(ClauseKind.MINIMUM_FEE_RELEASE, 2_000_000),
        clause(ClauseKind.MINIMUM_FEE_RELEASE_FOREIGN, 500_000),
        clause(ClauseKind.APPEARANCE_FEE, 3_000),
    ))  # fmt: skip
    assert release_clauses(cast(Contract, contract)) == (
        ReleaseClause(ReleaseScope.ANY, 2_000_000, None),
        ReleaseClause(ReleaseScope.FOREIGN, 500_000, None),
    )


def test_a_youth_contract_is_recognised():
    youth = SimpleNamespace(kind=SimpleNamespace(label=ContractType.YOUTH))
    professional = SimpleNamespace(kind=SimpleNamespace(label=ContractType.FULL_TIME))
    assert youth_contract(cast(Contract, youth)) is True
    assert youth_contract(cast(Contract, professional)) is False
    assert youth_contract(None) is None


def fixture(competition, home, away, home_slot=0, away_slot=0, season: int | None = 2026):
    return SimpleNamespace(competition_id=competition, home_club_uid=home, away_club_uid=away,
                           home_team_slot=home_slot, away_team_slot=away_slot, season_start_year=season)  # fmt: skip


SCOTLAND, SPAIN, ITALY = 167, 51, 59


def leagues_of(fixtures, nations):
    return first_team_leagues(cast(list[Fixture], fixtures), nations)


def test_a_clubs_league_is_where_its_first_team_plays_most():
    fixtures = [fixture(33, 1, 2), fixture(33, 2, 1), fixture(33, 1, 3), fixture(90, 1, 4), fixture(77, 1, 5, 1, 1),
                fixture(77, 5, 1, 1, 1), fixture(77, 1, 6, 1, 1)]  # fmt: skip
    leagues = leagues_of(fixtures, dict.fromkeys(range(1, 7), SCOTLAND))
    assert leagues[1] == 33
    assert leagues[4] == 90


def test_friendlies_without_a_season_are_not_a_league():
    fixtures = [fixture(131, 1, 2, season=None), fixture(131, 1, 3, season=None), fixture(131, 1, 4, season=None),
                fixture(33, 1, 5)]  # fmt: skip
    assert leagues_of(fixtures, dict.fromkeys(range(1, 6), SCOTLAND))[1] == 33


def test_a_competition_spanning_several_nations_is_not_a_league():
    nations = {1: SCOTLAND, 2: SPAIN, 3: ITALY, 4: SPAIN, 5: SCOTLAND}
    fixtures = [fixture(500, 1, 2), fixture(500, 1, 3), fixture(500, 1, 4), fixture(33, 1, 5)]
    assert leagues_of(fixtures, nations)[1] == 33
    assert 2 not in leagues_of(fixtures, nations)


def loanee(on_loan: bool):
    chain = (SimpleNamespace(club_uid=676, wage=12_500), SimpleNamespace(club_uid=1597, wage=2_500))
    contract = SimpleNamespace(wage=12_500, chain=chain)
    return cast(FmPlayer, SimpleNamespace(on_loan=on_loan, club_uid=1597, contract=contract))


def test_a_loan_player_records_what_his_current_club_pays():
    assert loan_wage(loanee(on_loan=True)) == 2_500


def test_a_permanent_player_has_no_loan_wage():
    assert loan_wage(loanee(on_loan=False)) is None


def test_a_domestic_release_clause_expires_the_given_days_after_the_contract_starts():
    contract = SimpleNamespace(
        start=date(2025, 7, 1), clauses=(clause(ClauseKind.MINIMUM_FEE_RELEASE_DOMESTIC, 900_000, 365),)
    )
    assert release_clauses(cast(Contract, contract)) == (
        ReleaseClause(ReleaseScope.DOMESTIC, 900_000, date(2026, 7, 1)),
    )


def test_only_first_team_manager_jobs_count_as_vacancies():
    manager = SimpleNamespace(team_slot=0, unknown={"role": StaffJob.MANAGER.value})
    scout = SimpleNamespace(team_slot=0, unknown={"role": StaffJob.SCOUT.value})
    reserve_manager = SimpleNamespace(team_slot=1, unknown={"role": StaffJob.MANAGER.value})
    assert [is_manager_job(cast(JobVacancy, job)) for job in (manager, scout, reserve_manager)] == [True, False, False]
