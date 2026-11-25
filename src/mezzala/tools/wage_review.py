from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.formations import PLAYERS_PER_STARTING_PLACE, STARTERS, Formation
from mezzala.core.lineup import pick_lineup
from mezzala.core.metrics import PeerMedians, weekly_wage
from mezzala.core.money import format_weekly_wage
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import covers
from mezzala.core.squad import available_squad, owned_players, plays_for_club, squad_level, wage_paid_by_club

OVERPAID_RATIO = 1.5
PROSPECT_MAX_AGE = 21


class Role(StrEnum):
    STARTER = "starter"
    DEPTH = "needed for depth"
    PROSPECT = "prospect"
    SURPLUS = "surplus"
    OUT_ON_LOAN = "out on loan"


@dataclass(frozen=True)
class WageEntry:
    name: str
    age: int
    current_ability: int
    potential_ability: int
    role: str
    weekly_wage_paid: str
    wage_vs_similar_players: str
    contract_end: str


@dataclass(frozen=True)
class WageReview:
    formation: str
    weekly_wage_bill: str
    overpaid: list[WageEntry]
    surplus: list[WageEntry]
    weekly_saving_without_surplus: str


def everyone_paid(snapshot: Snapshot) -> list[Player]:
    loaned_in = [player for player in available_squad(snapshot) if player.on_loan]
    return [*owned_players(snapshot), *loaned_in]


def roles(snapshot: Snapshot, formation: Formation) -> dict[int, Role]:
    squad = available_squad(snapshot)
    starters = {player.uid for player in pick_lineup(squad, formation).starters}
    places = STARTERS[formation]
    cover = {group: sum(1 for player in squad if covers(player, group)) for group in places}
    level = squad_level(snapshot)
    found: dict[int, Role] = {}
    for player in sorted(everyone_paid(snapshot), key=lambda p: p.current_ability):
        covered = [group for group in places if covers(player, group)]
        if not plays_for_club(player, snapshot.club_uid):
            found[player.uid] = Role.OUT_ON_LOAN
        elif player.uid in starters:
            found[player.uid] = Role.STARTER
        elif any(cover[group] <= PLAYERS_PER_STARTING_PLACE * places[group] for group in covered):
            found[player.uid] = Role.DEPTH
        elif player.age <= PROSPECT_MAX_AGE and player.potential_ability >= level:
            found[player.uid] = Role.PROSPECT
        else:
            found[player.uid] = Role.SURPLUS
            for group in covered:
                cover[group] -= 1
    return found


def wage_review(snapshot: Snapshot, formation: Formation) -> WageReview:
    peers = PeerMedians(snapshot.players, weekly_wage)
    role_of = roles(snapshot, formation)
    entries: list[tuple[Player, int | None, float | None]] = []
    for player in everyone_paid(snapshot):
        paid = wage_paid_by_club(player, snapshot.club_uid)
        entries.append((player, paid, peers.ratio_of(paid, player)))

    def entry(player: Player, paid: int | None, ratio: float | None) -> WageEntry:
        return WageEntry(
            player.name, player.age, player.current_ability, player.potential_ability, role_of[player.uid].value,
            format_weekly_wage(paid), "unknown" if ratio is None else f"{ratio:.2f}x",
            player.contract_end.isoformat() if player.contract_end else "none",
        )  # fmt: skip

    overpaid = sorted(
        (item for item in entries if item[2] is not None and item[2] >= OVERPAID_RATIO),
        key=lambda item: item[2] or 0.0,
        reverse=True,
    )
    surplus = sorted((item for item in entries if role_of[item[0].uid] is Role.SURPLUS), key=lambda i: -(i[1] or 0))
    return WageReview(
        formation=formation.value,
        weekly_wage_bill=format_weekly_wage(sum(paid or 0 for _, paid, _ in entries)),
        overpaid=[entry(*item) for item in overpaid],
        surplus=[entry(*item) for item in surplus],
        weekly_saving_without_surplus=format_weekly_wage(sum(paid or 0 for _, paid, _ in surplus)),
    )
