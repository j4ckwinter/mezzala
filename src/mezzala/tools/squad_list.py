from dataclasses import dataclass

from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import Fit, PositionGroup, fit
from mezzala.core.squad import available_squad, owned_players, plays_for_club
from mezzala.core.summary import PlayerSummary, summarize


@dataclass(frozen=True)
class SquadMember:
    player: PlayerSummary
    natural_positions: list[str]
    accomplished_positions: list[str]
    status: str


@dataclass(frozen=True)
class SquadList:
    available: list[SquadMember]
    loaned_out: list[SquadMember]


def positions_with(player: Player, wanted: Fit) -> list[str]:
    return [group.value for group in PositionGroup if fit(player, group) is wanted]


def status(player: Player, club_uid: int) -> str:
    until = f" until {player.loan_end.isoformat()}" if player.loan_end else ""
    if not player.on_loan:
        return "permanent"
    if plays_for_club(player, club_uid):
        return f"loaned in{until}"
    return f"loaned out to {player.club_name}{until}"


def member(player: Player, club_uid: int) -> SquadMember:
    return SquadMember(
        summarize(player),
        positions_with(player, Fit.NATURAL),
        positions_with(player, Fit.ACCOMPLISHED),
        status(player, club_uid),
    )


def by_ability(players: list[Player]) -> list[Player]:
    return sorted(players, key=lambda player: player.current_ability, reverse=True)


def squad_list(snapshot: Snapshot) -> SquadList:
    loaned_out = [player for player in owned_players(snapshot) if not plays_for_club(player, snapshot.club_uid)]
    return SquadList(
        [member(player, snapshot.club_uid) for player in by_ability(available_squad(snapshot))],
        [member(player, snapshot.club_uid) for player in by_ability(loaned_out)],
    )
