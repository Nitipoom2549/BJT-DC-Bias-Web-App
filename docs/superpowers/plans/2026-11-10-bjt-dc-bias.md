# BJT Voltage-Divider DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested, multi-file Flask app that computes and displays the NPN voltage-divider DC operating point with Thai validation and forward-active region warnings.

**Architecture:** A pure-Python `dc_bias.py` owns parsing, validation, engineering math, and region logic. A thin `app.py` owns HTTP routes and calls it. Jinja renders one server-side page; CSS only styles it. Tests use the standard library `unittest`, split into engineering and Flask test-client files.

**Tech Stack:** Python 3.14.2 (`py`), Flask 3.x, Jinja2, `unittest`, HTML/CSS, no JavaScript.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- Runtime is Python 3.14.2, invoked as `py` on this machine. Do not assume a `python` alias.
- Only production dependency is `Flask>=3.1,<4.0`.
- Tests use `unittest`; run with `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
- UI labels and user-facing errors are Thai; symbols and units are standard (`V`, `A`, `mA`, `µA`, `Ω`, `kΩ`).
- Bind to `127.0.0.1:5000` only.
- Invalid POST returns HTTP 400 while re-rendering the form; valid POST returns HTTP 200.
- All displayed values carry units.
- Scope is DC Bias only: no AC, transient, SPICE, other bias types, FET, or schematic editor.
- The prototype `app.py` and `dc_bias.py` are deleted and rebuilt test-first. Keep `requirements.txt` and `.gitignore`.
- **Commit protocol:** the agent must **never** run `git commit` or `git push`. Each task ends with a handoff: report changed files and test evidence, suggest a summary, and the owner commits in GitHub Desktop on branch `lab02-dc-bias`.
- Reference case: `VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V`.
- Hand-derived reference: `VTH=2.163934 V`, `RTH=18032.787 Ω`, `IB=12.298581 µA`, `IC=1.229858 mA`, `IE=1.242157 mA`, `VE=1.242157 V`, `VB=1.942157 V`, `VC=9.294312 V`, `VCE=8.052155 V`.

## Review Focus

These are the input classes most likely to bite a real user even though the spec does not enumerate them. Each line is pinned to a test in the task that owns the code.

1. Numeric text with thousands separators (`100,000`) — a reasonable person expects either correct parsing or a clear numeric error, never a crash or a silently wrong value. Task 1.
2. Surrounding whitespace (`" 100 "`) — should be trimmed and accepted, not rejected. Task 1.
3. Thai or full-width digits (`๑๐๐`, `１００`) — should produce the readable non-numeric error. Task 1.
4. Overflowing input (`1e400`) — should produce the finite-number error, not `inf` arithmetic or a 500. Task 1.
5. A POST without `r_unit`, or with a corrected field after an error — should default safely and preserve the other submitted values. Task 4.

---

### Task 1: Environment, input parsing, and validation

**Files:**
- Delete: `app.py`, `dc_bias.py` (prototype, not reused)
- Create: `dc_bias.py`
- Create: `tests/__init__.py`
- Create: `tests/test_dc_bias.py`

**Interfaces:**
- Produces:
  - `PARAMETERS: tuple[str, ...] = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")`
  - `RESISTOR_PARAMETERS: tuple[str, ...] = ("r1", "r2", "rc", "re")`
  - `DEFAULTS: dict[str, str]` with `vcc="12"`, `r1="100"`, `r2="22"`, `rc="2.2"`, `re="1"`, `beta="100"`, `vbe="0.7"`, `r_unit="kohm"`
  - `class BiasInputError(ValueError)` with `.errors: dict[str, str]`
  - `def parse_inputs(raw: Mapping[str, str]) -> dict[str, float]` — returns `vcc`, `beta`, `vbe` as-is, and `r1`, `r2`, `rc`, `re` converted to ohms using `raw.get("r_unit", "ohm")`
  - `def to_ohms(value: float, unit: str = "ohm") -> float`

- [ ] **Step 1: Create the virtual environment and install Flask**

```powershell
cd "C:\Users\b6809195\Documents\GitHub\BJT DC Bias Web App"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import flask; print(flask.__version__)"
```

Expected: a Flask version starting with `3.`.

- [ ] **Step 2: Delete the prototype modules**

```powershell
Remove-Item app.py, dc_bias.py -Force
```

Expected: `Get-ChildItem` shows `requirements.txt`, `.gitignore`, and `.venv`.

