from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Annotated

import fmsave
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mezzala.core.formations import DEFAULT_FORMATION, Formation, saved_formation
from mezzala.core.lookup import AmbiguousPlayer, PlayerNotFound, find_player
from mezzala.core.money import format_money, format_weekly_wage, stored_from_pounds
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import ACCOMPLISHED_POSITION_RATING, NATURAL_POSITION_RATING, PositionGroup
from mezzala.core.reach import REPUTATION_REACH
from mezzala.core.rejections import without_rejected
from mezzala.core.squad import belongs_to_club, owned_players, plays_for_club, squad_level
from mezzala.core.view import View, shows_hidden_information
from mezzala.save.career import Career, Current
from mezzala.save.reader import UnreadableSave
from mezzala.save.rejections import RejectionStore
from mezzala.save.store import FileStamp
from mezzala.save.watchlist import WatchlistStore
from mezzala.tools.compare_formations import FormationComparison, compare_formations
from mezzala.tools.contract_watch import ContractWatch, contract_watch
from mezzala.tools.development_check import CheckScope, DevelopmentCheck, development_check
from mezzala.tools.development_plan import DevelopmentPlan, development_plan
from mezzala.tools.dressing_room import DressingRoom, dressing_room
from mezzala.tools.find_players import FoundPlayers, PlayerSearch, SearchScope, SortBy, find_players
from mezzala.tools.fitness import FitnessReport, fitness
from mezzala.tools.league_comparison import LeagueComparison, league_comparison
from mezzala.tools.league_values import LeagueValues, league_values
from mezzala.tools.next_job import NextJob, next_job
from mezzala.tools.next_opponent import NextOpponent, next_opponent
from mezzala.tools.performance import Performance, PerformanceScope, PerformanceSearch, PerformanceSort, performance
from mezzala.tools.player_profile import PlayerProfiles, player_profiles
from mezzala.tools.positional_fit import PositionalFit, positional_fit
from mezzala.tools.regen_intake import RegenIntake, regen_intake
from mezzala.tools.rejections import NotRejected, RejectedList, find_rejected_entry, rejected_list, rejected_record
from mezzala.tools.relegated_clubs import RelegatedClubs, relegated_clubs
from mezzala.tools.replacement import Limits, Replacements, find_replacements
from mezzala.tools.risers import RiserFilters, Risers, RiserScope, find_risers
from mezzala.tools.sell_high import SellHigh, sell_high
from mezzala.tools.shortlist import Shortlist, shortlist
from mezzala.tools.squad_gaps import SquadGaps, squad_gaps
from mezzala.tools.squad_list import SquadList, squad_list
from mezzala.tools.squad_profile import SquadProfile, squad_profile
from mezzala.tools.squad_progress import SquadProgress, squad_progress
from mezzala.tools.staff_review import StaffReview, staff_review
from mezzala.tools.training_plan import TrainingPlan, training_plan
from mezzala.tools.wage_review import WageReview, wage_review
from mezzala.tools.watchlist import NotWatched, Watchlist, find_watched_entry, watched_record, watchlist
from mezzala.tools.what_changed import WhatChanged, what_changed

DEFAULT_LIMIT = 10
RISER_CA_BELOW_SQUAD_LEVEL = 20
RISER_TARGET_MAX_AGE = 23
RELEGATION_LOOKBACK_DAYS = 300
PERFORMANCE_MIN_MINUTES = 450
NANOSECONDS_PER_SECOND = 1_000_000_000
WRITTEN_FORMAT = "%Y-%m-%d %H:%M UTC"
DEVELOPMENT_MIN_PA = 150
REGEN_MIN_PA = 120
RISER_MIN_CA_GAIN = 3

