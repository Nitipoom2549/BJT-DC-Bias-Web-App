"""Engineering model for an NPN voltage-divider BJT DC bias circuit.

This module is deliberately free of Flask, HTML, and HTTP concerns. It owns
input parsing, physical validation, the DC operating-point calculation, and
the forward-active region checks.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping

PARAMETERS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_PARAMETERS = ("r1", "r2", "rc", "re")

VCE_SATURATION_THRESHOLD = 0.30
VBE_TYPICAL_RANGE = (0.50, 0.90)

DEFAULTS: dict[str, str] = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
    "r_unit": "kohm",
}

UNIT_FACTORS = {"ohm": 1.0, "kohm": 1000.0}

MISSING_MESSAGE = "กรุณากรอกค่านี้"
NON_NUMERIC_MESSAGE = "ต้องเป็นตัวเลข เช่น 12 หรือ 2.2"
NON_FINITE_MESSAGE = "ต้องเป็นจำนวนจริงที่มีค่าจำกัด"
INVALID_UNIT_MESSAGE = "หน่วยความต้านทานไม่ถูกต้อง (เลือก Ω หรือ kΩ)"

_NUMBER_PATTERN = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)


class BiasInputError(ValueError):
    """Raised when submitted values are missing, non-numeric, or unphysical."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors: dict[str, str] = dict(errors)
        super().__init__("; ".join(self.errors.values()))


def to_ohms(value: float, unit: str = "ohm") -> float:
    """Convert a resistance in ``unit`` to ohms."""
    try:
        factor = UNIT_FACTORS[unit]
    except KeyError:
        raise BiasInputError({"r_unit": INVALID_UNIT_MESSAGE}) from None
    return float(value) * factor


def _parse_number(field: str, text: object, errors: dict[str, str]) -> float | None:
    if text is None:
        errors[field] = MISSING_MESSAGE
        return None

    trimmed = str(text).strip()
    if not trimmed:
        errors[field] = MISSING_MESSAGE
        return None

    if _NUMBER_PATTERN.fullmatch(trimmed) is None:
        errors[field] = NON_NUMERIC_MESSAGE
        return None

    try:
        number = float(trimmed)
    except ValueError:
        errors[field] = NON_NUMERIC_MESSAGE
        return None

    if not math.isfinite(number):
        errors[field] = NON_FINITE_MESSAGE
        return None

    return number


def parse_inputs(raw: Mapping[str, str]) -> dict[str, float]:
    """Parse and validate a submitted form.

    Resistances are returned in ohms; all other values keep their SI unit.
    Every invalid field is collected so the page can show all errors at once.
    """
    errors: dict[str, str] = {}
    values: dict[str, float | None] = {
        field: _parse_number(field, raw.get(field), errors) for field in PARAMETERS
    }

    unit = str(raw.get("r_unit", "ohm")).strip() or "ohm"
    if unit not in UNIT_FACTORS:
        errors["r_unit"] = INVALID_UNIT_MESSAGE

    vcc = values["vcc"]
    if vcc is not None and vcc <= 0:
        errors["vcc"] = "VCC ต้องมากกว่า 0 V"

    for field in RESISTOR_PARAMETERS:
        resistance = values[field]
        if resistance is not None and resistance <= 0:
            errors[field] = "ความต้านทานต้องมากกว่า 0 Ω"

    beta = values["beta"]
    if beta is not None and beta <= 0:
        errors["beta"] = "β ต้องมากกว่า 0"

    vbe = values["vbe"]
    if vbe is not None:
        if vbe < 0:
            errors["vbe"] = "VBE ต้องไม่ติดลบ"
        elif vcc is not None and vbe >= vcc:
            errors["vbe"] = "VBE ต้องน้อยกว่า VCC"

    if errors:
        raise BiasInputError(errors)

    parsed: dict[str, float] = {}
    for field in PARAMETERS:
        value = values[field]
        assert value is not None
        parsed[field] = to_ohms(value, unit) if field in RESISTOR_PARAMETERS else value
    return parsed
