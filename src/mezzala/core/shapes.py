from dataclasses import dataclass

from mezzala.core.positions import GROUP_OF_POSITION_CODE, PositionGroup
from mezzala.core.roles import Role, Side, find_role

SLOT_SEPARATOR = ":"
CENTRAL_SLOT_PREFIXES = ("STC", "AMC", "DMC", "MC", "DC")
WIDE_SLOT_CODES = {
    "DL": "dl", "DR": "dr", "WBL": "wbl", "WBR": "wbr", "ML": "ml", "MR": "mr", "AML": "aml", "AMR": "amr",
}  # fmt: skip
CENTRAL_POSITION_CODES = {"STC": "stc", "AMC": "amc", "DMC": "dm", "MC": "mc", "DC": "dc"}
SINGLE_SLOT_CODES = {"GK": "gk", "DM": "dm", "ST": "stc"}
SIDE_LETTERS = {"L": Side.LEFT, "R": Side.RIGHT}


class BadSlot(ValueError):
    pass


@dataclass(frozen=True)
class Slot:
    label: str
    group: PositionGroup
    side: Side | None
    role: Role


def position_of(label: str) -> tuple[str, Side | None]:
    if label in SINGLE_SLOT_CODES:
        return SINGLE_SLOT_CODES[label], None
    if label in WIDE_SLOT_CODES:
        return WIDE_SLOT_CODES[label], SIDE_LETTERS[label[-1]]
    for prefix in CENTRAL_SLOT_PREFIXES:
        rest = label.removeprefix(prefix)
        if rest != label and rest in ("", *SIDE_LETTERS):
            return CENTRAL_POSITION_CODES[prefix], SIDE_LETTERS.get(rest)
    raise BadSlot(
        f"'{label}' is not a slot mezzala knows. Use FM's position codes: GK, DL, DCL, DC, DCR, DR, WBL, WBR, "
        "DM, DMCL, DMCR, ML, MCL, MC, MCR, MR, AML, AMCL, AMC, AMCR, AMR, STCL, STC, STCR."
    )


def parse_slot(text: str) -> Slot:
    label, separator, role = text.partition(SLOT_SEPARATOR)
    if not separator or not role.strip():
        raise BadSlot(f"'{text}' needs a slot and a role, like 'AML: inside forward'.")
    code, side = position_of(label.strip().upper())
    return Slot(label.strip().upper(), GROUP_OF_POSITION_CODE[code], side, find_role(role))