INSTRUCTIONS = f"""\
mezzala reads the manager's Football Manager 27 save and answers squad, formation and transfer questions about it.
Every answer starts with the save's in-game date and club, and when the save file was written (save_written).
mezzala sees only what FM wrote at that save: budgets, transfers or squad changes made in the game since then do not
show until the manager saves again, so say so when an answer looks out of date. Each call checks the save file
and stores a new snapshot when it has changed, so growth compares real snapshots once there are two or more.
Money is in pounds. Fees are FM's transfer values, because asking prices are not stored in the save.
Current and potential ability (CA, PA) are FM's hidden 1-200 numbers.
find_players searches every player in the save with filters and sorts, and answers most recruitment
questions. shortlist builds a transfer shortlist within the budgets. wage_review, development_plan and
league_comparison cover wages, young players and how the squad compares with its league. squad lists
the players. compare_formations ranks formations by how well the squad fits them and shows each eleven.
what_changed, development_check, squad_progress and the watchlist tools (watch_player, unwatch_player,
watchlist) work from history and say so when there is only one snapshot. reject_player keeps a player who
has said no out of recruitment answers; unreject_player and rejected_players manage that list. next_job,
league_values and relegated_clubs cover managerial vacancies, the best-value leagues and clubs that dropped a league.
player_profile shows one player in full, or two side by side. training_plan suggests one of the club's players'
position, attribute focus, intensity, traits and mentors. dressing_room ranks captains and flags troublemakers.
fitness lists injuries, bans, injury risks, condition and sharpness. staff_review rates the backroom staff.
performance ranks season stats: who plays above or below their ability, finishing against xG, output per 90.
squad_profile, positional_fit and next_opponent support tactics and match preparation; the save stores formations
but not roles or instructions, so suggest tactics from the attributes they report.
Positions are natural (FM rating {NATURAL_POSITION_RATING}+) or accomplished
({ACCOMPLISHED_POSITION_RATING}-{NATURAL_POSITION_RATING - 1}). Ask the manager which formation they
play if it matters. Tools that take one default to the shape of the first-team tactic saved in the game, and to
{DEFAULT_FORMATION.value} when no saved tactic can be read; the answer's notes say which."""

SPOILER_FREE_INSTRUCTIONS = """
Fog of war is on: the manager does not want to see what FM hides. Ability and potential come as star ratings
(5 stars is the best in the world), and hidden attributes and personality numbers are left out. Never state,
estimate or work back to CA or PA numbers, and talk about players the way FM's coaches and scouts would."""


def instructions_for(view: View) -> str:
    match view:
        case View.FULL:
            return INSTRUCTIONS
        case View.SPOILER_FREE:
            return INSTRUCTIONS + SPOILER_FREE_INSTRUCTIONS


FIND_PLAYERS_DESCRIPTION = f"""\
Search every player in the save with filters and a sort. Money is in pounds (max_wage weekly).

Sorts: "value for money" puts players valued lowest against similar players first; "above league level"
puts players furthest above their league's first-team median CA first; "position attributes" ranks the
key attributes for the position (combine with max_ca to find attributes ahead of ability); "most
overpaid" ranks wages against similar players.

Who: scope "elsewhere" (default) searches other clubs and free agents, "own" your club, "everyone" the
whole save. position matches players natural or accomplished there (FM rating 15 or more); natural_only
keeps naturals (18 or more). nationality matches a first or second nationality, such as "Republic of
Ireland"; work_permit_free keeps British and Irish players, who need no UK work permit. free_agents_only
and clubs_only keep or leave out players without a club.

Where: country is where the club plays (Cardiff count as England); division_level is 1 for a country's
top flight, estimated from first-team strength because the save names no leagues; league matches part
of a league's name, such as a club in it. reserves_only keeps players outside their club's first team;
bigger_clubs_only keeps clubs with a higher reputation than yours. within_reach keeps players whose
reputation is at most your club's plus {REPUTATION_REACH} (results show both), so a move is realistic
on paper, though a player may still refuse; set it false for questions like the best players in the world.

Availability: the save does not record transfer or loan listing; fringe_only keeps players whose
contract squad status says their club does not count on them (surplus, fringe, backup), the likeliest
to be listed or loaned."""


@dataclass(frozen=True)
class SaveContext:
    save: str
    game_date: str
    club: str
    club_reputation: int
    save_written: str
    transfer_budget: str
    wage_headroom: str
    snapshots: int
    notes: list[str]


@dataclass(frozen=True)
class SnapshotReport:
    context: SaveContext
    players: int
    snapshot_dates: list[str]


@dataclass(frozen=True)
class SquadReport:
    context: SaveContext
    result: SquadList


@dataclass(frozen=True)
class FoundPlayersReport:
    context: SaveContext
    result: FoundPlayers


@dataclass(frozen=True)
class ShortlistReport:
    context: SaveContext
    result: Shortlist


@dataclass(frozen=True)
class WageReviewReport:
    context: SaveContext
    result: WageReview


@dataclass(frozen=True)
class DevelopmentPlanReport:
    context: SaveContext
    result: DevelopmentPlan


@dataclass(frozen=True)
class LeagueComparisonReport:
    context: SaveContext
    result: LeagueComparison


@dataclass(frozen=True)
class WhatChangedReport:
    context: SaveContext
    result: WhatChanged


@dataclass(frozen=True)
class WatchlistReport:
    context: SaveContext
    result: Watchlist


@dataclass(frozen=True)
class DevelopmentCheckReport:
    context: SaveContext
    result: DevelopmentCheck


@dataclass(frozen=True)
class SquadProgressReport:
    context: SaveContext
    result: SquadProgress


@dataclass(frozen=True)
class NextJobReport:
    context: SaveContext
    result: NextJob


