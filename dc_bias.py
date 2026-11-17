"""Engineering model for an NPN voltage-divider BJT DC bias circuit.

This module is deliberately free of Flask, HTML, and HTTP concerns. It owns
input parsing, physical validation, the DC operating-point calculation, and
the forward-active region checks.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

PARAMETERS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_PARAMETERS = ("r1", "r2", "rc", "re")

SHARED_PARAMETERS = ("vcc", "beta", "vbe")

# ฟิลด์ตัวต้านทานของแต่ละโหมด — ใช้ทั้งตอน parse และตอนเลือก solver
MODE_FIELDS: dict[str, tuple[str, ...]] = {
    "divider": ("r1", "r2", "rc", "re"),
    "fixed": ("rb", "rc"),
    "emitter": ("rb", "rc", "re"),
}
BIAS_MODES = tuple(MODE_FIELDS)

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

MODE_DEFAULTS: dict[str, dict[str, str]] = {
    "divider": {
        "vcc": "12",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.7",
        "r_unit": "kohm",
    },
    "fixed": {
        "vcc": "12",
        "rb": "470",
        "rc": "2.2",
        "beta": "100",
        "vbe": "0.7",
        "r_unit": "kohm",
    },
    "emitter": {
        "vcc": "12",
        "rb": "470",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.7",
        "r_unit": "kohm",
    },
}

# คีย์ผลลัพธ์ + หน่วยของแต่ละคีย์ — ใช้ร่วมกันทั้งสามโหมด
OUTPUT_UNITS: dict[str, str] = {
    "vth_v": "V",
    "rth_kohm": "kΩ",
    "ib_ua": "µA",
    "ic_ma": "mA",
    "ie_ma": "mA",
    "ve_v": "V",
    "vb_v": "V",
    "vc_v": "V",
    "vce_v": "V",
    "power_q_mw": "mW",
}

MISSING_MESSAGE = "กรุณากรอกค่านี้"
NON_NUMERIC_MESSAGE = "ต้องเป็นตัวเลข เช่น 12 หรือ 2.2"
NON_FINITE_MESSAGE = "ต้องเป็นจำนวนจริงที่มีค่าจำกัด"
INVALID_UNIT_MESSAGE = "หน่วยความต้านทานไม่ถูกต้อง (เลือก Ω หรือ kΩ)"
INVALID_MODE_MESSAGE = "โหมดไบอัสไม่ถูกต้อง (เลือก Divider, Fixed หรือ Emitter)"

_NUMBER_PATTERN = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)

ASSUMPTIONS: tuple[str, ...] = (
    "β คงที่ตลอดช่วงการทำงาน",
    "VBE คงที่ตามค่าที่กรอก",
    "ไม่คิด Early effect และกระแสรั่ว",
    "อุณหภูมิคงที่ 25 °C",
)

REGION_LABELS = {
    "active": "Forward-Active",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
    "out_of_model": "นอกแบบจำลอง Forward-Active",
}

VCE_MODEL_LIMIT = 0.20
IB_NON_POSITIVE_WARNING = (
    "IB ≤ 0: แบบจำลอง Forward-Active ใช้ไม่ได้ "
    "(Lab นี้ไม่คำนวณค่า Cutoff หรือ Saturation)"
)
VCE_LOW_WARNING = (
    "VCE ≤ 0.20 V: แบบจำลอง Forward-Active อาจใช้ไม่ได้ "
    "(Lab นี้ไม่คำนวณค่า Saturation)"
)

CUTOFF_WARNING = (
    "Cutoff: VTH ≤ VBE ทำให้ทรานซิสเตอร์ไม่นำกระแส; "
    "แบบจำลอง Forward-Active ใช้ไม่ได้"
)
SATURATION_WARNING = (
    "Saturation: กำหนด VCE = 0.30 V; IC ถูกจำกัดด้วย RC และ RE "
    "ไม่ใช่ β × IB"
)
SATURATION_FALLBACK_WARNING = (
    "Saturation: ไม่สามารถแก้สมการ Saturation ด้วยค่า VBE นี้ได้ (IC ≤ 0); "
    "ตรวจสอบ VBE แล้วรายงานเป็น Cutoff"
)
VBE_RANGE_WARNING = (
    "VBE อยู่นอกช่วงปกติ 0.50–0.90 V; ตรวจสอบสมมติฐานอีกครั้ง"
)
NON_FINITE_RESULT_MESSAGE = (
    "ค่าที่คำนวณได้เกินขอบเขตตัวเลข กรุณาลดขนาดค่าที่กรอก"
)

SATURATION_ASSUMPTION = (
    "Saturation: กำหนด VCE = 0.30 V และหา IC จากวงจร RC/RE"
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


def parse_inputs(raw: Mapping[str, str], mode: str = "divider") -> dict[str, float]:
    """Parse and validate a submitted form for one bias mode.

    Only the fields that the selected mode needs are read, so a mode never
    requires the resistors of another mode. Resistances are converted from
    the chosen unit to ohms here — the solvers only ever see SI values.
    Every invalid field is collected so the page can show all errors at once.
    """
    if mode not in MODE_FIELDS:
        raise BiasInputError({"mode": INVALID_MODE_MESSAGE})

    resistors = MODE_FIELDS[mode]
    fields = (*SHARED_PARAMETERS, *resistors)

    errors: dict[str, str] = {}
    values: dict[str, float | None] = {
        field: _parse_number(field, raw.get(field), errors) for field in fields
    }

    unit = str(raw.get("r_unit", "ohm")).strip() or "ohm"
    if unit not in UNIT_FACTORS:
        errors["r_unit"] = INVALID_UNIT_MESSAGE

    vcc = values["vcc"]
    if vcc is not None and vcc <= 0:
        errors["vcc"] = "VCC ต้องมากกว่า 0 V"

    for field in resistors:
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
    for field in fields:
        value = values[field]
        assert value is not None
        parsed[field] = to_ohms(value, unit) if field in resistors else value
    return parsed


@dataclass(frozen=True)
class BiasResult:
    """DC operating point and the region judgement for one circuit."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]

    @property
    def ic_ma(self) -> float:
        return self.ic * 1_000.0

    @property
    def ib_ua(self) -> float:
        return self.ib * 1_000_000.0

    @property
    def ie_ma(self) -> float:
        return self.ie * 1_000.0

    @property
    def power_q_mw(self) -> float:
        return self.vce * self.ic * 1_000.0

    @property
    def rth_kohm(self) -> float:
        return self.rth / 1_000.0

    @property
    def region_label(self) -> str:
        return REGION_LABELS.get(self.region, self.region)


