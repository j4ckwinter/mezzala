from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated

import fmsave
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mezzala.core.formations import Formation
from mezzala.core.lookup import AmbiguousPlayer, PlayerNotFound, find_player
from mezzala.core.money import format_money, format_weekly_wage, stored_from_pounds
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import ACCOMPLISHED_POSITION_RATING, NATURAL_POSITION_RATING, PositionGroup
from mezzala.core.squad import owned_players, squad_level
from mezzala.save.career import Career, Current
from mezzala.save.reader import UnreadableSave
from mezzala.tools.compare_formations import FormationComparison, compare_formations
from mezzala.tools.contract_watch import ContractWatch, contract_watch
from mezzala.tools.development_plan import DevelopmentPlan, development_plan
from mezzala.tools.find_players import FoundPlayers, PlayerSearch, SearchScope, SortBy, find_players
from mezzala.tools.league_comparison import LeagueComparison, league_comparison
from mezzala.tools.regen_intake import RegenIntake, regen_intake
from mezzala.tools.replacement import Limits, Replacements, find_replacements
from mezzala.tools.risers import RiserFilters, Risers, RiserScope, find_risers
from mezzala.tools.sell_high import SellHigh, sell_high
from mezzala.tools.shortlist import Shortlist, shortlist
from mezzala.tools.squad_gaps import SquadGaps, squad_gaps
from mezzala.tools.squad_list import SquadList, squad_list
from mezzala.tools.wage_review import WageReview, wage_review

DEFAULT_FORMATION = Formation.FOUR_THREE_THREE
DEFAULT_LIMIT = 10
RISER_CA_BELOW_SQUAD_LEVEL = 20
RISER_TARGET_MAX_AGE = 23

INSTRUCTIONS = f"""\
mezzala reads the manager's Football Manager 27 save and answers squad, formation and transfer questions about it.
Every answer starts with the save's in-game date and club. Each call checks the save file and stores a new
snapshot when it has changed, so growth compares real snapshots once there are two or more.
Money is in pounds. Fees are FM's transfer values, because asking prices are not stored in the save.
Current and potential ability (CA, PA) are FM's hidden 1-200 numbers.
find_players searches every player in the save with filters and sorts, and answers most recruitment
questions. shortlist builds a transfer shortlist within the budgets. wage_review, development_plan and
league_comparison cover wages, young players and how the squad compares with its league. squad lists the players. compare_formations ranks formations by how well the squad fits them and shows each
eleven. Positions are natural (FM rating {NATURAL_POSITION_RATING}+) or accomplished
({ACCOMPLISHED_POSITION_RATING}-{NATURAL_POSITION_RATING - 1}). Ask the manager which formation they
play if it matters; tools that take one default to {DEFAULT_FORMATION.value}."""


@dataclass(frozen=True)
class SaveContext:
    save: str
    game_date: str
    club: str
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
class RegenIntakeReport:
    context: SaveContext
    result: RegenIntake


def save_context(current: Current) -> SaveContext:
    snapshot = current.snapshot
    return SaveContext(
        save=current.save_path.name,
        game_date=snapshot.game_date.isoformat(),
        club=snapshot.club_name,
        transfer_budget=format_money(snapshot.budget.transfer_remaining),
        wage_headroom=format_weekly_wage(snapshot.budget.wage_headroom_weekly),
        snapshots=current.snapshot_count,
        notes=current.notes,
    )


def optional_stored(pounds: float | None) -> int | None:
    return None if pounds is None else stored_from_pounds(pounds)


def read_current(career: Career) -> Current:
    try:
        return career.current()
    except (fmsave.FmsaveError, UnreadableSave, OSError) as error:
        raise ToolError(f"Could not read the save: {error}") from error


def target_player(snapshot: Snapshot, name: str) -> Player:
    try:
        return find_player(snapshot, name)
    except (PlayerNotFound, AmbiguousPlayer) as error:
        raise ToolError(str(error)) from error


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


FormationChoice = Annotated[Formation, Field(description=one_of(Formation))]
FormationChoices = Annotated[list[Formation] | None, Field(description=f"Defaults to all. {one_of(Formation)}")]
PositionChoice = Annotated[PositionGroup | None, Field(description=one_of(PositionGroup))]
ScopeChoice = Annotated[RiserScope, Field(description=one_of(RiserScope))]
SearchScopeChoice = Annotated[SearchScope, Field(description=one_of(SearchScope))]
SortChoice = Annotated[SortBy, Field(description=one_of(SortBy))]