@dataclass(frozen=True)
class LeagueValuesReport:
    context: SaveContext
    result: LeagueValues


@dataclass(frozen=True)
class RelegatedClubsReport:
    context: SaveContext
    result: RelegatedClubs


@dataclass(frozen=True)
class SquadProfileReport:
    context: SaveContext
    result: SquadProfile


@dataclass(frozen=True)
class PositionalFitReport:
    context: SaveContext
    result: PositionalFit


@dataclass(frozen=True)
class NextOpponentReport:
    context: SaveContext
    result: NextOpponent


@dataclass(frozen=True)
class FormationReport:
    context: SaveContext
    result: FormationComparison


@dataclass(frozen=True)
class SquadGapsReport:
    context: SaveContext
    result: SquadGaps


@dataclass(frozen=True)
class ReplacementReport:
    context: SaveContext
    result: Replacements


@dataclass(frozen=True)
class RisersReport:
    context: SaveContext
    result: Risers


@dataclass(frozen=True)
class SellHighReport:
    context: SaveContext
    result: SellHigh


@dataclass(frozen=True)
class ContractWatchReport:
    context: SaveContext
    result: ContractWatch


@dataclass(frozen=True)
class PlayerProfileReport:
    context: SaveContext
    result: PlayerProfiles


@dataclass(frozen=True)
class TrainingPlanReport:
    context: SaveContext
    result: TrainingPlan


@dataclass(frozen=True)
class DressingRoomReport:
    context: SaveContext
    result: DressingRoom


@dataclass(frozen=True)
class FitnessToolReport:
    context: SaveContext
    result: FitnessReport


@dataclass(frozen=True)
class StaffReviewReport:
    context: SaveContext
    result: StaffReview


@dataclass(frozen=True)
class PerformanceReport:
    context: SaveContext
    result: Performance


@dataclass(frozen=True)
class RejectedReport:
    context: SaveContext
    result: RejectedList


@dataclass(frozen=True)
class RegenIntakeReport:
    context: SaveContext
    result: RegenIntake


def written_at(stamp: FileStamp | None) -> str:
    if stamp is None:
        return "unknown"
    return datetime.fromtimestamp(stamp.mtime_ns / NANOSECONDS_PER_SECOND, UTC).strftime(WRITTEN_FORMAT)


def save_context(current: Current, notes: list[str] | None = None) -> SaveContext:
    snapshot = current.snapshot
    return SaveContext(
        save=current.save_path.name,
        game_date=snapshot.game_date.isoformat(),
        club=snapshot.club_name,
        club_reputation=snapshot.club_reputation,
        save_written=written_at(current.written),
        transfer_budget=format_money(snapshot.budget.transfer_remaining),
        wage_headroom=format_weekly_wage(snapshot.budget.wage_headroom_weekly),
        snapshots=current.snapshot_count,
        notes=[*current.notes, *(notes or [])],
    )


def optional_stored(pounds: float | None) -> int | None:
    return None if pounds is None else stored_from_pounds(pounds)


def read_current(career: Career) -> Current:
    try:
        return career.current()
    except (fmsave.FmsaveError, UnreadableSave, OSError) as error:
        raise ToolError(f"Could not read the save: {error}") from error


def target_player(snapshot: Snapshot, name: str, club: str | None = None) -> Player:
    try:
        return find_player(snapshot, name, club)
    except (PlayerNotFound, AmbiguousPlayer) as error:
        raise ToolError(str(error)) from error


def refuse_hidden_filters(view: View, filters: dict[str, bool]) -> None:
    used = [name for name, is_set in filters.items() if is_set]
    if used and not shows_hidden_information(view):
        raise ToolError(f"Fog of war is on, so {', '.join(used)} cannot be used: it filters on hidden ability.")


def with_formation(current: Current, asked: Formation | None) -> tuple[Formation, SaveContext]:
    if asked is not None:
        return asked, save_context(current)
    saved = saved_formation(current.snapshot.tactics)
    if saved is None and current.snapshot.tactics:
        unmatched = (
            f"Your saved tactic '{current.snapshot.tactics[0].name}' has a shape mezzala does not model, so "
            f"{DEFAULT_FORMATION.value} is used; say which formation you play for a closer answer."
        )
        return DEFAULT_FORMATION, save_context(current, [unmatched])
    if saved is None:
        return DEFAULT_FORMATION, save_context(current)
    formation, tactic = saved
    return formation, save_context(current, [f"Formation {formation.value}, from your saved tactic '{tactic.name}'."])


