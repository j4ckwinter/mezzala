import dataclasses
import warnings
from collections import Counter
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

import fmsave

from mezzala.core.players import Budget, Match, Player, ReleaseClause, ReleaseScope, Snapshot, Vacancy
from mezzala.save.contracts import contract_end, contract_wage
from mezzala.save.labels import coded_label, label
from mezzala.save.nations import nation_name
from mezzala.save.own_club import club_staff, first_team_tactics, mentoring_groups
from mezzala.save.player_records import PlayerRecords, player_records


class UnreadableSave(RuntimeError):
    pass


def known_value(state: fmsave.TransferValueState, value: int | None) -> int | None:
    match state:
        case fmsave.TransferValueState.OK:
            return value
        case fmsave.TransferValueState.ZERO:
            return 0
        case fmsave.TransferValueState.UNSET | fmsave.TransferValueState.PLACEHOLDER:
            return None


RELEASE_SCOPES = {
    fmsave.ClauseKind.MINIMUM_FEE_RELEASE: ReleaseScope.ANY,
    fmsave.ClauseKind.MINIMUM_FEE_RELEASE_DOMESTIC: ReleaseScope.DOMESTIC,
    fmsave.ClauseKind.MINIMUM_FEE_RELEASE_FOREIGN: ReleaseScope.FOREIGN,
}


def clause_expiry(scope: ReleaseScope, days: int | None, contract_start: date | None) -> date | None:
    if scope is not ReleaseScope.DOMESTIC or days is None or contract_start is None:
        return None
    return contract_start + timedelta(days=days)


def release_clauses(contract: fmsave.Contract | None) -> tuple[ReleaseClause, ...]:
    if contract is None:
        return ()
    found: list[ReleaseClause] = []
    for clause in contract.clauses:
        scope = RELEASE_SCOPES.get(clause.kind.label)
        if scope is not None and clause.value is not None:
            found.append(ReleaseClause(scope, clause.value, clause_expiry(scope, clause.parameter, contract.start)))
    return tuple(found)


def youth_contract(contract: fmsave.Contract | None) -> bool | None:
    if contract is None or contract.kind is None:
        return None
    match contract.kind.label:
        case fmsave.ContractType.YOUTH:
            return True
        case fmsave.ContractType.FULL_TIME:
            return False
        case fmsave.ContractType.UNKNOWN:
            return None


LEAGUE_NATION_SHARE = 0.9
VACANCY_ROLE_FIELD = "role"
UPCOMING_OPPONENTS_KEPT = 3
RECENT_RESULTS_KEPT = 5
RAW_PERCENT_SCALE = 100
COMPETITION_BAN = "one competition"
NATION_BAN = "some competitions in one country"
EUROPEAN_BAN = "European competitions"
UNKNOWN_BAN = "unknown competitions"


def first_team_fixtures(fixtures: Iterable[fmsave.Fixture]) -> Counter[tuple[int, int]]:
    played: Counter[tuple[int, int]] = Counter()
    for fixture in fixtures:
        if fixture.competition_id is None or fixture.season_start_year is None:
            continue
        for club_uid, slot in (
            (fixture.home_club_uid, fixture.home_team_slot),
            (fixture.away_club_uid, fixture.away_team_slot),
        ):
            if club_uid is not None and slot == 0:
                played[(club_uid, fixture.competition_id)] += 1
    return played


def domestic_competitions(played: Counter[tuple[int, int]], club_nations: dict[int, int | None]) -> set[int]:
    nations: dict[int, Counter[int | None]] = {}
    for club_uid, competition_id in played:
        nations.setdefault(competition_id, Counter())[club_nations.get(club_uid)] += 1
    return {
        competition_id
        for competition_id, found in nations.items()
        if found.most_common(1)[0][0] is not None and found.most_common(1)[0][1] >= LEAGUE_NATION_SHARE * found.total()
    }


def first_team_leagues(fixtures: Iterable[fmsave.Fixture], club_nations: dict[int, int | None]) -> dict[int, int]:
    played = first_team_fixtures(fixtures)
    domestic = domestic_competitions(played, club_nations)
    leagues: dict[int, int] = {}
    for (club_uid, competition_id), _ in played.most_common():
        if competition_id in domestic:
            leagues.setdefault(club_uid, competition_id)
    return leagues


def loan_wage(player: fmsave.Player) -> int | None:
    contract = player.contract
    if contract is None or not player.on_loan:
        return None
    for entry in contract.chain:
        if entry.club_uid == player.club_uid:
            return entry.wage
    return None