- [ ] **Step 3: Write the failing validation tests**

Create `tests/__init__.py` (empty) and `tests/test_dc_bias.py`:

```python
import unittest

from dc_bias import BiasInputError, parse_inputs, to_ohms


class ParseInputsTests(unittest.TestCase):
    def test_reference_inputs_convert_kohm_to_ohms(self):
        parsed = parse_inputs({
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
            "beta": "100", "vbe": "0.7", "r_unit": "kohm",
        })
        self.assertAlmostEqual(parsed["r1"], 100_000.0)
        self.assertAlmostEqual(parsed["rc"], 2_200.0)
        self.assertAlmostEqual(parsed["vcc"], 12.0)

    def test_missing_field_reports_that_field(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs({"vcc": "12", "r1": "100", "r2": "22",
                          "rc": "2.2", "re": "1", "beta": "100"})
        self.assertIn("vbe", ctx.exception.errors)

    def test_non_numeric_reports_the_field(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs({"vcc": "12", "r1": "100", "r2": "22",
                          "rc": "2.2", "re": "1", "beta": "abc",
                          "vbe": "0.7", "r_unit": "kohm"})
        self.assertIn("beta", ctx.exception.errors)

    def test_thousands_separator_is_rejected_with_numeric_error(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs({"vcc": "12", "r1": "100,000", "r2": "22",
                          "rc": "2.2", "re": "1", "beta": "100",
                          "vbe": "0.7", "r_unit": "ohm"})
        self.assertIn("r1", ctx.exception.errors)

    def test_surrounding_whitespace_is_accepted(self):
        parsed = parse_inputs({"vcc": " 12 ", "r1": " 100 ", "r2": "22",
                               "rc": "2.2", "re": "1", "beta": "100",
                               "vbe": "0.7", "r_unit": "kohm"})
        self.assertAlmostEqual(parsed["r1"], 100_000.0)

    def test_thai_digits_are_rejected_with_numeric_error(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs({"vcc": "๑๒", "r1": "100", "r2": "22",
                          "rc": "2.2", "re": "1", "beta": "100",
                          "vbe": "0.7", "r_unit": "kohm"})
        self.assertIn("vcc", ctx.exception.errors)

    def test_overflowing_value_is_rejected_as_non_finite(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs({"vcc": "1e400", "r1": "100", "r2": "22",
                          "rc": "2.2", "re": "1", "beta": "100",
                          "vbe": "0.7", "r_unit": "kohm"})
        self.assertIn("vcc", ctx.exception.errors)


class UnitConversionTests(unittest.TestCase):
    def test_kohm_to_ohms(self):
        self.assertAlmostEqual(to_ohms(100, "kohm"), 100_000.0)

    def test_ohm_passthrough(self):
        self.assertAlmostEqual(to_ohms(100, "ohm"), 100.0)

    def test_invalid_unit_raises_with_unit_key(self):
        with self.assertRaises(BiasInputError) as ctx:
            to_ohms(100, "mohm")
        self.assertIn("r_unit", ctx.exception.errors)


class ValidationTests(unittest.TestCase):
    def _raw(self, **overrides):
        raw = dict(DEFAULTS)
        raw.update(overrides)
        return raw

    def test_resistance_must_be_positive(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs(self._raw(r1="0"))
        self.assertIn("r1", ctx.exception.errors)

    def test_beta_must_be_positive(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs(self._raw(beta="0"))
        self.assertIn("beta", ctx.exception.errors)

    def test_vcc_must_be_positive(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs(self._raw(vcc="0"))
        self.assertIn("vcc", ctx.exception.errors)

    def test_vbe_must_be_non_negative(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs(self._raw(vbe="-0.1"))
        self.assertIn("vbe", ctx.exception.errors)

    def test_vbe_must_be_less_than_vcc(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_inputs(self._raw(vbe="12"))
        self.assertIn("vbe", ctx.exception.errors)
```

Import `DEFAULTS` alongside the other names at the top of the test file.

- [ ] **Step 4: Run the tests and confirm they fail**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: import error because `dc_bias` does not exist.

- [ ] **Step 5: Implement the parsing and validation layer**

In `dc_bias.py`, define the constants, `BiasInputError`, `to_ohms`, and `parse_inputs`. Rules:

- Trim every raw string value. Empty or absent → `"กรุณากรอกค่านี้"`.
- Convert with `float(text)`. `ValueError` → `"ต้องเป็นตัวเลข เช่น 12 หรือ 2.2"`.
- Reject `math.isfinite` being false → `"ต้องเป็นจำนวนจริงที่มีค่าจำกัด"`.
- Collect **all** field errors into one `BiasInputError`; do not stop at the first.
- `to_ohms` accepts `"ohm"` (factor 1) and `"kohm"` (factor 1000); any other value raises `BiasInputError({"r_unit": "หน่วยความต้านทานไม่ถูกต้อง (เลือก Ω หรือ kΩ)"})`.
- Validation messages: `vcc` → `"VCC ต้องมากกว่า 0 V"`; each resistor → `"ความต้านทานต้องมากกว่า 0 Ω"`; `beta` → `"β ต้องมากกว่า 0"`; `vbe < 0` → `"VBE ต้องไม่ติดลบ"`; `vbe >= vcc` → `"VBE ต้องน้อยกว่า VCC"`.
- `parse_inputs` returns a dict whose resistor values are in ohms.

- [ ] **Step 6: Run the tests and confirm they pass**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dc_bias -v
```

Expected: all Task 1 tests PASS.

- [ ] **Step 7: Hand off commit (GitHub Desktop)**

Files: `dc_bias.py`, `tests/__init__.py`, `tests/test_dc_bias.py`, deleted `app.py`/`dc_bias.py` prototype.
Suggested summary: `feat: add BJT input parsing and validation`
Owner: review **Changes** → **Commit to lab02-dc-bias**. Agent must not commit.

---

### Task 2: Forward-active solver and result model

**Files:**
- Modify: `dc_bias.py`
- Modify: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `BiasInputError`, `parse_inputs` from Task 1.
- Produces:
  - `@dataclass(frozen=True) class BiasResult` with fields, in order: `vcc, r1, r2, rc, re, beta, vbe, vth, rth, ib, ic, ie, vb, ve, vc, vce: float`, then `region: str`, `warnings: tuple[str, ...]`, `assumptions: tuple[str, ...]`
  - Properties on `BiasResult`: `ic_ma -> float`, `ib_ua -> float`, `ie_ma -> float`, `power_q_mw -> float`, `region_label -> str`
  - `def solve_voltage_divider_bias(vcc: float, r1: float, r2: float, rc: float, re: float, beta: float, vbe: float) -> BiasResult`
  - `assumptions` is the fixed tuple: `("β คงที่ตลอดช่วงการทำงาน", "VBE คงที่ตามค่าที่กรอก", "ไม่คิด Early effect และกระแสรั่ว", "อุณหภูมิคงที่ 25 °C")`

- [ ] **Step 1: Write the failing reference-case and identity tests**

Append to `tests/test_dc_bias.py`:

```python
class ReferenceCaseTests(unittest.TestCase):
    def setUp(self):
        self.result = solve_voltage_divider_bias(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=0.70,
        )

    def test_intermediate_values_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.vth, 2.163934, places=5)
        self.assertAlmostEqual(self.result.rth, 18_032.787, places=3)

    def test_currents_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.ib, 12.298581e-6, places=11)
        self.assertAlmostEqual(self.result.ic, 1.229858e-3, places=8)
        self.assertAlmostEqual(self.result.ie, 1.242157e-3, places=8)
        self.assertAlmostEqual(self.result.ic_ma, 1.229858, places=6)
        self.assertAlmostEqual(self.result.ib_ua, 12.298581, places=5)

    def test_voltages_match_hand_calculation(self):
        self.assertAlmostEqual(self.result.ve, 1.242157, places=5)
        self.assertAlmostEqual(self.result.vb, 1.942157, places=5)
        self.assertAlmostEqual(self.result.vc, 9.294312, places=5)
        self.assertAlmostEqual(self.result.vce, 8.052155, places=5)

    def test_identities_hold_in_forward_active(self):
        r = self.result
        self.assertAlmostEqual(r.ie, r.ic + r.ib, places=12)
        self.assertAlmostEqual(r.vb, r.ve + self.result.vbe, places=9)
        self.assertAlmostEqual(r.vc, r.vcc - r.ic * r.rc, places=9)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=9)

    def test_region_is_active(self):
        self.assertEqual(self.result.region, "active")
        self.assertEqual(self.result.region_label, "Forward-Active")
```

Import `solve_voltage_divider_bias` at the top.

- [ ] **Step 2: Run the tests and confirm they fail**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dc_bias -v
```

