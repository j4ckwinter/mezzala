from datetime import date, timedelta
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mezzala.core.formations import Formation
from mezzala.core.players import Snapshot
from mezzala.core.rejections import without_rejected
from mezzala.core.roles import UnknownRole, find_role
from mezzala.core.slots import BadSlot, parse_slot
from mezzala.core.squad import belongs_to_club, is_outside_club, owned_players, plays_for_club
from mezzala.core.view import View
from mezzala.save.career import Career, Current
from mezzala.save.rejections import RejectionStore
from mezzala.save.watchlist import WatchlistStore
from mezzala.server.instructions import FIND_PLAYERS_DESCRIPTION, RISERS_DESCRIPTION, instructions_for
from mezzala.server.parameters import (
    DEFAULT_LIMIT,
    DEVELOPMENT_MIN_PA,
    PERFORMANCE_MIN_MINUTES,
    REGEN_MIN_PA,
    RELEGATION_LOOKBACK_DAYS,
    RISER_MIN_CA_GAIN,
    CheckScopeChoice,
    ClubChoice,
    FormationChoice,
    FormationChoices,
    PerformanceScopeChoice,
    PerformanceSortChoice,
    PositionChoice,
    ScopeChoice,
    SearchScopeChoice,
    SideChoice,
    SortChoice,
    optional_stored,
    read_current,
    refuse_hidden_filters,
    target_player,
    with_formation,
)
from mezzala.server.reports import (
    BudgetReport,
    ContractWatchReport,
    DevelopmentCheckReport,
    DevelopmentPlanReport,
    DressingRoomReport,
    FitnessToolReport,
    FormationReport,
    FoundPlayersReport,
    LeagueComparisonReport,
    LeagueValuesReport,
    NextJobReport,
    NextOpponentReport,
    PerformanceReport,
    PlayerProfileReport,
    PositionalFitReport,
    RegenIntakeReport,
    RejectedReport,
    RelegatedClubsReport,
    ReplacementReport,
    RisersReport,
    SellHighReport,
    ShortlistReport,
    SnapshotReport,
    SquadGapsReport,
    SquadProfileReport,
    SquadProgressReport,
    SquadReport,
    StaffReviewReport,
    TacticFitReport,
    TrainingPlanReport,
    WageReviewReport,
    WatchlistReport,
    WhatChangedReport,
    save_context,
)
from mezzala.tools.budget import budget_picture
from mezzala.tools.compare_formations import compare_formations
from mezzala.tools.contract_watch import contract_watch
from mezzala.tools.development_check import CheckScope, development_check
from mezzala.tools.development_plan import development_plan
from mezzala.tools.dressing_room import dressing_room
from mezzala.tools.find_players import PlayerSearch, SearchScope, SortBy, find_players
from mezzala.tools.fitness import fitness
from mezzala.tools.league_comparison import league_comparison
from mezzala.tools.league_values import league_values
from mezzala.tools.next_job import next_job
from mezzala.tools.next_opponent import next_opponent
from mezzala.tools.performance import PerformanceScope, PerformanceSearch, PerformanceSort, performance
from mezzala.tools.player_profile import player_profiles
from mezzala.tools.positional_fit import positional_fit
from mezzala.tools.regen_intake import regen_intake
from mezzala.tools.rejections import NotRejected, find_rejected_entry, rejected_list, rejected_record
from mezzala.tools.relegated_clubs import relegated_clubs
from mezzala.tools.replacement import Limits, find_replacements
from mezzala.tools.risers import RiserFilters, RiserScope, find_risers, riser_defaults
from mezzala.tools.sell_high import sell_high
from mezzala.tools.shortlist import shortlist
from mezzala.tools.squad_gaps import squad_gaps
from mezzala.tools.squad_list import squad_list
from mezzala.tools.squad_profile import squad_profile
from mezzala.tools.squad_progress import squad_progress
from mezzala.tools.staff_review import staff_review
from mezzala.tools.tactic_fit import tactic_fit
from mezzala.tools.training_plan import training_plan
from mezzala.tools.wage_review import wage_review
from mezzala.tools.watchlist import NotWatched, find_watched_entry, watched_record, watchlist
from mezzala.tools.what_changed import what_changed


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
        pre_contract_only: bool = False,
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
        compact: bool = False,
        role: str | None = None,
        side: SideChoice = None,
    ) -> FoundPlayersReport:
        current = read_current(career)
        refuse_hidden_filters(
            view, {"min_ca": min_ca is not None, "max_ca": max_ca is not None, "min_pa": min_pa is not None}
        )
        if sort_by is SortBy.ROLE_FIT and role is None:
            raise ToolError('Sorting by "role fit" needs a role, such as "inside forward".')
        try:
            chosen_role = find_role(role) if role is not None else None
        except UnknownRole as error:
            raise ToolError(str(error)) from error
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
            pre_contract_only=pre_contract_only,
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
            compact=compact,
            role=chosen_role,
            side=side,
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
        similar reputation (in your country first), and no more than the top of their range. Targets are young
        enough not to be ageing for at least two seasons, and among targets within a few CA of the best the one
        using the smallest share of the tighter budget wins."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        budget = current.snapshot.budget
        fees = optional_stored(transfer_budget) if transfer_budget is not None else budget.transfer_remaining
        wages = optional_stored(weekly_wage_budget) if weekly_wage_budget is not None else budget.wage_headroom_weekly
        return ShortlistReport(context, shortlist(recruitable(current), shape, fees, wages, view))

    @server.tool(name="budget")
    def budget_tool() -> BudgetReport:
        """The club's money: transfer budget left, weekly wage budget, wage bill and room, and the same after the
        season's contracts end (the commonest end date among your contracts): who leaves, who has a move lined up
        to join, and the wage bill and room that leaves. Budgets come from FM's monthly finance records, so the
        answer names the month they are from."""
        current = read_current(career)
        return BudgetReport(save_context(current), budget_picture(current.snapshot))

    @server.tool(name="wage_review")
    def wage_review_tool(formation: FormationChoice = None) -> WageReviewReport:
        """Everyone the club pays, at what it actually pays them: the wage bill, players paid well above others
        of similar CA, age and potential, and surplus players (not in the best eleven and not needed for cover
        anywhere in the formation, and not a young prospect) with the weekly saving if they all went."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        return WageReviewReport(context, wage_review(current.snapshot, shape, view))

    @server.tool(name="development_plan")
    def development_plan_tool(formation: FormationChoice = None) -> DevelopmentPlanReport:
        """The club's players aged 21 or under: who is ready for the first team (within a few CA of the weakest
        starter in a position he can play), who to loan out for games (not ready, old enough, room to grow),
        who is already on loan, and the five to focus on: potential that reaches the first eleven's level, ranked
        by potential then projected growth."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        return DevelopmentPlanReport(context, development_plan(current.snapshot, shape, view))

    @server.tool(name="league_comparison")
    def league_comparison_tool(formation: FormationChoice = None) -> LeagueComparisonReport:
        """How the club's squad compares with the rest of its league: every club ranked by the average CA of its
        best eleven for the formation, with first-team value, and position by position the club's starters
        against the league median and the best club there."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        return LeagueComparisonReport(context, league_comparison(current.snapshot, shape, view))

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
        shape, context = with_formation(current, formation)
        first = career.baseline(current, None)
        return SquadProgressReport(context, squad_progress(current.snapshot, first, shape, view))

    @server.tool(name="next_job")
    def next_job_tool(
        formation: FormationChoice = None, bigger_only: bool = False, limit: int = DEFAULT_LIMIT
    ) -> NextJobReport:
        """Open first-team manager jobs in the save, biggest club first: each club's reputation against yours,
        its league level, the strength of its best eleven, and its money where the save has finances."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        return NextJobReport(context, next_job(current.snapshot, shape, bigger_only, limit, view))

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
        shape, context = with_formation(current, formation)
        return SquadProfileReport(context, squad_profile(current.snapshot, shape))

    @server.tool(name="positional_fit")
    def positional_fit_tool(formation: FormationChoice = None) -> PositionalFitReport:
        """Whether the best eleven's players suit the positions they are picked in: each starter's key-attribute
        score there, and starters whose attributes suit another position they can play noticeably better."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        return PositionalFitReport(context, positional_fit(current.snapshot, shape))

    @server.tool(name="next_opponent")
    def next_opponent_tool(formation: FormationChoice = None) -> NextOpponentReport:
        """The club's next first-team fixture and an analysis of the opponent: their likely formation and best
        eleven, key players, how their outfield attributes compare with your eleven's, and their recent results.
        Use it to suggest tactical adjustments."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        return NextOpponentReport(context, next_opponent(current.snapshot, shape, view))

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
        shape, context = with_formation(current, formation)
        return SquadGapsReport(context, squad_gaps(current.snapshot, shape, view))

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

    @server.tool(description=RISERS_DESCRIPTION)
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
        who would beat your current starter somewhere in the formation. Each target says whether you can agree a
        pre-contract now (his contract ends within six months) or from when, and warns when he is on loan, at a
        club in your own country, has an open renewal offer, or has a move lined up elsewhere."""
        current = read_current(career)
        shape, context = with_formation(current, formation)
        result = contract_watch(recruitable(current), shape, within_months, max_age, within_reach, limit, view)
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
        shape, context = with_formation(current, formation)
        return FitnessToolReport(context, fitness(current.snapshot, shape, view))

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
        if not is_outside_club(target, current.snapshot.club_uid):
            raise ToolError(
                f"{target.name} plays for {current.snapshot.club_name}; only other clubs' players can be rejected."
            )
        rejections.add(current.career, rejected_record(target, current.snapshot, note))
        return RejectedReport(save_context(current), rejected_list(rejections.entries(current.career)))

    @server.tool(name="unreject_player")
    def unreject_player_tool(player: str, club: ClubChoice = None) -> RejectedReport:
        """Take a player off the rejected list so recruitment answers can suggest him again."""
        current = read_current(career)
        try:
            entry = find_rejected_entry(rejections.entries(current.career), player, club, current.snapshot)
        except NotRejected as error:
            raise ToolError(str(error)) from error
        rejections.remove(current.career, entry.uid)
        return RejectedReport(save_context(current), rejected_list(rejections.entries(current.career)))

    @server.tool(name="rejected_players")
    def rejected_players_tool() -> RejectedReport:
        """The players marked as rejected, who recruitment answers leave out."""
        current = read_current(career)
        return RejectedReport(save_context(current), rejected_list(rejections.entries(current.career)))

    @server.tool(name="tactic_fit")
    def tactic_fit_tool(
        slots: Annotated[
            list[str],
            Field(
                description="One entry per slot, FM position code then role, such as 'GK: sweeper keeper', "
                "'DCL: overlapping centre-back', 'WBL: wing-back', 'AML: inside forward', 'STC: advanced forward'."
            ),
        ],
    ) -> TacticFitReport:
        """Fit the squad to a tactic described slot by slot with roles, for shapes the six built-in formations do
        not cover. Each slot gets the player whose attributes suit its role best (using each player once), with
        his role score out of 20 and the next best options; the weakest slots are the ones to strengthen. Roles
        on one side favour a foot: inside forwards, inverted wingers and inverted wing-backs the opposite one,
        wingers, wing-backs and full-backs the same one."""
        current = read_current(career)
        try:
            parsed = [parse_slot(slot) for slot in slots]
        except (BadSlot, UnknownRole) as error:
            raise ToolError(str(error)) from error
        return TacticFitReport(save_context(current), tactic_fit(current.snapshot, parsed))

    return server