def _solve_saturation(
    vcc: float,
    rc: float,
    re: float,
    vth: float,
    rth: float,
    vbe: float,
) -> tuple[float, float, float, float, float, float] | None:
    """Solve the circuit with ``VCE`` fixed at the saturation threshold.

    In saturation the collector current is set by ``RC`` and ``RE``, not by
    ``beta * IB``. With ``VE = IE * RE``, ``VC = VE + VCE`` and
    ``IE = IC + IB``, the base loop ``VTH = IB * RTH + VBE + VE`` and the
    collector loop ``VCC = IC * RC + VCE + VE`` reduce to one equation in
    ``IC``.

    Returns ``(ib, ic, ie, ve, vb, vc)``, or ``None`` when the supplied
    ``VBE`` cannot produce a physical solution (``IC <= 0`` or ``IB < 0``).
    """
    vce = VCE_SATURATION_THRESHOLD
    share = re / (rth + re)
    ic = (vcc - vce - share * (vth - vbe)) / (rc + re - share * re)
    ib = (vth - vbe - ic * re) / (rth + re)
    if ic <= 0.0 or ib < 0.0:
        return None
    ie = ic + ib
    ve = ie * re
    return ib, ic, ie, ve, ve + vbe, ve + vce


def _ensure_finite(result: BiasResult) -> None:
    values = (
        result.vth,
        result.rth,
        result.ib,
        result.ic,
        result.ie,
        result.vb,
        result.ve,
        result.vc,
        result.vce,
    )
    if not all(math.isfinite(value) for value in values):
        raise BiasInputError({"__form__": NON_FINITE_RESULT_MESSAGE})


