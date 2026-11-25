from enum import IntEnum

import fmsave

UNKNOWN_LABEL = "UNKNOWN"


def label(name: str) -> str:
    return name.lower().replace("_", " ")


def coded_label[E: IntEnum](value: fmsave.CodedValue[E] | None) -> str | None:
    if value is None or value.label.name == UNKNOWN_LABEL:
        return None
    return label(value.label.name)
