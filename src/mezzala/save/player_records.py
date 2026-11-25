from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import fmsave

from mezzala.core.players import Injury, SeasonStats
from mezzala.save.labels import coded_label
from mezzala.save.sections import optional_section


@dataclass(frozen=True)
class CurrentInjury:
    name: str | None
    back_on: date


@dataclass(frozen=True)
class PlayerRecords:
    injuries: dict[int, tuple[Injury, ...]]
    current_injuries: dict[int, CurrentInjury]
    seasons: dict[int, SeasonStats]


def injury_records(
    records: Iterable[fmsave.InjuryRecord], today: date
) -> tuple[dict[int, tuple[Injury, ...]], dict[int, CurrentInjury]]:
    history: dict[int, list[Injury]] = {}
    current: dict[int, CurrentInjury] = {}
    for record in records:
        if record.player_uid is None or record.date is None:
            continue
        match record.kind:
            case fmsave.InjuryRecordKind.HISTORY:
                injury = Injury(record.date, coded_label(record.severity), coded_label(record.cause))
                history.setdefault(record.player_uid, []).append(injury)
            case fmsave.InjuryRecordKind.TYPED:
                if record.date >= today:
                    current[record.player_uid] = CurrentInjury(record.type_name, record.date)
    return {uid: tuple(sorted(found, key=lambda injury: injury.day)) for uid, found in history.items()}, current


def weighted_rating(rows: list[fmsave.PlayerSeasonStats]) -> float | None:
    rated = [(row.average_rating, row.rated_appearances) for row in rows if row.average_rating is not None]
    appearances = sum(count for _, count in rated)
    if not appearances:
        return None
    return round(sum(rating * count for rating, count in rated) / appearances, 2)


def optional_total(values: Iterable[int | None]) -> int | None:
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def season_totals(rows: list[fmsave.PlayerSeasonStats]) -> SeasonStats:
    return SeasonStats(
        minutes=sum(row.minutes for row in rows),
        starts=sum(row.starts for row in rows),
        substitute_appearances=sum(row.substitute_appearances for row in rows),
        average_rating=weighted_rating(rows),
        goals=sum(row.goals for row in rows),
        assists=sum(row.assists for row in rows),
        expected_goals=round(sum(row.expected_goals for row in rows), 2),
        expected_assists=round(sum(row.expected_assists for row in rows), 2),
        shots=sum(row.shots for row in rows),
        key_passes=sum(row.key_passes for row in rows),
        progressive_passes=sum(row.progressive_passes for row in rows),
        dribbles=sum(row.dribbles for row in rows),
        tackles_completed=sum(row.tackles_completed for row in rows),
        interceptions=sum(row.interceptions for row in rows),
        headers_won=optional_total(row.headers_won for row in rows),
        player_of_the_match=sum(row.player_of_the_match for row in rows),
    )


def season_records(rows: Iterable[fmsave.PlayerSeasonStats]) -> dict[int, SeasonStats]:
    by_player: dict[int, list[fmsave.PlayerSeasonStats]] = {}
    for row in rows:
        if row.kind is fmsave.SeasonStatsKind.OVERALL:
            by_player.setdefault(row.player_uid, []).append(row)
    return {uid: season_totals(found) for uid, found in by_player.items()}


def player_records(save: fmsave.Save, today: date) -> PlayerRecords:
    injuries, current = injury_records(optional_section(save.injuries), today)
    return PlayerRecords(injuries, current, season_records(optional_section(save.player_season_stats)))
