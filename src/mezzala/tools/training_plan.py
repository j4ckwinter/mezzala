from dataclasses import dataclass
from enum import StrEnum

from mezzala.core.growth import projected_growth
from mezzala.core.players import Player, Snapshot
from mezzala.core.positions import PositionGroup, covers, fit, primary_group
from mezzala.core.profile import KEY_ATTRIBUTES, attribute_label, position_score
from mezzala.core.squad import available_squad
from mezzala.core.view import View, shows_hidden_information, signed_amount_text

FOCUS_ATTRIBUTES = 3
MAX_ATTRIBUTE = 20
INJURY_PRONE_FROM = 14
LOW_NATURAL_FITNESS_BELOW = 11
VETERAN_AGE = 32
RECENT_INJURIES_FOR_CAUTION = 2
YOUNG_ENOUGH_FOR_A_MENTOR = 23
MENTOR_MIN_AGE = 26
MENTOR_MIN_PROFESSIONALISM = 15
MENTOR_MIN_DETERMINATION = 14
MENTORS_SHOWN = 3
TRAIT_SKILL_NEEDED = 13
TRAIT_SKILL_TO_LEARN = 15


class Intensity(StrEnum):
    LOWER = "lower intensity"
    NORMAL = "normal intensity"


@dataclass(frozen=True)
class TraitRule:
    trait: str
    needs: tuple[str, ...]
    learn_for: tuple[PositionGroup, ...]


TRAIT_RULES = (
    TraitRule("dives into tackles", ("tackling",), ()),
    TraitRule("shoots from distance", ("long_shots",), ()),
    TraitRule("tries killer balls often", ("passing", "vision"), (PositionGroup.ATTACKING_MIDFIELD,)),
    TraitRule("runs with ball often", ("dribbling",), (PositionGroup.LEFT_WING, PositionGroup.RIGHT_WING)),
    TraitRule("tries long range passes", ("passing",), ()),
    TraitRule("dictates tempo", ("passing", "vision", "decisions"), (PositionGroup.CENTRAL_MIDFIELD,)),
    TraitRule("likes to try to beat offside trap", ("off_the_ball", "pace"), (PositionGroup.STRIKER,)),
    TraitRule("crosses early", ("crossing",), (PositionGroup.LEFT_BACK, PositionGroup.RIGHT_BACK)),
)


@dataclass(frozen=True)
class FocusAttribute:
    attribute: str
    now: int


@dataclass(frozen=True)
class TrainingPlan:
    player: str
    age: int
    train_for: str
    fit_there: str
    key_attribute_score: float
    additional_focus: list[FocusAttribute]
    intensity: str
    why_this_intensity: list[str]
    traits_to_unlearn: list[str]
    traits_to_learn: list[str]
    current_mentoring_group: list[str]
    suggested_mentors: list[str]
    projected_gain_next_season: str
    explanation: str


EXPLANATION = (
    "FM27 trains a player for a position or role plus one additional attribute focus. The plan picks the "
    "position his key attributes suit best (or the one asked for) and the key attributes furthest from 20 for the "
    "focus. Traits are judged on the attributes they rely on. The save does not store the training you have set, "
    "so compare this with what he is doing now."
)


def best_position(player: Player) -> PositionGroup:
    playable = [group for group in PositionGroup if covers(player, group)]
    return max(playable, key=lambda group: position_score(player, group), default=primary_group(player))


def additional_focus(player: Player, group: PositionGroup) -> list[FocusAttribute]:
    room = [name for name in KEY_ATTRIBUTES[group] if player.attributes[name] < MAX_ATTRIBUTE]
    weakest = sorted(room, key=lambda name: player.attributes[name])[:FOCUS_ATTRIBUTES]
    return [FocusAttribute(attribute_label(name), player.attributes[name]) for name in weakest]


def intensity(player: Player, view: View) -> tuple[Intensity, list[str]]:
    reasons: list[str] = []
    if shows_hidden_information(view) and player.attributes["injury_proneness"] >= INJURY_PRONE_FROM:
        reasons.append("he is prone to injury")
    if player.attributes["natural_fitness"] < LOW_NATURAL_FITNESS_BELOW:
        reasons.append("his natural fitness is low")
    if player.age >= VETERAN_AGE:
        reasons.append(f"he is {player.age}")
    if len(player.injuries) >= RECENT_INJURIES_FOR_CAUTION:
        reasons.append(f"{len(player.injuries)} injuries in the last two years")
    return (Intensity.LOWER, reasons) if reasons else (Intensity.NORMAL, [])


def good_enough(player: Player, rule: TraitRule, level: int) -> bool:
    return all(player.attributes[name] >= level for name in rule.needs)


def traits_to_unlearn(player: Player) -> list[str]:
    return [
        f"{rule.trait} (needs better {', '.join(attribute_label(name) for name in rule.needs)})"
        for rule in TRAIT_RULES
        if rule.trait in player.traits and not good_enough(player, rule, TRAIT_SKILL_NEEDED)
    ]


def traits_to_learn(player: Player, group: PositionGroup) -> list[str]:
    return [
        rule.trait
        for rule in TRAIT_RULES
        if group in rule.learn_for
        and rule.trait not in player.traits
        and good_enough(player, rule, TRAIT_SKILL_TO_LEARN)
    ]


def mentoring_group(player: Player, snapshot: Snapshot) -> list[str]:
    names = {member.uid: member.name for member in snapshot.players}
    for group in snapshot.mentoring:
        if player.uid in group.member_uids:
            return [names[uid] for uid in group.member_uids if uid != player.uid and uid in names]
    return []


def is_role_model(candidate: Player) -> bool:
    return (
        candidate.age >= MENTOR_MIN_AGE
        and candidate.professionalism >= MENTOR_MIN_PROFESSIONALISM
        and candidate.attributes["determination"] >= MENTOR_MIN_DETERMINATION
    )


def suggested_mentors(player: Player, group: PositionGroup, snapshot: Snapshot) -> list[str]:
    if player.age > YOUNG_ENOUGH_FOR_A_MENTOR:
        return []
    models = [p for p in available_squad(snapshot) if p.uid != player.uid and is_role_model(p)]
    models.sort(
        key=lambda p: (covers(p, group), p.professionalism + p.attributes["determination"], p.reputation),
        reverse=True,
    )
    return [p.name for p in models[:MENTORS_SHOWN]]


def training_plan(player: Player, snapshot: Snapshot, asked: PositionGroup | None, view: View) -> TrainingPlan:
    group = asked or best_position(player)
    level, reasons = intensity(player, view)
    return TrainingPlan(
        player=player.name,
        age=player.age,
        train_for=group.value,
        fit_there=fit(player, group).value,
        key_attribute_score=position_score(player, group),
        additional_focus=additional_focus(player, group),
        intensity=level.value,
        why_this_intensity=reasons,
        traits_to_unlearn=traits_to_unlearn(player),
        traits_to_learn=traits_to_learn(player, group),
        current_mentoring_group=mentoring_group(player, snapshot),
        suggested_mentors=suggested_mentors(player, group, snapshot),
        projected_gain_next_season=signed_amount_text(view, projected_growth(player).ability_gain, 1),
        explanation=EXPLANATION,
    )