def named_traits(player: fmsave.Player) -> tuple[str, ...]:
    return tuple(label(trait.label.name) for trait in player.traits if trait.label is not fmsave.Trait.UNKNOWN)


def ban_label(ban: fmsave.PlayerSuspension) -> str:
    match ban.scope:
        case fmsave.SuspensionScope.COMPETITION:
            return ban.competition_name or COMPETITION_BAN
        case fmsave.SuspensionScope.NATION:
            return NATION_BAN
        case fmsave.SuspensionScope.EUROPE:
            return EUROPEAN_BAN
        case fmsave.SuspensionScope.UNKNOWN:
            return UNKNOWN_BAN


def percent(raw: int) -> int:
    return round(raw / RAW_PERCENT_SCALE)


def nationalities(player: fmsave.Player, nations: dict[int, str]) -> tuple[str, ...]:
    ids = [player.nation_id, *player.second_nation_ids]
    return tuple(dict.fromkeys(nations[uid] for uid in ids if uid is not None and uid in nations))


def to_player(
    player: fmsave.Player, leagues: dict[int, int], records: PlayerRecords, nations: dict[int, str], today: date
) -> Player | None:
    contract = player.contract
    personality = player.personality
    if player.name is None or player.age is None or player.ability.potential is None or personality is None:
        return None
    return Player(
        uid=player.uid,
        name=player.name,
        age=player.age,
        birth_date=player.birth_date,
        club_uid=player.club_uid,
        club_name=player.club_name,
        position_ratings=dataclasses.asdict(player.positions),
        current_ability=player.ability.current,
        potential_ability=player.ability.potential,
        value=known_value(player.transfer_value_state, player.transfer_value),
        wage=contract_wage(contract, today) if contract else None,
        contract_end=contract_end(contract, today) if contract else None,
        on_loan=bool(player.on_loan),
        loan_parent_club_uid=player.loan_parent_club_uid,
        loan_end=player.loan_end,
        attributes=dataclasses.asdict(player.attributes),
        reputation=player.reputation.current,
        professionalism=personality.professionalism,
        ambition=personality.ambition,
        first_team=None if player.team_slot is None else player.team_slot == 0,
        club_reputation=player.club_reputation,
        club_nation_id=player.club_nation_id,
        league_id=leagues.get(player.club_uid) if player.club_uid is not None else None,
        youth_contract=youth_contract(contract),
        release_clauses=release_clauses(contract),
        loan_wage=loan_wage(player),
        adaptability=personality.adaptability,
        loyalty=personality.loyalty,
        pressure=personality.pressure,
        sportsmanship=personality.sportsmanship,
        temperament=personality.temperament,
        controversy=personality.controversy,
        left_foot=player.left_foot,
        right_foot=player.right_foot,
        height_cm=player.height_cm,
        traits=named_traits(player),
        condition=percent(player.raw_condition),
        match_sharpness=percent(player.raw_match_sharpness),
        banned_from=tuple(ban_label(ban) for ban in player.suspensions or ()),
        injury=current.name if (current := records.current_injuries.get(player.uid)) else None,
        injured_until=current.back_on if current else None,
        injuries=records.injuries.get(player.uid, ()),
        season=records.seasons.get(player.uid),
        nationalities=nationalities(player, nations),
        club_country=nations.get(player.club_nation_id) if player.club_nation_id is not None else None,
        squad_status=coded_label(contract.squad_status) if contract else None,
    )


def budget(save: fmsave.Save, club_uid: int) -> Budget:
    months = sorted(save.finances().where(club_uid=club_uid), key=lambda month: month.month)
    if not months:
        return Budget(None, None, None)
    latest = months[-1]
    return Budget(latest.transfer_budget_remaining, latest.wage_budget_weekly, latest.wage_payroll_weekly)


def latest_finances(save: fmsave.Save) -> dict[int, fmsave.FinanceMonth]:
    latest: dict[int, fmsave.FinanceMonth] = {}
    for month in save.finances():
        known = latest.get(month.club_uid)
        if known is None or month.month > known.month:
            latest[month.club_uid] = month
    return latest


def is_manager_job(job: fmsave.JobVacancy) -> bool:
    return job.team_slot == 0 and job.unknown.get(VACANCY_ROLE_FIELD) == fmsave.StaffJob.MANAGER.value


def clubs_with_a_manager(staff: Iterable[fmsave.Staff]) -> set[int]:
    return {
        person.club_uid
        for person in staff
        if person.team_slot == 0 and person.job is not None and person.job.label is fmsave.StaffJob.MANAGER
    }


