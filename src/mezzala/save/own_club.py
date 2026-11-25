from dataclasses import asdict

import fmsave

from mezzala.core.players import MentoringGroup, StaffMember, Tactic
from mezzala.save.labels import label
from mezzala.save.sections import optional_section

FIRST_TEAM_SLOT = 0

TACTIC_POSITION_CODES: dict[fmsave.TacticPosition, str] = {
    fmsave.TacticPosition.GOALKEEPER: "gk",
    fmsave.TacticPosition.DEFENDER_RIGHT: "dr",
    fmsave.TacticPosition.DEFENDER_LEFT: "dl",
    fmsave.TacticPosition.DEFENDER_CENTRE: "dc",
    fmsave.TacticPosition.DEFENSIVE_MIDFIELDER: "dm",
    fmsave.TacticPosition.MIDFIELDER_RIGHT: "mr",
    fmsave.TacticPosition.MIDFIELDER_LEFT: "ml",
    fmsave.TacticPosition.MIDFIELDER_CENTRE: "mc",
    fmsave.TacticPosition.ATTACKING_MIDFIELDER_RIGHT: "amr",
    fmsave.TacticPosition.ATTACKING_MIDFIELDER_LEFT: "aml",
    fmsave.TacticPosition.ATTACKING_MIDFIELDER_CENTRE: "amc",
    fmsave.TacticPosition.STRIKER_CENTRE: "stc",
}


def staff_member(person: fmsave.Staff) -> StaffMember | None:
    if person.name is None:
        return None
    ratings = person.attributes.to_display_scale() if person.attributes is not None else None
    shown = {name: value for name, value in asdict(ratings).items() if value is not None} if ratings else {}
    job = label(person.job.label.name) if person.job is not None else "unknown"
    return StaffMember(person.name, job, person.age, shown)


def club_staff(save: fmsave.Save, club_uid: int) -> tuple[StaffMember, ...]:
    members = (staff_member(person) for person in save.staff() if person.club_uid == club_uid)
    return tuple(member for member in members if member is not None)


def first_known(positions: tuple[fmsave.CodedValue[fmsave.TacticPosition], ...]) -> str | None:
    return next((code for p in positions if (code := TACTIC_POSITION_CODES.get(p.label)) is not None), None)


def slot_position(slot: fmsave.TacticSlot) -> str | None:
    return first_known(slot.in_possession_positions) or first_known(slot.out_of_possession_positions)


def first_team_tactics(save: fmsave.Save, club_uid: int) -> tuple[Tactic, ...]:
    return tuple(
        Tactic(tactic.name, label(tactic.mentality.label.name), tuple(slot_position(slot) for slot in tactic.slots))
        for tactic in optional_section(save.tactics)
        if tactic.club_uid == club_uid and tactic.team_slot == FIRST_TEAM_SLOT
    )


def mentoring_groups(save: fmsave.Save, club_uid: int) -> tuple[MentoringGroup, ...]:
    return tuple(
        MentoringGroup(group.label, tuple(uid for uid in group.member_uids if uid is not None))
        for group in optional_section(save.mentoring)
        if group.club_uid == club_uid
    )
