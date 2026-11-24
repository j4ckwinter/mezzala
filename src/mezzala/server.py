from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated

import fmsave
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mezzala.career import Career, Current
from mezzala.compare_formations import FormationComparison, compare_formations
from mezzala.contract_watch import ContractWatch, contract_watch
from mezzala.formations import Formation
from mezzala.lookup import AmbiguousPlayer, PlayerNotFound, find_player
from mezzala.money import format_money, format_weekly_wage, stored_from_pounds
from mezzala.players import Player, Snapshot
from mezzala.positions import ACCOMPLISHED_POSITION_RATING, NATURAL_POSITION_RATING, PositionGroup
from mezzala.reader import UnreadableSave
from mezzala.regen_intake import RegenIntake, regen_intake
from mezzala.replacement import Limits, Replacements, find_replacements
from mezzala.risers import RiserFilters, Risers, RiserScope, find_risers
from mezzala.sell_high import SellHigh, sell_high
from mezzala.squad import owned_players, squad_level
from mezzala.squad_gaps import SquadGaps, squad_gaps
from mezzala.squad_list import SquadList, squad_list

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
squad lists the players. compare_formations ranks formations by how well the squad fits them and shows each
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