def open_manager_jobs(
    jobs: Iterable[fmsave.JobVacancy], filled: set[int], managed_club_uid: int
) -> list[fmsave.JobVacancy]:
    latest: dict[int, fmsave.JobVacancy] = {}
    for job in jobs:
        if not is_manager_job(job) or job.club_uid is None or job.club_uid in filled | {managed_club_uid}:
            continue
        known = latest.get(job.club_uid)
        if known is None or (job.advertised_date or date.min) > (known.advertised_date or date.min):
            latest[job.club_uid] = job
    return list(latest.values())


def vacancies(save: fmsave.Save, managed_club_uid: int) -> tuple[Vacancy, ...]:
    clubs = save.clubs()
    finances = latest_finances(save)
    found: list[Vacancy] = []
    for job in open_manager_jobs(save.job_vacancies(), clubs_with_a_manager(save.staff()), managed_club_uid):
        if job.club_uid is None:
            continue
        money = finances.get(job.club_uid)
        found.append(
            Vacancy(
                job.club_uid,
                job.club_name or "unknown",
                clubs.by_uid(job.club_uid).reputation,
                job.advertised_date,
                money.balance if money else None,
                money.transfer_budget_remaining if money else None,
            )
        )
    return tuple(found)


def to_match(fixture: fmsave.Fixture) -> Match | None:
    if fixture.date is None or fixture.home_club_uid is None or fixture.away_club_uid is None:
        return None
    return Match(
        fixture.date, fixture.competition_id, fixture.home_club_uid, fixture.home_club_name or "unknown",
        fixture.away_club_uid, fixture.away_club_name or "unknown", bool(fixture.played), fixture.home_goals,
        fixture.away_goals, bool(fixture.is_neutral_venue), fixture.home_team_slot, fixture.away_team_slot,
    )  # fmt: skip


def first_team_side(fixture: fmsave.Fixture, club_uid: int) -> bool:
    return (fixture.home_club_uid == club_uid and fixture.home_team_slot == 0) or (
        fixture.away_club_uid == club_uid and fixture.away_team_slot == 0
    )


def first_team_matches(fixtures: list[fmsave.Fixture], club_uid: int) -> list[Match]:
    found: list[Match] = []
    for fixture in fixtures:
        match = to_match(fixture) if first_team_side(fixture, club_uid) else None
        if match is not None:
            found.append(match)
    return sorted(found, key=lambda match: match.day)


def matches_kept(fixtures: Iterable[fmsave.Fixture], club_uid: int, today: date) -> tuple[Match, ...]:
    listed = list(fixtures)
    ours = first_team_matches(listed, club_uid)
    upcoming = [match for match in ours if not match.played and match.day >= today][:UPCOMING_OPPONENTS_KEPT]
    opponents = {m.away_club_uid if m.home_club_uid == club_uid else m.home_club_uid for m in upcoming}
    recent: list[Match] = []
    for opponent in opponents:
        played = [match for match in first_team_matches(listed, opponent) if match.played]
        recent.extend(played[-RECENT_RESULTS_KEPT:])
    return tuple(dict.fromkeys([*ours, *recent]))


def read_snapshot(path: Path) -> Snapshot:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", fmsave.FmsaveWarning)
        with fmsave.open(path) as save:
            clubs = save.managed_clubs()
            if not clubs:
                raise UnreadableSave(f"{path.name} has no managed club; mezzala needs a manager in a job.")
            club = clubs[0]
            game_date = save.info.game_date
            if game_date is None:
                raise UnreadableSave(f"{path.name} has no in-game date.")
            leagues = first_team_leagues(save.fixtures(), {c.uid: c.nation_id for c in save.clubs()})
            records = player_records(save, game_date)
            nations = {nation.nation_id: nation_name(nation.database_id) for nation in save.nations()}
            converted = (to_player(player, leagues, records, nations, game_date) for player in save.players())
            players = tuple(player for player in converted if player is not None)
            managed = save.clubs().by_uid(club.club_uid)
            reputation = managed.reputation
            if reputation is None:
                raise UnreadableSave(f"{path.name} has no reputation for {club.club_name}.")
            return Snapshot(
                game_date,
                club.club_uid,
                club.club_name,
                reputation,
                managed.nation_id,
                budget(save, club.club_uid),
                players,
                vacancies(save, club.club_uid),
                matches_kept(save.fixtures(), club.club_uid, game_date),
                club_staff(save, club.club_uid),
                first_team_tactics(save, club.club_uid),
                mentoring_groups(save, club.club_uid),
            )