def create_server(career: Career) -> MCPServer:
    server = MCPServer("mezzala", instructions=INSTRUCTIONS)

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
        return SquadReport(save_context(current), squad_list(current.snapshot))

    @server.tool(name="find_players")
    def find_players_tool(
        sort_by: SortChoice = SortBy.CURRENT_ABILITY,
        scope: SearchScopeChoice = SearchScope.ELSEWHERE,
        position: PositionChoice = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_ca: int | None = None,
        max_ca: int | None = None,
        min_pa: int | None = None,
        max_fee: float | None = None,
        max_wage: float | None = None,
        free_agents_only: bool = False,
        contract_ending_within_months: int | None = None,
        max_release_clause: float | None = None,
        youth_contract_only: bool = False,
        reserves_only: bool = False,
        bigger_clubs_only: bool = False,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> FoundPlayersReport:
        """Search every player in the save with filters and a sort. Money is in pounds (max_wage weekly).

        Sorts: "value for money" puts players valued lowest against others of similar CA, age and potential first
        (undervalued, cheap to flip); "above league level" puts players furthest above their league's
        first-team median CA first (too good for their division); "position attributes" ranks the key
        attributes for the position (combine with max_ca to find attributes ahead of ability); "most overpaid"
        ranks wages against similar players. reserves_only keeps players outside their club's first team;
        bigger_clubs_only keeps clubs with a higher reputation than yours. within_reach keeps players whose
        reputation makes a move realistic; set it false for questions like the best players in the world.
        scope "own" searches your club, "everyone" the whole save."""
        current = read_current(career)
        search = PlayerSearch(
            scope, position, min_age, max_age, min_ca, max_ca, min_pa, optional_stored(max_fee),
            optional_stored(max_wage), free_agents_only, contract_ending_within_months,
            optional_stored(max_release_clause), youth_contract_only, reserves_only, bigger_clubs_only,
            within_reach, sort_by, limit,
        )  # fmt: skip
        return FoundPlayersReport(save_context(current), find_players(current.snapshot, search))

    @server.tool(name="shortlist")
    def shortlist_tool(
        formation: FormationChoice = DEFAULT_FORMATION,
        transfer_budget: float | None = None,
        weekly_wage_budget: float | None = None,
    ) -> ShortlistReport:
        """A realistic transfer shortlist: for each position squad_gaps flags, worst first, the best player
        within reach who beats the current starter, spending down the transfer budget and weekly wage room as it
        goes, with two alternatives each. Budgets are in pounds and default to the club's remaining transfer
        budget and wage room. Wages shown are the player's current wage; a free agent's is estimated from
        similar players and counted against the wage room."""
        current = read_current(career)
        budget = current.snapshot.budget
        fees = optional_stored(transfer_budget) if transfer_budget is not None else budget.transfer_remaining
        wages = optional_stored(weekly_wage_budget) if weekly_wage_budget is not None else budget.wage_headroom_weekly
        return ShortlistReport(save_context(current), shortlist(current.snapshot, formation, fees, wages))

    @server.tool(name="wage_review")
    def wage_review_tool(formation: FormationChoice = DEFAULT_FORMATION) -> WageReviewReport:
        """Everyone the club pays, at what it actually pays them: the wage bill, players paid well above others
        of similar CA, age and potential, and surplus players (not in the best eleven and not needed for cover
        anywhere in the formation, and not a young prospect) with the weekly saving if they all went."""
        current = read_current(career)
        return WageReviewReport(save_context(current), wage_review(current.snapshot, formation))

    @server.tool(name="development_plan")
    def development_plan_tool(formation: FormationChoice = DEFAULT_FORMATION) -> DevelopmentPlanReport:
        """The club's players aged 21 or under: who is ready for the first team (within a few CA of the weakest
        starter in a position he can play), who to loan out for games (not ready, old enough, room to grow),
        who is already on loan, and the five to focus on: potential that reaches the first eleven's level, ranked
        by potential then projected growth."""
        current = read_current(career)
        return DevelopmentPlanReport(save_context(current), development_plan(current.snapshot, formation))

    @server.tool(name="league_comparison")
    def league_comparison_tool(formation: FormationChoice = DEFAULT_FORMATION) -> LeagueComparisonReport:
        """How the club's squad compares with the rest of its league: every club ranked by the average CA of its
        best eleven for the formation, with first-team value, and position by position the club's starters
        against the league median and the best club there."""
        current = read_current(career)
        return LeagueComparisonReport(save_context(current), league_comparison(current.snapshot, formation))

    @server.tool(name="compare_formations")
    def compare_formations_tool(formations: FormationChoices = None) -> FormationReport:
        """Rank formations by how well the squad fits them: for each, the best eleven (each player once, with
        natural or accomplished fit), its score, accomplished (non-natural) starters, empty places, weakest place,
        and whether it is effectively tied with the best."""
        current = read_current(career)
        chosen = list(dict.fromkeys(formations)) if formations else list(Formation)
        return FormationReport(save_context(current), compare_formations(current.snapshot, chosen))

    @server.tool(name="squad_gaps")
    def squad_gaps_tool(formation: FormationChoice = DEFAULT_FORMATION) -> SquadGapsReport:
        """Where the squad is thin, ageing, leaving, weak or has no young successor, by position for a formation."""
        current = read_current(career)
        return SquadGapsReport(save_context(current), squad_gaps(current.snapshot, formation))

    @server.tool()
    def find_replacement(
        player: str,
        max_fee: float | None = None,
        max_age: int | None = None,
        max_wage: float | None = None,
        position: PositionChoice = None,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> ReplacementReport:
        """Players outside the club with a similar attribute profile who could replace `player`.

        max_fee and max_wage (weekly) are in pounds. max_fee defaults to the club's remaining transfer budget;
        free agents always qualify. position defaults to the player's main position. within_reach keeps
        players whose reputation is close enough to the club's that a move is realistic."""
        current = read_current(career)
        snapshot = current.snapshot
        target = target_player(snapshot, player)
        fee_cap = optional_stored(max_fee) if max_fee is not None else snapshot.budget.transfer_remaining
        limits = Limits(fee_cap, max_age, optional_stored(max_wage), within_reach)
        result = find_replacements(snapshot, target, limits, limit, position)
        return ReplacementReport(save_context(current), result)

    @server.tool()
    def risers(
        scope: ScopeChoice = RiserScope.ELSEWHERE,
        since: date | None = None,
        min_ca_gain: float = 3,
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
        floor, age_limit = riser_defaults(scope, current.snapshot, min_ca, max_age)
        fee_cap = optional_stored(max_fee) if max_fee is not None else current.snapshot.budget.transfer_remaining
        filters = RiserFilters(scope, min_ca_gain, floor, within_reach, age_limit, fee_cap, position)
        result = find_risers(current.snapshot, career.baseline(current, since), filters, limit)
        return RisersReport(save_context(current), result)

    @server.tool(name="sell_high")
    def sell_high_tool(limit: int = DEFAULT_LIMIT) -> SellHighReport:
        """Your players worth selling now: past peak age, at their ceiling, valued above similar players,
        contract running down, or (with history) value falling or ability stalled while value rose."""
        current = read_current(career)
        owned = {player.uid for player in owned_players(current.snapshot)}
        result = sell_high(current.snapshot, career.past_players(current, owned), limit)
        return SellHighReport(save_context(current), result)

    @server.tool(name="contract_watch")
    def contract_watch_tool(
        within_months: int = 12,
        max_age: int | None = None,
        formation: FormationChoice = DEFAULT_FORMATION,
        within_reach: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> ContractWatchReport:
        """Your contracts and loans ending soon, plus free agents and players elsewhere with expiring contracts
        who would beat your current starter somewhere in the formation."""
        current = read_current(career)
        result = contract_watch(current.snapshot, formation, within_months, max_age, within_reach, limit)
        return ContractWatchReport(save_context(current), result)

    @server.tool(name="regen_intake")
    def regen_intake_tool(since: date | None = None, min_pa: int = 120, limit: int = 20) -> RegenIntakeReport:
        """Newly generated youth players (regens) that appeared since an earlier snapshot, best potential first."""
        current = read_current(career)
        baseline = career.baseline(current, since)
        return RegenIntakeReport(save_context(current), regen_intake(current.snapshot, baseline, min_pa, limit))

    return server
