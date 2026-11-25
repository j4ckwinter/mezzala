from enum import StrEnum
from typing import Annotated

import fmsave
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mezzala.core.formations import DEFAULT_FORMATION, Formation, Shape, places_text, saved_shape, shape_for
from mezzala.core.lookup import AmbiguousPlayer, PlayerNotFound, find_player
from mezzala.core.money import stored_from_pounds
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup
from mezzala.core.roles import Side
from mezzala.core.view import View, shows_hidden_information
from mezzala.save.career import Career, Current
from mezzala.save.reader import UnreadableSave
from mezzala.server.reports import SaveContext, save_context
from mezzala.tools.development_check import CheckScope
from mezzala.tools.find_players import SearchScope, SortBy
from mezzala.tools.performance import PerformanceScope, PerformanceSort
from mezzala.tools.risers import RiserScope

DEFAULT_LIMIT = 10
RELEGATION_LOOKBACK_DAYS = 300
PERFORMANCE_MIN_MINUTES = 450
DEVELOPMENT_MIN_PA = 150
REGEN_MIN_PA = 120
RISER_MIN_CA_GAIN = 3


def optional_stored(pounds: float | None) -> int | None:
    return None if pounds is None else stored_from_pounds(pounds)


def read_current(career: Career) -> Current:
    try:
        return career.current()
    except (fmsave.FmsaveError, UnreadableSave, OSError) as error:
        raise ToolError(f"Could not read the save: {error}") from error


def target_player(snapshot: Snapshot, name: str, club: str | None = None) -> Player:
    try:
        return find_player(snapshot, name, club)
    except (PlayerNotFound, AmbiguousPlayer) as error:
        raise ToolError(str(error)) from error


def refuse_hidden_filters(view: View, filters: dict[str, bool]) -> None:
    used = [name for name, is_set in filters.items() if is_set]
    if used and not shows_hidden_information(view):
        raise ToolError(f"Fog of war is on, so {', '.join(used)} cannot be used: it filters on hidden ability.")


def with_formation(current: Current, asked: Formation | None) -> tuple[Shape, SaveContext]:
    if asked is not None:
        return shape_for(asked), save_context(current)
    saved = saved_shape(current.snapshot.tactics)
    if saved is None and current.snapshot.tactics:
        unreadable = (
            f"Your saved tactic '{current.snapshot.tactics[0].name}' has positions mezzala cannot read, so "
            f"{DEFAULT_FORMATION.value} is used; say which formation you play for a closer answer."
        )
        return shape_for(DEFAULT_FORMATION), save_context(current, [unreadable])
    if saved is None:
        return shape_for(DEFAULT_FORMATION), save_context(current)
    if saved.built_in:
        return saved.shape, save_context(
            current, [f"Formation {saved.shape.name}, from your saved tactic '{saved.tactic.name}'."]
        )
    own = (
        f"Your saved tactic '{saved.tactic.name}' matches none of the built-in formations, so its own shape is "
        f"used: {places_text(saved.shape)}."
    )
    return saved.shape, save_context(current, [own])


def one_of(choices: type[StrEnum]) -> str:
    return "One of: " + ", ".join(f'"{choice.value}"' for choice in choices)


FORMATION_DEFAULT = f"Defaults to the saved first-team tactic's shape, else {DEFAULT_FORMATION.value}."
FormationChoice = Annotated[Formation | None, Field(description=f"{FORMATION_DEFAULT} {one_of(Formation)}")]
FormationChoices = Annotated[list[Formation] | None, Field(description=f"Defaults to all. {one_of(Formation)}")]
PositionChoice = Annotated[PositionGroup | None, Field(description=one_of(PositionGroup))]
ClubChoice = Annotated[
    str | None,
    Field(
        description="The club the player is at now, to tell apart players who share a name. Leave it out "
        "unless an answer says the name is ambiguous."
    ),
]
ScopeChoice = Annotated[RiserScope, Field(description=one_of(RiserScope))]
SearchScopeChoice = Annotated[SearchScope, Field(description=one_of(SearchScope))]
SortChoice = Annotated[SortBy, Field(description=one_of(SortBy))]
CheckScopeChoice = Annotated[CheckScope, Field(description=one_of(CheckScope))]
SideChoice = Annotated[Side | None, Field(description=one_of(Side))]
PerformanceScopeChoice = Annotated[PerformanceScope, Field(description=one_of(PerformanceScope))]
PerformanceSortChoice = Annotated[PerformanceSort, Field(description=one_of(PerformanceSort))]
