import calendar
from datetime import date
from enum import StrEnum

from mezzala.core.players import Player, Snapshot

PRE_CONTRACT_MONTHS = 6


def months_before(day: date, months: int) -> date:
    month_index = day.year * 12 + day.month - 1 - months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def pre_contract_opens(player: Player) -> date | None:
    if player.is_free_agent or player.contract_end is None:
        return None
    return months_before(player.contract_end, PRE_CONTRACT_MONTHS)


def can_sign_on_pre_contract(player: Player, today: date) -> bool:
    opens = pre_contract_opens(player)
    return opens is not None and player.contract_end is not None and opens <= today <= player.contract_end


def pre_contract_status(player: Player, today: date) -> str:
    opens = pre_contract_opens(player)
    if opens is None or player.contract_end is None or player.contract_end < today:
        return "no pre-contract: he has no running contract"
    if opens <= today:
        return f"contract ends {player.contract_end.isoformat()}: you can agree a pre-contract now"
    return (
        f"contract ends {player.contract_end.isoformat()}: a pre-contract is possible from {opens.isoformat()}, "
        "a cut-price fee before then"
    )


class Route(StrEnum):
    FREE_AGENT = "free agent"
    PRE_CONTRACT = "pre-contract"
    TRANSFER = "transfer"


def pre_contract_warnings(player: Player, snapshot: Snapshot) -> list[str]:
    if player.on_loan:
        return [f"on loan at {player.club_name or 'another club'}: players on loan often refuse a pre-contract"]
    if player.club_nation_id is not None and player.club_nation_id == snapshot.club_nation_id:
        return [
            "at a club in your own country: such players often refuse a pre-contract, so expect to wait "
            "for his contract to end or to pay a fee"
        ]
    return []


def route_warnings(player: Player, snapshot: Snapshot, route: Route) -> list[str]:
    match route:
        case Route.FREE_AGENT:
            return []
        case Route.PRE_CONTRACT:
            return pre_contract_warnings(player, snapshot)
        case Route.TRANSFER:
            on_loan = f"on loan at {player.club_name or 'another club'}, so his parent club decides on a sale"
            return [on_loan] if player.on_loan else []


def signing_warnings(player: Player, snapshot: Snapshot, route: Route) -> list[str]:
    warnings = route_warnings(player, snapshot, route)
    offer = player.renewal_offer
    if offer is not None:
        until = f" until {offer.ends.isoformat()}" if offer.ends else ""
        warnings.append(f"his club has offered him a new deal{until}, and he may sign it first")
    warnings.extend(
        f"a move to {move.club_name or 'another club'} is lined up"
        + (f" from {move.starts.isoformat()}" if move.starts else "")
        for move in player.moves_lined_up
        if move.club_uid != snapshot.club_uid
    )
    return warnings


def signing_route(player: Player, today: date) -> Route:
    if player.is_free_agent:
        return Route.FREE_AGENT
    if can_sign_on_pre_contract(player, today):
        return Route.PRE_CONTRACT
    return Route.TRANSFER


def route_fee(player: Player, route: Route) -> int | None:
    match route:
        case Route.FREE_AGENT | Route.PRE_CONTRACT:
            return 0
        case Route.TRANSFER:
            return player.value