Expected: FAIL with `ImportError: cannot import name 'solve_voltage_divider_bias'`.

- [ ] **Step 3: Implement `BiasResult` and the forward-active solver**

In `dc_bias.py`, add the dataclass and solver. Compute exactly:

```text
VTH = VCC × R2 / (R1 + R2)
RTH = R1 × R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1) × RE)
IC  = β × IB
IE  = (β + 1) × IB
VE  = IE × RE
VB  = VE + VBE
VC  = VCC − IC × RC
VCE = VC − VE
```

For this task, set `region="active"` and `warnings=()` unconditionally. `power_q_mw = vce * ic * 1000.0`. Keep the resolver free of Flask imports.

- [ ] **Step 4: Run the tests and confirm they pass**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dc_bias -v
```

Expected: all Task 2 tests PASS.

- [ ] **Step 5: Hand off commit (GitHub Desktop)**

Files: `dc_bias.py`, `tests/test_dc_bias.py`.
Suggested summary: `feat: add forward-active DC bias solver`
Owner commits in GitHub Desktop.

---

### Task 3: Region detection and warnings

**Files:**
- Modify: `dc_bias.py`
- Modify: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `BiasResult`, `solve_voltage_divider_bias` from Task 2.
- Produces: the same solver, now returning `region` as `"active"`, `"cutoff"`, or `"saturation"`, and `warnings` with Thai messages.
- Produces constants: `VCE_SATURATION_THRESHOLD = 0.30`, `VBE_TYPICAL_RANGE = (0.50, 0.90)`.

- [ ] **Step 1: Write the failing region tests**

Append:

```python
class RegionTests(unittest.TestCase):
    def test_cutoff_contract(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=2.5,
        )
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, r.vth)

    def test_cutoff_does_not_assert_base_emitter_identity(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=2.5,
        )
        self.assertNotAlmostEqual(r.vb, r.ve + r.vbe, places=6)
        self.assertAlmostEqual(r.vc, r.vcc)
        self.assertAlmostEqual(r.vce, r.vcc)

    def test_cutoff_has_warning(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=2.5,
        )
        self.assertTrue(any("Cutoff" in w for w in r.warnings))

    def test_saturation_when_vce_at_or_below_threshold(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=10_000.0, r2=10_000.0, rc=10_000.0,
            re=1_000.0, beta=100.0, vbe=0.7,
        )
        self.assertEqual(r.region, "saturation")
        self.assertLessEqual(r.vce, 0.30)
        self.assertTrue(any("Saturation" in w for w in r.warnings))

    def test_vbe_outside_typical_range_warns_but_solves(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=0.3,
        )
        self.assertEqual(r.region, "active")
        self.assertTrue(any("VBE" in w for w in r.warnings))

    def test_assumptions_are_reported(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=0.7,
        )
        self.assertGreaterEqual(len(r.assumptions), 3)
```

- [ ] **Step 2: Run the tests and confirm they fail**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dc_bias -v
```

Expected: the cutoff and saturation tests FAIL because `region` is always `"active"`.

- [ ] **Step 3: Implement region logic**

In `solve_voltage_divider_bias`, after computing `vth` and `rth`:

- If `vth <= vbe`: return a `BiasResult` with `region="cutoff"`, `ib=ic=ie=0.0`, `ve=0.0`, `vb=vth`, `vc=vcc`, `vce=vcc`, and warning `"Cutoff: VTH ≤ VBE ทำให้ทรานซิสเตอร์ไม่นำกระแส; แบบจำลอง Forward-Active ใช้ไม่ได้"`.
- Otherwise compute the forward-active values from Task 2.
- If `vce <= VCE_SATURATION_THRESHOLD`: `region="saturation"` and warning `"Saturation: VCE ≤ 0.30 V; ค่า IC จากแบบจำลอง Forward-Active อาจสูงเกินจริง"`. Keep the computed values for inspection.
- Else: `region="active"`.
- If `not (VBE_TYPICAL_RANGE[0] <= vbe <= VBE_TYPICAL_RANGE[1])`: append `"VBE อยู่นอกช่วงปกติ 0.50–0.90 V; ตรวจสอบสมมติฐานอีกครั้ง"`.
- Build `warnings` as a tuple, region warning first, then the VBE warning.

