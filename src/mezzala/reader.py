import dataclasses
import warnings
from collections import defaultdict
from pathlib import Path

import fmsave

from mezzala.players import Budget, Player, Snapshot


class UnreadableSave(RuntimeError):
    pass


def known_value(player: fmsave.Player) -> int | None:
    if player.transfer_value_state is fmsave.TransferValueState.OK:
        return player.transfer_value
    return None


def to_player(player: fmsave.Player, minutes: int) -> Player | None:
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
        value=known_value(player),
        wage=contract.wage if contract else None,
        contract_end=contract.end if contract else None,
        on_loan=bool(player.on_loan),
        loan_parent_club_uid=player.loan_parent_club_uid,
        loan_end=player.loan_end,
        attributes=dataclasses.asdict(player.attributes),
        reputation=player.reputation.current,
        professionalism=personality.professionalism,
        ambition=personality.ambition,
        last_season_minutes=minutes,
    )


def last_season_minutes(save: fmsave.Save) -> dict[int, int]:
    minutes: dict[int, int] = defaultdict(int)
    for season in save.player_season_history():
        minutes[season.player_uid] += season.minutes
    return minutes


def budget(save: fmsave.Save, club_uid: int) -> Budget:
    months = sorted(save.finances().where(club_uid=club_uid), key=lambda month: month.month)
    if not months:
        return Budget(None, None, None)
    latest = months[-1]
    return Budget(latest.transfer_budget_remaining, latest.wage_budget_weekly, latest.wage_payroll_weekly)


def read_snapshot(path: Path) -> Snapshot:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", fmsave.FmsaveWarning)
        with fmsave.open(path) as save:
            clubs = save.managed_clubs()
            if not clubs:
                raise UnreadableSave(f"{path.name} has no managed club; mezzala needs a manager in a job.")
            club = clubs[0]
            minutes = last_season_minutes(save)
            converted = (to_player(player, minutes.get(player.uid, 0)) for player in save.players())
            players = tuple(player for player in converted if player is not None)
            game_date = save.info.game_date
            if game_date is None:
                raise UnreadableSave(f"{path.name} has no in-game date.")
            reputation = save.clubs().by_uid(club.club_uid).reputation
            if reputation is None:
                raise UnreadableSave(f"{path.name} has no reputation for {club.club_name}.")
            return Snapshot(game_date, club.club_uid, club.club_name, reputation, budget(save, club.club_uid), players)