def riser_defaults(
    scope: RiserScope, snapshot: Snapshot, min_ca: int | None, max_age: int | None
) -> tuple[float, int | None]:
    match scope:
        case RiserScope.ELSEWHERE:
            floor = squad_level(snapshot) - RISER_CA_BELOW_SQUAD_LEVEL if min_ca is None else min_ca
            return floor, RISER_TARGET_MAX_AGE if max_age is None else max_age
        case RiserScope.OWN | RiserScope.FORMER:
            return (0 if min_ca is None else min_ca), max_age


def one_of(choices: type[StrEnum]) -> str:
    return "One of: " + ", ".join(f'"{choice.value}"' for choice in choices)


FORMATION_DEFAULT = f"Defaults to the saved first-team tactic's shape, else {DEFAULT_FORMATION.value}."
FormationChoice = Annotated[Formation | None, Field(description=f"{FORMATION_DEFAULT} {one_of(Formation)}")]
FormationChoices = Annotated[list[Formation] | None, Field(description=f"Defaults to all. {one_of(Formation)}")]
PositionChoice = Annotated[PositionGroup | None, Field(description=one_of(PositionGroup))]
ClubChoice = Annotated[
    str | None,
    Field(
        description="The club the player is at now, to tell apart players who share a name. Leave it out "
        "unless an answer says the name is ambiguous."
    ),
]
ScopeChoice = Annotated[RiserScope, Field(description=one_of(RiserScope))]
SearchScopeChoice = Annotated[SearchScope, Field(description=one_of(SearchScope))]
SortChoice = Annotated[SortBy, Field(description=one_of(SortBy))]
CheckScopeChoice = Annotated[CheckScope, Field(description=one_of(CheckScope))]
PerformanceScopeChoice = Annotated[PerformanceScope, Field(description=one_of(PerformanceScope))]
PerformanceSortChoice = Annotated[PerformanceSort, Field(description=one_of(PerformanceSort))]