- [ ] **Step 4: Run the tests and confirm they pass**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dc_bias -v
```

Expected: all Task 3 tests PASS.

- [ ] **Step 5: Hand off commit (GitHub Desktop)**

Files: `dc_bias.py`, `tests/test_dc_bias.py`.
Suggested summary: `feat: detect cutoff and saturation regions`
Owner commits in GitHub Desktop.

---

### Task 4: Flask routes, template, and stylesheet

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: `BiasInputError`, `DEFAULTS`, `parse_inputs`, `solve_voltage_divider_bias`, `BiasResult` from Tasks 1–3.
- Produces:
  - `def create_app(test_config: dict | None = None) -> Flask`
  - `app = create_app()`
  - Route `GET /` → 200, renders `index.html` with `form=DEFAULTS`, no result.
  - Routes `POST /calculate` and `POST /` → valid: 200 with `result`; invalid: 400 with `errors` and the submitted `form`.
  - Template filter `num3` (thousands separator, 3 decimals) and `num0` (thousands separator, 0 decimals).

- [ ] **Step 1: Write the failing HTTP tests**

Create `tests/test_web.py`:

```python
import unittest

from app import create_app

REFERENCE_FORM = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.7", "r_unit": "kohm",
}


class WebTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_get_index_renders_all_fields(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', response.get_data(as_text=True))

    def test_post_calculate_renders_reference_values(self):
        response = self.client.post("/calculate", data=REFERENCE_FORM)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        for expected in ("1.942", "9.294", "8.052", "1.230", "Forward-Active"):
            self.assertIn(expected, body)

    def test_post_root_alias_works(self):
        response = self.client.post("/", data=REFERENCE_FORM)
        self.assertEqual(response.status_code, 200)
        self.assertIn("1.230", response.get_data(as_text=True))

    def test_zero_resistance_returns_400_and_keeps_form(self):
        data = dict(REFERENCE_FORM, r1="0")
        response = self.client.post("/calculate", data=data)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn("ความต้านทานต้องมากกว่า 0", body)
        self.assertIn('value="22"', body)

    def test_non_numeric_beta_returns_400(self):
        data = dict(REFERENCE_FORM, beta="abc")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("ต้องเป็นตัวเลข", response.get_data(as_text=True))

    def test_cutoff_post_shows_warning(self):
        data = dict(REFERENCE_FORM, vbe="2.5")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cutoff", response.get_data(as_text=True))

    def test_invalid_unit_returns_400(self):
        data = dict(REFERENCE_FORM, r_unit="mohm")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("หน่วยความต้านทานไม่ถูกต้อง", response.get_data(as_text=True))

    def test_missing_unit_defaults_to_ohm(self):
        data = {k: v for k, v in REFERENCE_FORM.items() if k != "r_unit"}
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("9.294", response.get_data(as_text=True))
```

- [ ] **Step 2: Run the tests and confirm they fail**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_web -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Implement `app.py`**

Create `create_app` and `app`. Logic:

- `GET /` renders `index.html` with `form=DEFAULTS`, `result=None`, `errors={}`.
- `POST /calculate` and `POST /` read `request.form`, call `parse_inputs`, then `solve_voltage_divider_bias(**parsed)`, render with `form=request.form`, `result=result`.
- On `BiasInputError`: render the same template with `form=request.form`, `result=None`, `errors=exc.errors`, status 400.
- Register `num3` and `num0` template filters using f-strings with `,` thousands separator.
- Do not catch arbitrary exceptions; let real bugs surface during development.

- [ ] **Step 4: Create `templates/index.html`**

One responsive page, Thai labels, no JavaScript, all displayed values with units:

1. Header: course/lab identifier and scope statement.
2. Form with `method="post" action="/calculate"`, seven numeric inputs plus a `select name="r_unit"` offering `Ω`/`kΩ`, inline errors next to each field, and a submit button.
3. Result card rendered only when `result` exists: region badge using `result.region_label`, summary tiles for `VB`, `VE`, `VC`, `VCE`, `IC` (use `num3` and the correct unit), detail table including `VTH`, `RTH`, `IB`, `IE`, and `power_q_mw`, warnings list, assumptions list.
4. Equations card: the eight model equations and the region thresholds.
5. Footer with lab/version note.

Echo submitted values with `value="{{ form.get('r1', '') }}"`. Preserve the selected unit.

- [ ] **Step 5: Create `static/style.css`**

Responsive navy/teal academic styling. Layout must remain readable at 360 px width. No CSS that changes values or hides warnings.

- [ ] **Step 6: Run the web tests and confirm they pass**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_web -v
```

Expected: all Task 4 tests PASS.

- [ ] **Step 7: Run the full suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all engineering and web tests PASS.

- [ ] **Step 8: Hand off commit (GitHub Desktop)**

Files: `app.py`, `templates/index.html`, `static/style.css`, `tests/test_web.py`.
Suggested summary: `feat: add Flask form and DC bias results page`
Owner commits in GitHub Desktop.

---

### Task 5: Documentation and reflection

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/design-note.md`
- Create: `docs/validation.md`
- Create: `docs/reflection.md`

**Interfaces:**
- Consumes: the finished app, test suite, and reference values from Tasks 1–4.
- Produces: documentation only; no runtime code.

- [ ] **Step 1: Write `README.md`**

Include: project purpose, scope/non-goals, file layout, Python/Flask requirements, setup commands (`py -m venv .venv`, `pip install -r requirements.txt`), run command (`.\.venv\Scripts\python.exe -m flask --app app run --debug`), open `http://127.0.0.1:5000/`, test command, reference case table, model equations, region rules, assumptions, and limitations. State that `python` may be `py` on Windows.

- [ ] **Step 2: Write `AGENTS.md`**

Record the architecture boundary (`dc_bias.py` must not import Flask/HTML), TDD requirement, test command, no-JavaScript rule, and the GitHub Desktop commit protocol.

- [ ] **Step 3: Write `docs/validation.md`**

Show the independent hand calculation for the reference case with every intermediate value, then a table mapping each value to the test that asserts it. State that the expected values were derived independently of the app.

- [ ] **Step 4: Write `docs/design-note.md`**

Summarize the approved design: chosen architecture, why server-rendered Flask, rejected alternatives, interfaces, and the region contract.

- [ ] **Step 5: Write `docs/reflection.md`**

Answer the four handout questions in Thai, citing this project's files:

1. เหตุใดการเปิด `templates/index.html` ตรง ๆ จึงไม่เท่ากับการรัน Flask?
2. ฟอร์มส่งข้อมูลไป Python อย่างไร?
3. แก้สมการใน `dc_bias.py` แล้วต้องแก้ HTML หรือไม่?
4. ทำไมผลใน Region ที่แบบจำลองใช้ไม่ได้จึงต้องมี Warning?

- [ ] **Step 6: Verify the README commands actually work**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests PASS, confirming the documented test command is correct.

- [ ] **Step 7: Hand off commit (GitHub Desktop)**

Files: `README.md`, `AGENTS.md`, `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md`.
Suggested summary: `docs: add README, validation report and reflection`
Owner commits in GitHub Desktop.

---

### Task 6: Final verification and browser acceptance

**Files:**
- Modify: any file only if verification exposes a real defect (fix test-first).
- Test: full suite.

- [ ] **Step 1: Run the complete suite fresh**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: every test PASS, zero failures, zero errors. Copy the final counts into the handoff report.

- [ ] **Step 2: Start the server**

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Expected: the server reports it is running on `http://127.0.0.1:5000/`.

- [ ] **Step 3: Perform the A1–A5 browser checks**

- Open `http://127.0.0.1:5000/`; confirm HTTP 200 and all seven fields.
- Submit the reference case; confirm `VB=1.942 V`, `VE=1.242 V`, `VC=9.294 V`, `VCE=8.052 V`, `IC=1.230 mA`, region `Forward-Active`.
- Submit `R1=0`; confirm HTTP 400, a readable Thai error, and the other values preserved.
- Submit `VBE=2.5`; confirm the Cutoff warning.
- Submit a saturation case; confirm the Saturation warning.
- Confirm every displayed value has a unit.

- [ ] **Step 4: Record evidence**

Collect the test summary, the reference-case screenshot, and the invalid-input screenshot for the submission. Do not claim completion without this evidence.

- [ ] **Step 5: Finish the branch**

Use `superpowers:finishing-a-development-branch` to present integration options. The owner performs the final GitHub Desktop commit/push.

---

## Self-Review Notes

- Spec coverage: A1/A2 → Task 4; A3 → Tasks 2 and 5; A4 → Tasks 1 and 4; A5 → Tasks 3 and 4; A6 → Tasks 1–4; A7 → Tasks 5–6; reflection → Task 5.
- The cutoff identity exception from the design is pinned by `test_cutoff_does_not_assert_base_emitter_identity`.
- All five Review Focus inputs have a named test.
- Commit steps are handoffs, never agent-run `git commit`/`git push`.
