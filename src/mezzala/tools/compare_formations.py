from dataclasses import dataclass

from mezzala.core.formations import Formation
from mezzala.core.lineup import (
    ACCOMPLISHED_PENALTY,
    Lineup,
    Place,
    StarterEntry,
    ability_in,
    pick_lineup,
    starter_entries,
)
from mezzala.core.players import Snapshot
from mezzala.core.positions import Fit, fit
from mezzala.core.squad import available_squad
from mezzala.core.view import Measure, View, measure, rating

SCORE_TIE_MARGIN = 0.5

EXPLANATION = (
    "Each formation gets the best eleven the squad can field, using each player once. The score is the "
    "average ability of that eleven in their places: accomplished (non-natural) positions count "
    f"{ACCOMPLISHED_PENALTY} CA lower and an empty place counts as 0. Formations within {SCORE_TIE_MARGIN} of "
    "the best score are effectively tied. It measures squad fit, not how the match engine rates the shape."
)


@dataclass(frozen=True)
class FormationFit:
    formation: str
    rank: int
    score: Measure
    tied_with_best: bool
    median_ability: Measure
    accomplished_starters: int
    empty_places: int
    weakest_place: str
    eleven: list[StarterEntry]


@dataclass(frozen=True)
class FormationComparison:
    explanation: str
    ranking: list[FormationFit]


def place_ability(place: Place) -> float:
    if place.player is None:
        return 0.0
    return ability_in(place.player, place.group) or 0.0


def score(lineup: Lineup) -> float:
    return round(sum(place_ability(place) for place in lineup.places) / len(lineup.places), 1)


def weakest_place(lineup: Lineup, view: View) -> str:
    place = min(lineup.places, key=place_ability)
    if place.player is None:
        return f"{place.group.value}: nobody"
    return f"{place.group.value}: {place.player.name} ({rating(view, place.player.current_ability)})"


def formation_fit(lineup: Lineup, rank: int, best: float, view: View) -> FormationFit:
    accomplished = [p for p in lineup.places if p.player is not None and fit(p.player, p.group) is Fit.ACCOMPLISHED]
    return FormationFit(
        formation=lineup.formation.value,
        rank=rank,
        score=measure(view, score(lineup)),
        tied_with_best=round(best - score(lineup), 1) <= SCORE_TIE_MARGIN,
        median_ability=measure(view, lineup.median_ability()),
        accomplished_starters=len(accomplished),
        empty_places=sum(1 for place in lineup.places if place.player is None),
        weakest_place=weakest_place(lineup, view),
        eleven=starter_entries(lineup, view),
    )


def compare_formations(snapshot: Snapshot, formations: list[Formation], view: View) -> FormationComparison:
    squad = available_squad(snapshot)
    lineups = sorted((pick_lineup(squad, f) for f in formations), key=score, reverse=True)
    best = score(lineups[0]) if lineups else 0.0
    return FormationComparison(
        EXPLANATION, [formation_fit(lineup, rank, best, view) for rank, lineup in enumerate(lineups, start=1)]
    )
