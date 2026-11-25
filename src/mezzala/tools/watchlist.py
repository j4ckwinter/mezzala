from dataclasses import dataclass

from mezzala.core.lookup import folded
from mezzala.core.metrics import release_clause_for
from mezzala.core.money import format_money
from mezzala.core.players import Player, Snapshot, WatchedPlayer
from mezzala.core.squad import contract_ends_within
from mezzala.core.summary import PlayerSummary, summarize

CHEAPER_SHARE = 0.9
CONTRACT_SOON_MONTHS = 12


@dataclass(frozen=True)
class WatchedNow:
    name: str
    note: str
    added_on: str
    now: PlayerSummary | None
    since_added: list[str]
    cheaper_because: list[str]


@dataclass(frozen=True)
class Watchlist:
    players: list[WatchedNow]


class NotWatched(LookupError):
    pass


def find_watched_entry(entries: list[WatchedPlayer], query: str) -> WatchedPlayer:
    wanted = folded(query.strip())
    exact = [entry for entry in entries if folded(entry.name) == wanted]
    partial = [entry for entry in entries if wanted in folded(entry.name)]
    for found in (exact, partial):
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            names = ", ".join(f"{entry.name} ({entry.club_name or 'free agent'})" for entry in found)
            raise NotWatched(f"'{query}' matches several watched players: {names}. Use a fuller name.")
    raise NotWatched(f"No player called '{query}' is on the watchlist.")


def watched_record(player: Player, snapshot: Snapshot, note: str) -> WatchedPlayer:
    return WatchedPlayer(
        player.uid, player.birth_date, player.name, snapshot.game_date, player.value, player.current_ability,
        player.club_name, note,
    )  # fmt: skip


def find_watched(watched: WatchedPlayer, by_uid: dict[int, Player]) -> Player | None:
    player = by_uid.get(watched.uid)
    if player is None or player.birth_date != watched.birth_date:
        return None
    return player


def changes_since(watched: WatchedPlayer, player: Player) -> list[str]:
    found: list[str] = []
    if player.club_name != watched.club_name:
        found.append(f"moved: {watched.club_name or 'no club'} -> {player.club_name or 'no club'}")
    if player.current_ability != watched.current_ability:
        found.append(f"CA {watched.current_ability} -> {player.current_ability}")
    if player.value != watched.value:
        found.append(f"value {format_money(watched.value)} -> {format_money(player.value)}")
    return found


def cheaper_because(watched: WatchedPlayer, player: Player, snapshot: Snapshot) -> list[str]:
    reasons: list[str] = []
    if player.is_free_agent and watched.club_name is not None:
        reasons.append("now a free agent")
    if watched.value and player.value is not None and player.value <= CHEAPER_SHARE * watched.value:
        reasons.append(f"value down from {format_money(watched.value)} to {format_money(player.value)}")
    ending = contract_ends_within(player, snapshot.game_date, CONTRACT_SOON_MONTHS)
    if ending is not None and not player.is_free_agent:
        reasons.append(f"contract ends {ending.isoformat()}")
    clause = release_clause_for(player, snapshot.club_nation_id, snapshot.game_date)
    if clause is not None:
        reasons.append(f"release clause of {format_money(clause)} applies to your club")
    return reasons


def watchlist(snapshot: Snapshot, entries: list[WatchedPlayer]) -> Watchlist:
    by_uid = snapshot.by_uid()
    found: list[WatchedNow] = []
    for watched in entries:
        player = find_watched(watched, by_uid)
        if player is None:
            found.append(WatchedNow(watched.name, watched.note, watched.added_on.isoformat(), None,
                                    ["no longer in the save (retired or removed)"], []))  # fmt: skip
            continue
        found.append(
            WatchedNow(watched.name, watched.note, watched.added_on.isoformat(), summarize(player),
                       changes_since(watched, player), cheaper_because(watched, player, snapshot))
        )  # fmt: skip
    found.sort(key=lambda entry: len(entry.cheaper_because), reverse=True)
    return Watchlist(found)
