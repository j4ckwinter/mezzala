from dataclasses import dataclass
from datetime import UTC, datetime

from mezzala.core.money import format_money, format_weekly_wage
from mezzala.save.career import Current
from mezzala.save.store import FileStamp
from mezzala.tools.compare_formations import FormationComparison
from mezzala.tools.contract_watch import ContractWatch
from mezzala.tools.development_check import DevelopmentCheck
from mezzala.tools.development_plan import DevelopmentPlan
from mezzala.tools.dressing_room import DressingRoom
from mezzala.tools.find_players import FoundPlayers
from mezzala.tools.fitness import FitnessReport
from mezzala.tools.league_comparison import LeagueComparison
from mezzala.tools.league_values import LeagueValues
from mezzala.tools.next_job import NextJob
from mezzala.tools.next_opponent import NextOpponent
from mezzala.tools.performance import Performance
from mezzala.tools.player_profile import PlayerProfiles
from mezzala.tools.positional_fit import PositionalFit
from mezzala.tools.regen_intake import RegenIntake
from mezzala.tools.rejections import RejectedList
from mezzala.tools.relegated_clubs import RelegatedClubs
from mezzala.tools.replacement import Replacements
from mezzala.tools.risers import Risers
from mezzala.tools.sell_high import SellHigh
from mezzala.tools.shortlist import Shortlist
from mezzala.tools.squad_gaps import SquadGaps
from mezzala.tools.squad_list import SquadList
from mezzala.tools.squad_profile import SquadProfile
from mezzala.tools.squad_progress import SquadProgress
from mezzala.tools.staff_review import StaffReview
from mezzala.tools.tactic_fit import TacticFit
from mezzala.tools.training_plan import TrainingPlan
from mezzala.tools.wage_review import WageReview
from mezzala.tools.watchlist import Watchlist
from mezzala.tools.what_changed import WhatChanged

NANOSECONDS_PER_SECOND = 1_000_000_000
WRITTEN_FORMAT = "%Y-%m-%d %H:%M UTC"


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
class TacticFitReport:
    context: SaveContext
    result: TacticFit


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
