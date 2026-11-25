from datetime import date
from types import SimpleNamespace
from typing import cast

from fmsave import ClauseKind, Contract, ContractType, Fixture, JobVacancy, Staff, StaffJob, TransferValueState
from fmsave import Player as FmPlayer

from mezzala.core.players import ReleaseClause, ReleaseScope
from mezzala.save.reader import (
    clubs_with_a_manager,
    first_team_leagues,
    is_manager_job,
    known_value,
    loan_wage,
    matches_kept,
    open_manager_jobs,
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


def job(club, day, role=StaffJob.MANAGER, slot=0):
    return SimpleNamespace(club_uid=club, team_slot=slot, advertised_date=day, unknown={"role": role.value})


def test_open_manager_jobs_skip_filled_and_own_jobs_and_keep_the_latest_advert():
    jobs = [job(5, date(2016, 1, 1)), job(5, date(2026, 6, 1)), job(6, date(2026, 6, 1)), job(7, date(2026, 6, 1)),
            job(8, date(2026, 6, 1), role=StaffJob.SCOUT)]  # fmt: skip
    found = open_manager_jobs(cast(list[JobVacancy], jobs), filled={6}, managed_club_uid=7)
    assert [(j.club_uid, j.advertised_date) for j in found] == [(5, date(2026, 6, 1))]


def test_a_club_with_a_first_team_manager_on_its_staff_is_filled():
    staff = [SimpleNamespace(club_uid=5, team_slot=0, job=SimpleNamespace(label=StaffJob.MANAGER)),
             SimpleNamespace(club_uid=6, team_slot=3, job=SimpleNamespace(label=StaffJob.MANAGER)),
             SimpleNamespace(club_uid=7, team_slot=0, job=SimpleNamespace(label=StaffJob.SCOUT))]  # fmt: skip
    assert clubs_with_a_manager(cast(list[Staff], staff)) == {5}


def raw_fixture(day, home, away, home_slot=0, away_slot=0, played=False, neutral=False, goals=(None, None)):
    return SimpleNamespace(date=day, competition_id=33, home_club_uid=home, home_club_name=f"Club {home}",
                           away_club_uid=away, away_club_name=f"Club {away}", home_team_slot=home_slot,
                           away_team_slot=away_slot, played=played, home_goals=goals[0], away_goals=goals[1],
                           is_neutral_venue=neutral)  # fmt: skip


def test_kept_matches_include_first_team_games_against_b_teams_but_not_our_reserves():
    fixtures = [raw_fixture(date(2026, 8, 1), 1, 2, away_slot=1), raw_fixture(date(2026, 8, 2), 1, 3, home_slot=3)]
    kept = matches_kept(cast(list[Fixture], fixtures), 1, date(2026, 7, 1))
    assert [(m.home_club_uid, m.away_club_uid) for m in kept] == [(1, 2)]


def test_kept_matches_cover_three_upcoming_opponents_and_their_last_five_results():
    ours = [raw_fixture(date(2026, 8, day), 1, opponent) for day, opponent in ((1, 2), (8, 3), (15, 4), (22, 5))]
    theirs = [raw_fixture(date(2026, 7, day), 2, 9, played=True, goals=(1, 0)) for day in range(1, 8)]
    elsewhere = [raw_fixture(date(2026, 7, 9), 5, 9, played=True, goals=(2, 2))]
    kept = matches_kept(cast(list[Fixture], [*ours, *theirs, *elsewhere]), 1, date(2026, 7, 20))
    opponent_results = [m for m in kept if m.played and m.home_club_uid == 2]
    assert len(opponent_results) == 5 and opponent_results[0].day == date(2026, 7, 3)
    assert not any(m.home_club_uid == 5 and m.played for m in kept)


def test_a_neutral_venue_is_kept():
    kept = matches_kept(cast(list[Fixture], [raw_fixture(date(2026, 8, 1), 1, 2, neutral=True)]), 1, date(2026, 7, 1))
    assert kept[0].neutral is True


def test_fixtures_stored_in_older_formats_still_decode():
    from mezzala.save.store import decode_match

    nine = ["2026-08-01", 33, 1, "Paisley", 2, "Rival FC", False, None, None]
    ten = [*nine, True]
    assert (decode_match(nine).neutral, decode_match(nine).away_team_slot) == (False, 0)
    assert decode_match(ten).neutral is True
