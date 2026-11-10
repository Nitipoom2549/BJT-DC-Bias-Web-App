"""Engineering core for the NPN BJT voltage-divider DC bias calculator.

This module deliberately has no Flask, HTML or HTTP imports.  It can therefore
be unit-tested as pure engineering logic, independent of the web layer.

Model
-----
Voltage-divider bias, NPN, common emitter, forward-active approximation:

    VTH = VCC * R2 / (R1 + R2)
    RTH = R1 * R2 / (R1 + R2)
    IB  = (VTH - VBE) / (RTH + (beta + 1) * RE)
    IC  = beta * IB
    IE  = (beta + 1) * IB
    VE  = IE * RE
    VB  = VE + VBE
    VC  = VCC - IC * RC
    VCE = VC - VE

The model is intentionally simple.  Results that leave the forward-active
region are reported together with an explicit warning; they must not be read
as validated SPICE output.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

# Parameter names used by both the form and the engineering function.
PARAMETERS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_PARAMETERS = ("r1", "r2", "rc", "re")

# Boundary used only to flag a model limitation.  It is not a SPICE model.
VCE_SATURATION_THRESHOLD = 0.30  # V

# Typical silicon-BJT base-emitter voltage at room temperature.
VBE_TYPICAL_RANGE = (0.50, 0.90)  # V

# Defaults shown by the web form.  The handout's reference circuit is
# VCC=12 V, R1=100 kOhm, R2=22 kOhm, RC=2.2 kOhm, RE=1 kOhm, beta=100.
DEFAULTS = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
    "r_unit": "kohm",
}

_UNIT_FACTORS = {
    "ohm": 1.0,
    "Ω": 1.0,
    "kohm": 1_000.0,
    "kΩ": 1_000.0,
}

_ASSUMPTIONS = (
    "Forward-Active approximation: β คงที่ และ VBE คงที่ตลอดการคำนวณ",
    "อุณหภูมิคงที่ (ประมาณ 25 °C) ไม่คิด Early effect, leakage และค่าคลาดเคลื่อนของอุปกรณ์",
    "ตัวต้านทานเป็นอุดมคติ และแหล่งจ่าย VCC ไม่มีความต้านทานภายใน",
    "วงจรเป็น NPN Common Emitter แบบ Voltage-Divider Bias ตามสมการที่แสดงในหน้าเว็บ",
)


class BiasInputError(ValueError):
    """Raised when form values are missing, non-numeric or physically invalid.

    ``errors`` maps a parameter name (or ``r_unit``) to a short, user-readable
    Thai message so the Flask layer can render it next to the matching field.
    """

    def __init__(self, errors: Mapping[str, str]):
        self.errors = dict(errors)
        super().__init__("; ".join(f"{key}: {msg}" for key, msg in self.errors.items()))


@dataclass(frozen=True)
class BiasResult:
    """Solved DC operating point.  All currents are in A, voltages in V."""

    # Inputs after unit conversion
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float

    # Small-signal/Thevenin equivalent of the base divider
    vth: float
    rth: float

    # Operating point
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float

    region: str
    warnings: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = _ASSUMPTIONS

    @property
    def ic_ma(self) -> float:
        return self.ic * 1e3

    @property
    def ib_ua(self) -> float:
        return self.ib * 1e6

    @property
    def ie_ma(self) -> float:
        return self.ie * 1e3

    @property
    def power_q_mw(self) -> float:
        """Approximate collector dissipation of the transistor, in mW."""
        return self.vce * self.ic * 1e3

    @property
    def region_label(self) -> str:
        return {
            "active": "Active (Forward-Active)",
            "cutoff": "Cutoff (OFF)",
            "saturation": "Saturation",
        }.get(self.region, self.region)


def parse_inputs(raw: Mapping[str, str]) -> dict[str, float]:
    """Parse the seven form fields into finite floats.

    Missing and non-numeric values raise :class:`BiasInputError` with one
    message per field.  Physical constraints (positive resistances etc.) are
    checked by :func:`solve_voltage_divider_bias`.
    """
    errors: dict[str, str] = {}
    parsed: dict[str, float] = {}

    for name in PARAMETERS:
        text = str(raw.get(name, "") or "").strip()
        if not text:
            errors[name] = "กรุณากรอกค่านี้"
            continue
        try:
            value = float(text)
        except (TypeError, ValueError):
            errors[name] = "ต้องเป็นตัวเลข เช่น 12 หรือ 2.2"
            continue
        if not isfinite(value):
            errors[name] = "ต้องเป็นจำนวนจริงที่มีค่าจำกัด"
            continue
        parsed[name] = value

    if errors:
        raise BiasInputError(errors)
    return parsed


def to_ohms(value: float, unit: str = "ohm") -> float:
    """Convert a resistance entered in ohm or kOhm to ohm."""
    try:
        factor = _UNIT_FACTORS[unit]
    except KeyError as exc:
        raise BiasInputError(
            {"r_unit": "หน่วยความต้านทานไม่ถูกต้อง (เลือก Ω หรือ kΩ)"}
        ) from exc
    return float(value) * factor


def solve_voltage_divider_bias(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Solve the voltage-divider bias operating point.

    Raises :class:`BiasInputError` when an input is non-numeric or outside the
    physically meaningful range.  If the operating point is outside the
    forward-active region, a result is still returned but ``region`` is
    ``"cutoff"``/``"saturation"`` and ``warnings`` explains the limitation.
    """
    raw = {
        "vcc": vcc,
        "r1": r1,
        "r2": r2,
        "rc": rc,
        "re": re,
        "beta": beta,
        "vbe": vbe,
    }

    errors: dict[str, str] = {}
    values: dict[str, float] = {}

    for name, value in raw.items():
        if isinstance(value, bool):
            errors[name] = "ต้องเป็นตัวเลข"
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors[name] = "ต้องเป็นตัวเลข"
            continue
        if not isfinite(number):
            errors[name] = "ต้องเป็นจำนวนจริงที่มีค่าจำกัด"
            continue
        values[name] = number

    if values:
        if values.get("vcc", 1.0) <= 0:
            errors["vcc"] = "VCC ต้องมากกว่า 0 V"
        for name in RESISTOR_PARAMETERS:
            if name in values and values[name] <= 0:
                errors[name] = "ความต้านทานต้องมากกว่า 0 Ω"
        if "beta" in values and values["beta"] <= 0:
            errors["beta"] = "β ต้องมากกว่า 0"
        if "vbe" in values:
            if values["vbe"] < 0:
                errors["vbe"] = "VBE ต้องไม่ติดลบ"
            elif "vcc" in values and values["vbe"] >= values["vcc"]:
                errors["vbe"] = "VBE ต้องน้อยกว่า VCC"

    if errors:
        raise BiasInputError(errors)

    vcc = values["vcc"]
    r1 = values["r1"]
    r2 = values["r2"]
    rc = values["rc"]
    re = values["re"]
    beta = values["beta"]
    vbe = values["vbe"]

    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)
    denominator = rth + (beta + 1.0) * re

    # ------------------------------------------------------------------
    # Cutoff: the divider cannot forward-bias the base-emitter junction.
    # ------------------------------------------------------------------
    if vth <= vbe:
        warning = (
            f"โหมด Cutoff: VTH = {vth:.3f} V ≤ VBE = {vbe:.3f} V ทำให้ IB ≈ 0; "
            "สมการ Forward-Active ใช้ไม่ได้ ค่า VC = VCC และ VE = 0 เป็นเพียง "
            "ขอบเขตของแบบจำลอง ไม่ใช่ผลที่ผ่านการตรวจสอบด้วย SPICE"
        )
        return BiasResult(
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
            warnings=(warning,),
        )

    ib = (vth - vbe) / denominator
    if ib <= 0:  # Numerical safety net, effectively the same cutoff case.
        warning = (
            "โหมด Cutoff: กระแสฐานที่คำนวณได้มีค่า ≤ 0; "
            "สมการ Forward-Active ใช้ไม่ได้"
        )
        return BiasResult(
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
            warnings=(warning,),
        )

    ic = beta * ib
    ie = ic + ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    warnings: list[str] = []

    if not (VBE_TYPICAL_RANGE[0] <= vbe <= VBE_TYPICAL_RANGE[1]):
        warnings.append(
            f"VBE = {vbe:.3f} V อยู่นอกช่วงปกติของ BJT ซิลิคอน "
            f"({VBE_TYPICAL_RANGE[0]:.1f}–{VBE_TYPICAL_RANGE[1]:.1f} V); "
            "ตรวจสอบค่าที่กรอกก่อนใช้ผลลัพธ์"
        )

    if vce <= VCE_SATURATION_THRESHOLD:
        region = "saturation"
        warnings.append(
            f"โหมด Saturation: VCE = {vce:.3f} V ≤ {VCE_SATURATION_THRESHOLD:.2f} V; "
            "สมการ Forward-Active ใช้ไม่ได้ ค่า IC จากสมการจึงสูงเกินความเป็นจริง "
            "และ VCE จริงจะถูกจำกัดใกล้ค่าอิ่มตัว ควรตรวจสอบด้วย SPICE หรือการวัดจริง"
        )
    else:
        region = "active"

    return BiasResult(
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
        warnings=tuple(warnings),
    )
