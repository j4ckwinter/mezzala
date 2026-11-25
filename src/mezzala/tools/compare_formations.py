from dataclasses import dataclass, replace

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
    score: float
    tied_with_best: bool
    median_ability: float
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


def weakest_place(lineup: Lineup) -> str:
    place = min(lineup.places, key=place_ability)
    if place.player is None:
        return f"{place.group.value}: nobody"
    return f"{place.group.value}: {place.player.name} ({place.player.current_ability})"


def formation_fit(lineup: Lineup) -> FormationFit:
    accomplished = [p for p in lineup.places if p.player is not None and fit(p.player, p.group) is Fit.ACCOMPLISHED]
    return FormationFit(
        formation=lineup.formation.value,
        rank=0,
        score=score(lineup),
        tied_with_best=False,
        median_ability=lineup.median_ability(),
        accomplished_starters=len(accomplished),
        empty_places=sum(1 for place in lineup.places if place.player is None),
        weakest_place=weakest_place(lineup),
        eleven=starter_entries(lineup),
    )


def compare_formations(snapshot: Snapshot, formations: list[Formation]) -> FormationComparison:
    squad = available_squad(snapshot)
    fits = sorted((formation_fit(pick_lineup(squad, f)) for f in formations), key=lambda f: f.score, reverse=True)
    best = fits[0].score if fits else 0.0
    ranked = [
        replace(fit, rank=rank, tied_with_best=round(best - fit.score, 1) <= SCORE_TIE_MARGIN)
        for rank, fit in enumerate(fits, start=1)
    ]
    return FormationComparison(EXPLANATION, ranked)