def create_server(
    career: Career, watched: WatchlistStore, rejections: RejectionStore, view: View = View.FULL
) -> MCPServer:
    def recruitable(current: Current) -> Snapshot:
        return without_rejected(current.snapshot, rejections.entries(current.career))

    server = MCPServer("mezzala", instructions=instructions_for(view))

    @server.tool()
    def snapshot() -> SnapshotReport:
        """Read the save now, store a snapshot if it changed, and list the in-game dates with snapshots."""
        current = read_current(career)
        dates = [*career.earlier_dates(current), current.snapshot.game_date]
        return SnapshotReport(save_context(current), len(current.snapshot.players), [d.isoformat() for d in dates])

    @server.tool(name="squad")
    def squad_tool() -> SquadReport:
        """Everyone available to the club, loan players included, best first, with natural and accomplished
        positions; plus the club's own players who are out on loan."""
        current = read_current(career)
        return SquadReport(save_context(current), squad_list(current.snapshot, view))

    @server.tool(name="find_players", description=FIND_PLAYERS_DESCRIPTION)
    def find_players_tool(
        sort_by: SortChoice = SortBy.CURRENT_ABILITY,
        scope: SearchScopeChoice = SearchScope.ELSEWHERE,
        position: PositionChoice = None,
        natural_only: bool = False,
        min_age: int | None = None,
        max_age: int | None = None,
        min_ca: int | None = None,
        max_ca: int | None = None,
        min_pa: int | None = None,
        max_fee: float | None = None,
        max_wage: float | None = None,
        free_agents_only: bool = False,
        clubs_only: bool = False,
        contract_ending_within_months: int | None = None,
        max_release_clause: float | None = None,
        youth_contract_only: bool = False,
        nationality: str | None = None,
        work_permit_free: bool = False,
        country: str | None = None,
        division_level: int | None = None,
        league: str | None = None,
        fringe_only: bool = False,
        reserves_only: bool = False,
        bigger_clubs_only: bool = False,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> FoundPlayersReport:
        current = read_current(career)
        refuse_hidden_filters(
            view, {"min_ca": min_ca is not None, "max_ca": max_ca is not None, "min_pa": min_pa is not None}
        )
        search = PlayerSearch(
            scope=scope,
            position=position,
            natural_only=natural_only,
            min_age=min_age,
            max_age=max_age,
            min_ca=min_ca,
            max_ca=max_ca,
            min_pa=min_pa,
            max_fee=optional_stored(max_fee),
            max_wage=optional_stored(max_wage),
            free_agents_only=free_agents_only,
            clubs_only=clubs_only,
            contract_ending_within_months=contract_ending_within_months,
            max_release_clause=optional_stored(max_release_clause),
            youth_contract_only=youth_contract_only,
            nationality=nationality,
            work_permit_free_only=work_permit_free,
            country=country,
            division_level=division_level,
            league=league,
            fringe_only=fringe_only,
            reserves_only=reserves_only,
            bigger_clubs_only=bigger_clubs_only,
            within_reach=within_reach,
            sort_by=sort_by,
            limit=limit,
        )
        return FoundPlayersReport(save_context(current), find_players(recruitable(current), search, view))

    @server.tool(name="shortlist")
    def shortlist_tool(
        formation: FormationChoice = None,
        transfer_budget: float | None = None,
        weekly_wage_budget: float | None = None,
    ) -> ShortlistReport:
        """A realistic transfer shortlist: for each position squad_gaps flags, worst first, the best player
        within reach who beats the current starter, spending down the transfer budget and weekly wage room as it
        goes, with two alternatives each. Budgets are in pounds and default to the club's remaining transfer
        budget and wage room. A target is expected to want at least the going rate for his ability at clubs of
        similar reputation (in your country first). Targets are young enough not to be ageing for at least two
        seasons, and among targets within a few CA of the best the one using the smallest share of the tighter
        budget wins."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        budget = current.snapshot.budget
        fees = optional_stored(transfer_budget) if transfer_budget is not None else budget.transfer_remaining
        wages = optional_stored(weekly_wage_budget) if weekly_wage_budget is not None else budget.wage_headroom_weekly
        return ShortlistReport(context, shortlist(recruitable(current), formation, fees, wages, view))

    @server.tool(name="wage_review")
    def wage_review_tool(formation: FormationChoice = None) -> WageReviewReport:
        """Everyone the club pays, at what it actually pays them: the wage bill, players paid well above others
        of similar CA, age and potential, and surplus players (not in the best eleven and not needed for cover
        anywhere in the formation, and not a young prospect) with the weekly saving if they all went."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return WageReviewReport(context, wage_review(current.snapshot, formation, view))

    @server.tool(name="development_plan")
    def development_plan_tool(formation: FormationChoice = None) -> DevelopmentPlanReport:
        """The club's players aged 21 or under: who is ready for the first team (within a few CA of the weakest
        starter in a position he can play), who to loan out for games (not ready, old enough, room to grow),
        who is already on loan, and the five to focus on: potential that reaches the first eleven's level, ranked
        by potential then projected growth."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return DevelopmentPlanReport(context, development_plan(current.snapshot, formation, view))

    @server.tool(name="league_comparison")
    def league_comparison_tool(formation: FormationChoice = None) -> LeagueComparisonReport:
        """How the club's squad compares with the rest of its league: every club ranked by the average CA of its
        best eleven for the formation, with first-team value, and position by position the club's starters
        against the league median and the best club there."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return LeagueComparisonReport(context, league_comparison(current.snapshot, formation, view))

    @server.tool(name="what_changed")
    def what_changed_tool() -> WhatChangedReport:
        """What has changed since the previous snapshot: budget, players who joined or left the club, the club's
        players whose CA, contract or value moved, new regens, and big transfers elsewhere."""
        current = read_current(career)
        return WhatChangedReport(save_context(current), what_changed(current.snapshot, career.previous(current), view))

    @server.tool(name="watch_player")
    def watch_player_tool(player: str, club: ClubChoice = None, note: str = "") -> WatchlistReport:
        """Add a player to mezzala's watchlist (FM's own shortlist is not readable from the save). His value, CA and
        club are recorded so later calls can show how he has changed and whether he has become cheaper. club
        narrows the search when players share a name. Watching a player again keeps his baseline and only
        updates the note (an empty note keeps the old one)."""
        current = read_current(career)
        target = target_player(current.snapshot, player, club)
        watched.add(current.career, watched_record(target, current.snapshot, note))
        return WatchlistReport(
            save_context(current), watchlist(current.snapshot, watched.entries(current.career), view)
        )

    @server.tool(name="unwatch_player")
    def unwatch_player_tool(player: str, club: ClubChoice = None) -> WatchlistReport:
        """Remove a player from mezzala's watchlist. club narrows the match when watched players share a name."""
        current = read_current(career)
        try:
            entry = find_watched_entry(watched.entries(current.career), player, club)
        except NotWatched as error:
            raise ToolError(str(error)) from error
        watched.remove(current.career, entry.uid)
        return WatchlistReport(
            save_context(current), watchlist(current.snapshot, watched.entries(current.career), view)
        )

    @server.tool(name="watchlist")
    def watchlist_tool() -> WatchlistReport:
        """mezzala's watchlist: each player now, what has changed since he was added, and whether he has become
        cheaper (value down, contract ending within a year, now a free agent, or a release clause that applies)."""
        current = read_current(career)
        return WatchlistReport(
            save_context(current), watchlist(current.snapshot, watched.entries(current.career), view)
        )

    @server.tool(name="development_check")
    def development_check_tool(
        scope: CheckScopeChoice = CheckScope.OWN,
        since: date | None = None,
        min_pa: int = DEVELOPMENT_MIN_PA,
        limit: int = DEFAULT_LIMIT,
    ) -> DevelopmentCheckReport:
        """Against an earlier snapshot (since is an in-game date; defaults to the oldest): players aged 21 or under
        with potential of at least min_pa who are gaining less than half the CA projected for them, and players
        who have lost 3 or more CA. scope "own" is the club's players, "everyone" the whole save."""
        current = read_current(career)
        refuse_hidden_filters(view, {"min_pa": min_pa != DEVELOPMENT_MIN_PA})
        result = development_check(current.snapshot, career.baseline(current, since), scope, min_pa, limit, view)
        return DevelopmentCheckReport(save_context(current), result)

    @server.tool(name="squad_progress")
    def squad_progress_tool(formation: FormationChoice = None) -> SquadProgressReport:
        """How the squad has changed since the first snapshot of the save (usually when mezzala was first used):
        best eleven, league rank, size, age, value and wage bill then and now, and the most improved players."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        first = career.baseline(current, None)
        return SquadProgressReport(context, squad_progress(current.snapshot, first, formation, view))

    @server.tool(name="next_job")
    def next_job_tool(
        formation: FormationChoice = None, bigger_only: bool = False, limit: int = DEFAULT_LIMIT
    ) -> NextJobReport:
        """Open first-team manager jobs in the save, biggest club first: each club's reputation against yours,
        its league level, the strength of its best eleven, and its money where the save has finances."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return NextJobReport(context, next_job(current.snapshot, formation, bigger_only, limit, view))

    @server.tool(name="league_values")
    def league_values_tool(limit: int = DEFAULT_LIMIT) -> LeagueValuesReport:
        """Which leagues offer the best value: leagues whose first-team players cost least against similar players
        (same CA, age and potential) across the save, cheapest first, with each league's level and median value.
        Leagues are named after their three biggest clubs."""
        current = read_current(career)
        return LeagueValuesReport(save_context(current), league_values(current.snapshot, limit, view))

    @server.tool(name="relegated_clubs")
    def relegated_clubs_tool(since: date | None = None) -> RelegatedClubsReport:
        """Clubs now in a weaker league than at an earlier snapshot, with their best players within reach. since
        is an in-game date; by default the comparison is with the latest snapshot about a season earlier. Needs a
        snapshot from before the season changed."""
        current = read_current(career)
        lookback = since or current.snapshot.game_date - timedelta(days=RELEGATION_LOOKBACK_DAYS)
        result = relegated_clubs(recruitable(current), career.baseline(current, lookback), view)
        return RelegatedClubsReport(save_context(current), result)

    @server.tool(name="squad_profile")
    def squad_profile_tool(formation: FormationChoice = None) -> SquadProfileReport:
        """The best eleven's attribute strengths and weaknesses (pace, physical, aerial, defending, passing,
        creativity, finishing, work rate, wide play, decision making) against the other clubs' best elevens in
        your league. Use it to suggest tactics; the save's tactic itself cannot be read."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return SquadProfileReport(context, squad_profile(current.snapshot, formation))

    @server.tool(name="positional_fit")
    def positional_fit_tool(formation: FormationChoice = None) -> PositionalFitReport:
        """Whether the best eleven's players suit the positions they are picked in: each starter's key-attribute
        score there, and starters whose attributes suit another position they can play noticeably better."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return PositionalFitReport(context, positional_fit(current.snapshot, formation))

    @server.tool(name="next_opponent")
    def next_opponent_tool(formation: FormationChoice = None) -> NextOpponentReport:
        """The club's next first-team fixture and an analysis of the opponent: their likely formation and best
        eleven, key players, how their outfield attributes compare with your eleven's, and their recent results.
        Use it to suggest tactical adjustments."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return NextOpponentReport(context, next_opponent(current.snapshot, formation, view))

    @server.tool(name="compare_formations")
    def compare_formations_tool(formations: FormationChoices = None) -> FormationReport:
        """Rank formations by how well the squad fits them: for each, the best eleven (each player once, with
        natural or accomplished fit), its score, accomplished (non-natural) starters, empty places, weakest place,
        and whether it is effectively tied with the best."""
        current = read_current(career)
        chosen = list(dict.fromkeys(formations)) if formations else list(Formation)
        return FormationReport(save_context(current), compare_formations(current.snapshot, chosen, view))

    @server.tool(name="squad_gaps")
    def squad_gaps_tool(formation: FormationChoice = None) -> SquadGapsReport:
        """Where the squad is thin, ageing, leaving, weak or has no young successor, by position for a formation."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return SquadGapsReport(context, squad_gaps(current.snapshot, formation, view))

    @server.tool()
    def find_replacement(
        player: str,
        club: ClubChoice = None,
        max_fee: float | None = None,
        max_age: int | None = None,
        max_wage: float | None = None,
        position: PositionChoice = None,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> ReplacementReport:
        """Players outside the club with a similar attribute profile who could replace `player`, usually one
        of yours who is leaving or not good enough (he can be anyone in the save).

        max_fee and max_wage (weekly) are in pounds. max_fee defaults to the club's remaining transfer budget;
        free agents always qualify. position defaults to the player's main position. within_reach keeps
        players whose reputation is close enough to the club's that a move is realistic."""
        current = read_current(career)
        snapshot = current.snapshot
        target = target_player(snapshot, player, club)
        fee_cap = optional_stored(max_fee) if max_fee is not None else snapshot.budget.transfer_remaining
        limits = Limits(fee_cap, max_age, optional_stored(max_wage), within_reach)
        result = find_replacements(recruitable(current), target, limits, limit, view, position)
        return ReplacementReport(save_context(current), result)

    @server.tool()
    def risers(
        scope: ScopeChoice = RiserScope.ELSEWHERE,
        since: date | None = None,
        min_ca_gain: float = RISER_MIN_CA_GAIN,
        min_ca: int | None = None,
        max_age: int | None = None,
        max_fee: float | None = None,
        position: PositionChoice = None,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> RisersReport:
        """Players whose current ability is rising fastest.

        scope: elsewhere (transfer targets), own (your players) or former (players who have left you, to spot
        sales made too early). since is an in-game date; it defaults to the oldest snapshot. With one snapshot,
        gains are projected rather than observed. max_fee is in pounds and defaults to the remaining transfer budget;
        free agents always qualify. For elsewhere, min_ca defaults to 20 below the level of the current
        first eleven and max_age to 23; for own and former there is no floor or age limit unless given."""
        current = read_current(career)
        refuse_hidden_filters(view, {"min_ca": min_ca is not None, "min_ca_gain": min_ca_gain != RISER_MIN_CA_GAIN})
        floor, age_limit = riser_defaults(scope, current.snapshot, min_ca, max_age)
        fee_cap = optional_stored(max_fee) if max_fee is not None else current.snapshot.budget.transfer_remaining
        filters = RiserFilters(scope, min_ca_gain, floor, within_reach, age_limit, fee_cap, position)
        result = find_risers(recruitable(current), career.baseline(current, since), filters, limit, view)
        return RisersReport(save_context(current), result)

    @server.tool(name="sell_high")
    def sell_high_tool(limit: int = DEFAULT_LIMIT) -> SellHighReport:
        """Your players worth selling now: past peak age, at their ceiling, valued above similar players,
        contract running down, or (with history) value falling or ability stalled while value rose."""
        current = read_current(career)
        owned = {player.uid for player in owned_players(current.snapshot)}
        result = sell_high(current.snapshot, career.past_players(current, owned), limit, view)
        return SellHighReport(save_context(current), result)

    @server.tool(name="contract_watch")
    def contract_watch_tool(
        within_months: int = 12,
        max_age: int | None = None,
        formation: FormationChoice = None,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> ContractWatchReport:
        """Your contracts and loans ending soon, plus free agents and players elsewhere with expiring contracts
        who would beat your current starter somewhere in the formation."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        result = contract_watch(recruitable(current), formation, within_months, max_age, within_reach, limit, view)
        return ContractWatchReport(context, result)

    @server.tool(name="regen_intake")
    def regen_intake_tool(
        since: date | None = None,
        since_last_save: bool = False,
        min_pa: int = REGEN_MIN_PA,
        unsigned_only: bool = False,
        limit: int = 20,
    ) -> RegenIntakeReport:
        """Newly generated youth players (regens) since an earlier snapshot, best potential first, and the clubs
        whose intakes produced the best of them. The baseline is the oldest snapshot (the best regens of the save
        so far), the snapshot at or before since, or with since_last_save the previous snapshot. unsigned_only
        keeps regens on youth contracts or without a club, i.e. not yet on professional terms."""
        current = read_current(career)
        refuse_hidden_filters(view, {"min_pa": min_pa != REGEN_MIN_PA})
        baseline = career.previous(current) if since_last_save else career.baseline(current, since)
        result = regen_intake(current.snapshot, baseline, min_pa, unsigned_only, limit, view)
        return RegenIntakeReport(save_context(current), result)

    @server.tool(name="player_profile")
    def player_profile_tool(
        player: str, club: ClubChoice = None, compare_with: str | None = None, compare_club: ClubChoice = None
    ) -> PlayerProfileReport:
        """One player's full profile, or two side by side with compare_with: attributes grouped as FM groups
        them, hidden attributes and personality (left out under fog of war), feet, height, traits, the positions
        he can play with a key-attribute score for each, condition, sharpness, injuries, bans, this season's
        stats, and what has changed since the first snapshot. Pass club to tell apart players with the same name."""
        current = read_current(career)
        chosen = [target_player(current.snapshot, player, club)]
        if compare_with is not None:
            chosen.append(target_player(current.snapshot, compare_with, compare_club))
        result = player_profiles(chosen, career.baseline(current, None), view)
        return PlayerProfileReport(save_context(current), result)

    @server.tool(name="training_plan")
    def training_plan_tool(player: str, club: ClubChoice = None, position: PositionChoice = None) -> TrainingPlanReport:
        """A training plan for one of the club's players: the position to train him for (his best fit unless
        position is given), the key attributes to set as his additional focus, whether to lower his intensity,
        traits to learn or unlearn, his mentoring group and senior players who would make good mentors."""
        current = read_current(career)
        target = target_player(current.snapshot, player, club)
        if not (
            plays_for_club(target, current.snapshot.club_uid) or belongs_to_club(target, current.snapshot.club_uid)
        ):
            raise ToolError(
                f"{target.name} is not at {current.snapshot.club_name}; training plans are for your players."
            )
        return TrainingPlanReport(save_context(current), training_plan(target, current.snapshot, position, view))

    @server.tool(name="dressing_room")
    def dressing_room_tool() -> DressingRoomReport:
        """Who should captain the club, from leadership, determination and personality, and which players could
        unsettle the dressing room: volatile, hot-headed, unprofessional, or ambitious enough to push for a move."""
        current = read_current(career)
        return DressingRoomReport(save_context(current), dressing_room(current.snapshot))

    @server.tool(name="fitness")
    def fitness_tool(formation: FormationChoice = None) -> FitnessToolReport:
        """Who is injured or banned, which starters in the best eleven are injury risks, and who is low on
        condition or match sharpness."""
        current = read_current(career)
        formation, context = with_formation(current, formation)
        return FitnessToolReport(context, fitness(current.snapshot, formation, view))

    @server.tool(name="staff_review")
    def staff_review_tool() -> StaffReviewReport:
        """The backroom staff: the best coaching rating in each training area, the best scouting judgement of
        ability and potential, physio and sports science, and which coaching areas are weak enough to hire for."""
        current = read_current(career)
        return StaffReviewReport(save_context(current), staff_review(current.snapshot))

    @server.tool(name="performance")
    def performance_tool(
        sort_by: PerformanceSortChoice = PerformanceSort.ABOVE_HIS_LEVEL,
        scope: PerformanceScopeChoice = PerformanceScope.OWN,
        min_minutes: int = PERFORMANCE_MIN_MINUTES,
        position: PositionChoice = None,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> PerformanceReport:
        """Rank players on this season's stats: average rating against players of similar ability (who is
        playing above or below his level), goals against expected goals (clinical or wasteful finishers), and
        goals, assists, key passes or tackles and interceptions per 90. scope "own" is your club, "elsewhere"
        scouts other clubs (within_reach keeps realistic targets). Leagues between seasons have no stats yet."""
        current = read_current(career)
        search = PerformanceSearch(scope, sort_by, min_minutes, position, within_reach, limit)
        return PerformanceReport(save_context(current), performance(recruitable(current), search, view))

    @server.tool(name="reject_player")
    def reject_player_tool(player: str, club: ClubChoice = None, note: str = "") -> RejectedReport:
        """Mark a player as rejected, for example one who refused to talk, so find_players, shortlist,
        find_replacement, contract_watch, risers, performance and relegated_clubs stop suggesting him."""
        current = read_current(career)
        target = target_player(current.snapshot, player, club)
        if target.club_uid == current.snapshot.club_uid:
            raise ToolError(
                f"{target.name} plays for {current.snapshot.club_name}; only other clubs' players can be rejected."
            )
        rejections.add(current.career, rejected_record(target, current.snapshot, note))
        return RejectedReport(save_context(current), rejected_list(rejections.entries(current.career)))

    @server.tool(name="unreject_player")
    def unreject_player_tool(player: str) -> RejectedReport:
        """Take a player off the rejected list so recruitment answers can suggest him again."""
        current = read_current(career)
        try:
            entry = find_rejected_entry(rejections.entries(current.career), player)
        except NotRejected as error:
            raise ToolError(str(error)) from error
        rejections.remove(current.career, entry.uid)
        return RejectedReport(save_context(current), rejected_list(rejections.entries(current.career)))

    @server.tool(name="rejected_players")
    def rejected_players_tool() -> RejectedReport:
        """The players marked as rejected, who recruitment answers leave out."""
        current = read_current(career)
        return RejectedReport(save_context(current), rejected_list(rejections.entries(current.career)))

    return server