def solve_voltage_divider_bias(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Solve the DC operating point and classify the transistor region."""
    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)

    vbe_warning = (
        (VBE_RANGE_WARNING,)
        if not (VBE_TYPICAL_RANGE[0] <= vbe <= VBE_TYPICAL_RANGE[1])
        else ()
    )

    def cutoff_result(warning: str) -> BiasResult:
        result = BiasResult(
            vcc=vcc,
            r1=r1,
            r2=r2,
            rc=rc,
            re=re,
            beta=beta,
            vbe=vbe,
            vth=vth,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=vcc,
            vce=vcc,
            region="cutoff",
            warnings=(warning,) + vbe_warning,
            assumptions=ASSUMPTIONS,
        )
        _ensure_finite(result)
        return result

    if vth <= vbe:
        return cutoff_result(CUTOFF_WARNING)

    ib = (vth - vbe) / (rth + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    if vce <= VCE_SATURATION_THRESHOLD:
        saturation = _solve_saturation(vcc, rc, re, vth, rth, vbe)
        if saturation is None:
            return cutoff_result(SATURATION_FALLBACK_WARNING)
        ib, ic, ie, ve, vb, vc = saturation
        vce = VCE_SATURATION_THRESHOLD
        region = "saturation"
        warnings = (SATURATION_WARNING,) + vbe_warning
        assumptions = ASSUMPTIONS + (SATURATION_ASSUMPTION,)
    else:
        region = "active"
        warnings = vbe_warning
        assumptions = ASSUMPTIONS

    result = BiasResult(
        vcc=vcc,
        r1=r1,
        r2=r2,
        rc=rc,
        re=re,
        beta=beta,
        vbe=vbe,
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
        assumptions=assumptions,
    )
    _ensure_finite(result)
    return result


def _check_finite_output(values: Mapping[str, float]) -> None:
    if not all(math.isfinite(value) for value in values.values()):
        raise BiasInputError({"__form__": NON_FINITE_RESULT_MESSAGE})


def _output(
    mode: str,
    region: str,
    quantities: dict[str, float],
    warnings: tuple[str, ...],
    assumptions: tuple[str, ...] = ASSUMPTIONS,
) -> dict[str, object]:
    """Build the dict that every mode returns to the Flask layer."""
    _check_finite_output(quantities)
    return {
        "mode": mode,
        "region": region,
        "values": quantities,
        "warnings": warnings,
        "assumptions": assumptions,
    }


def _quantities(
    ib: float,
    ic: float,
    ie: float,
    ve: float,
    vb: float,
    vc: float,
    vce: float,
    extra: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Convert SI results to the display keys shared by all three modes."""
    quantities = {
        "ib_ua": ib * 1_000_000.0,
        "ic_ma": ic * 1_000.0,
        "ie_ma": ie * 1_000.0,
        "ve_v": ve,
        "vb_v": vb,
        "vc_v": vc,
        "vce_v": vce,
        "power_q_mw": vce * ic * 1_000.0,
    }
    if extra:
        quantities.update(extra)
    return quantities


def _lab3_model_checks(
    ib: float,
    vce: float,
    vbe: float,
) -> tuple[bool, tuple[str, ...]]:
    """Lab 3 rule: warn when the forward-active model may not apply.

    The handout does not ask for a cutoff/saturation solution in the new
    modes, so the computed values are shown together with a warning.
    """
    warnings: list[str] = []
    out_of_model = False
    if ib <= 0.0:
        warnings.append(IB_NON_POSITIVE_WARNING)
        out_of_model = True
    elif vce <= VCE_MODEL_LIMIT:
        warnings.append(VCE_LOW_WARNING)
        out_of_model = True
    if not (VBE_TYPICAL_RANGE[0] <= vbe <= VBE_TYPICAL_RANGE[1]):
        warnings.append(VBE_RANGE_WARNING)
    return out_of_model, tuple(warnings)


def solve_fixed_bias(
    vcc: float,
    rb: float,
    rc: float,
    beta: float,
    vbe: float,
) -> dict[str, object]:
    """Fixed bias: RB from VCC to the base, emitter grounded.

    ``IB = (VCC - VBE) / RB``, ``IC = beta * IB``, ``VE = 0``,
    ``VB = VBE``, ``VC = VCC - IC * RC``, ``VCE = VC``.
    """
    ib = (vcc - vbe) / rb
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = 0.0
    vb = vbe
    vc = vcc - ic * rc
    vce = vc - ve

    out_of_model, warnings = _lab3_model_checks(ib, vce, vbe)
    return _output(
        "fixed",
        "out_of_model" if out_of_model else "active",
        _quantities(ib, ic, ie, ve, vb, vc, vce),
        warnings,
    )


def solve_emitter_bias(
    vcc: float,
    rb: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> dict[str, object]:
    """Emitter bias: RB from VCC to the base, RE from emitter to ground.

    ``IB = (VCC - VBE) / (RB + (beta + 1) * RE)``,
    ``IC = beta * IB``, ``IE = (beta + 1) * IB``, ``VE = IE * RE``,
    ``VB = VE + VBE``, ``VC = VCC - IC * RC``, ``VCE = VC - VE``.
    """
    ib = (vcc - vbe) / (rb + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    out_of_model, warnings = _lab3_model_checks(ib, vce, vbe)
    return _output(
        "emitter",
        "out_of_model" if out_of_model else "active",
        _quantities(ib, ic, ie, ve, vb, vc, vce),
        warnings,
    )


def _divider_output(result: BiasResult) -> dict[str, object]:
    quantities = _quantities(
        result.ib,
        result.ic,
        result.ie,
        result.ve,
        result.vb,
        result.vc,
        result.vce,
        extra={"vth_v": result.vth, "rth_kohm": result.rth_kohm},
    )
    return _output(
        "divider",
        result.region,
        quantities,
        result.warnings,
        result.assumptions,
    )


def solve_bias(mode: str, values: Mapping[str, float]) -> dict[str, object]:
    """Dispatch to the solver of the selected mode.

    An unknown mode is an input error; it is never treated as Divider.
    """
    if mode == "divider":
        return _divider_output(solve_voltage_divider_bias(**values))
    if mode == "fixed":
        return solve_fixed_bias(**values)
    if mode == "emitter":
        return solve_emitter_bias(**values)
    raise BiasInputError({"mode": INVALID_MODE_MESSAGE})
