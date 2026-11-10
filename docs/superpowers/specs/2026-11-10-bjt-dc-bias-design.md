# BJT DC Bias Web App — Design Document

**Lab:** ENG29 2121 · Lab 02 · 2/2569
**Date:** 2026-11-10
**Status:** Draft for approval
**Author:** OpenCode + Superpowers (for the student owner)

---

## 1. Intent and Why

Build the smallest real, multi-file Flask web application that calculates the DC
operating point of an NPN BJT Common-Emitter amplifier using **Voltage-Divider
Bias**. The lab is a first end-to-end web-app experience: browser form → HTTP
request → Python backend → engineering calculation → HTML response → automated
tests → GitHub.

Success is not a beautiful mock-up. Success is a running localhost application
whose displayed values come from Python, whose invalid inputs produce readable
errors, whose out-of-region results carry explicit warnings, and whose tests can
be re-run by anyone who clones the repository.

**Why now:** This is Week 2 of a semester-long Virtual Transistor Laboratory.
Later weeks add other bias types, SPICE, AC, transient, and interactive
schematics. Week 2 must stay narrow so the whole workflow fits in one lab.

---

## 2. Users and Context

- **Primary user:** second-year Electrical Engineering student building and
  demonstrating the app.
- **Secondary user:** instructor/grader checking A1–A7 and GitHub
  reproducibility.
- **Environment:** Windows laptop, OpenCode Desktop, Python 3.14.2, Flask,
  GitHub Desktop for commits. Local development server only.

---

## 3. Goals

1. A Flask application with a clear multi-file structure:
   `app.py`, `dc_bias.py`, `templates/index.html`, `static/style.css`,
   `tests/`, `requirements.txt`, `README.md`, `docs/`.
2. Inputs: `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE`.
3. Outputs: `VB`, `VE`, `VC`, `VCE`, `IC`; additionally `IB`, `IE`, `VTH`,
   `RTH` for transparency.
4. Engineering math lives in a pure Python module with no Flask/HTML imports.
5. Friendly Thai validation errors for missing, non-numeric, and
   physically-invalid values.
6. Cutoff and saturation detection with explicit warnings that the
   forward-active approximation is not valid there.
7. Unit handling: resistances may be entered in `Ω` or `kΩ`; the backend
   converts to `Ω` before calculating.
8. Automated tests: at least 3 engineering tests and at least 1 Flask test
   client test; all pass with `python -m unittest discover -s tests -v`.
9. README with setup, run, test, model assumptions, and limitations.
10. A Git repository whose history is readable and whose `.gitignore` excludes
    `.venv/`, `__pycache__/`, `.env`, and secrets.

---

## 4. Non-Goals

- No AC small-signal analysis, gain, Bode plot, transient analysis, or signal
  generator.
- No SPICE/ngspice solver.
- No Fixed Bias, Emitter Bias, Collector Feedback, or FET support.
- No interactive schematic editor, animations, or drag-and-drop circuit builder.
- No authentication, database, REST API for third parties, or cloud deployment.
- No JavaScript framework or build pipeline.
- No attempt to model temperature, Early effect, leakage, or component
  tolerances.

---

## 5. Anti-Goals

The following would make the deliverable fail even if it “works”:

- Hardcoded answers in HTML or JavaScript.
- A single `index.html` opened with `file://` instead of a Python server.
- Calculations implemented only in JavaScript.
- Reporting `VCE` outside the forward-active region without a warning.
- A page that crashes or shows a stack trace on invalid input.
- Tests that assert only that the page loads, without checking engineering
  values.
- Committing `.venv/`, credentials, or API keys.
- A UI so elaborate that validation, tests, or README are incomplete.

---

## 6. Constraints

- **Language/runtime:** Python 3.14.2 via `py` on this machine.
- **Web framework:** Flask 3.x (single production dependency).
- **Templates:** Jinja2, server-rendered.
- **Tests:** standard library `unittest` (no pytest dependency required).
- **UI language:** Thai labels and messages, SI units and English symbols.
- **Server:** `127.0.0.1:5000`, Flask development server; never exposed publicly.
- **Commits:** GitHub Desktop only; the agent must not run `git commit` or
  `git push`.
- **Branch:** `lab02-dc-bias` unless the owner chooses `main`.
- **Timebox:** one 3-hour lab; scope must remain DC Bias only.

---

## 7. Approaches Considered

### A. Flask + Jinja server-rendered pages (chosen)

- Form posts to Flask; Flask calls `dc_bias.py`; Jinja renders results.
- One language on the server, no client-side calculation, easy to test with
  Flask's test client.
- Matches the handout's architecture diagram and learning outcomes.
- Trade-off: full-page reload on submit; acceptable for a lab.

### B. Flask JSON API + vanilla JavaScript front-end

- Browser sends `fetch()` to `/api/calculate`; JavaScript renders results.
- More “modern” separation, but adds a second calculation/rendering path,
  client-side state, and harder end-to-end tests.
- Trade-off: more moving parts and more ways to accidentally hardcode or
  duplicate physics. Rejected for Week 2.

### C. Static HTML + JavaScript only

- No Python backend, no HTTP route, no server-side validation.
- Directly violates the lab requirement that Python performs the calculation.
- Rejected.

### D. Flask + HTMX/Alpine.js

- Nicer partial updates with little JavaScript.
- Adds a dependency and a concept not needed to prove the learning outcomes.
- Rejected as scope creep.

**Decision:** A. Flask + Jinja server-rendered, with a pure Python engineering
module. This is the smallest design that satisfies every acceptance criterion.

---

## 8. Architecture

```
BJT DC Bias Web App/
├── app.py                  # Flask app factory, routes, form handling
├── dc_bias.py              # pure engineering calculations + validation
├── templates/
│   └── index.html          # input form, results, errors, warnings, equations
├── static/
│   └── style.css           # responsive presentation only
├── tests/
│   ├── test_dc_bias.py     # engineering math, validation, regions
│   └── test_web.py         # Flask test client: GET/POST/errors
├── requirements.txt        # Flask
├── README.md               # setup, run, test, model, limitations
├── AGENTS.md               # conventions for AI coding agents
├── .gitignore
└── docs/
    ├── design-note.md      # student-facing design summary
    ├── validation.md       # independent calculation + test evidence
    ├── reflection.md       # answers to the lab reflection questions
    └── superpowers/
        ├── specs/2026-11-10-bjt-dc-bias-design.md
        └── plans/2026-11-10-bjt-dc-bias.md
```

### Responsibilities

| File | Responsibility | Must not do |
|---|---|---|
| `app.py` | HTTP routes, parse form, call engineering module, render template | Contain physics equations |
| `dc_bias.py` | Validate physical values, solve operating point, region logic | Import Flask, HTML, or HTTP |
| `templates/index.html` | Display form/results/errors; show equations as documentation | Compute physics or hardcode answers |
| `static/style.css` | Layout, responsive design, print styles | Affect calculations |
| `tests/test_dc_bias.py` | Prove engineering behavior and boundaries | Depend on Flask |
| `tests/test_web.py` | Prove HTTP status, form rendering, backend values, errors | Re-implement physics |

### Data flow

```
Browser form (POST /calculate)
  → Flask route in app.py
  → parse_inputs(raw)                  # missing / non-numeric
  → to_ohms(value, unit)               # kΩ → Ω
  → solve_voltage_divider_bias(...)    # validation, math, region
  → BiasResult
  → render_template("index.html", result=...)
  → HTML response with values, warnings, units
```

On invalid input, the route renders the same template with a
`BiasInputError.errors` dictionary and HTTP 400; the form keeps the submitted
values so the user can correct one field.

### 8.1 Prototype disposition (decision)

Before Superpowers was installed, the workspace received a throwaway prototype
(`app.py`, `dc_bias.py`, `requirements.txt`, `.gitignore`). Only
`requirements.txt` and `.gitignore` are kept as-is. `app.py` and `dc_bias.py`
are **deleted and rebuilt test-first**; they are not a baseline to characterize
and must not be read as a shortcut around RED→GREEN. Historical recovery is
available through the file system if ever needed, but the plan treats the
engineering and route modules as new work.

---

## 9. Engineering Model

### 9.1 Circuit

NPN Common Emitter, Voltage-Divider Bias:

- `R1` from `VCC` to base
- `R2` from base to ground
- `RC` from `VCC` to collector
- `RE` from emitter to ground
- `VCC` supply, `β` constant, `VBE` constant

### 9.2 Forward-active equations

```
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

### 9.3 Region rules

| Condition | Region | Values | Warning |
|---|---|---|---|
| `VTH ≤ VBE` | Cutoff | `IB=IC=IE=0`, `VE=0`, `VB=VTH`, `VC=VCC`, `VCE=VCC` | “Cutoff: forward-active model not applicable” |
| `VCE ≤ 0.30 V` | Saturation | Use forward-active equations, but flag values as invalid | “Saturation: model not applicable; IC is overestimated” |
| otherwise | Active | Equations above | None, unless `VBE` is outside 0.5–0.9 V |

`VBE` outside `0.50–0.90 V` produces an additional warning but does not stop
the calculation. `VCE = 0.30 V` is a model-flagging threshold, not a SPICE
model or a claim about a real transistor.

**Identity scope:** The KVL identity `VB = VE + VBE` holds only in the
active and saturation branches, where the base-emitter junction is modelled
as a fixed `VBE`. In cutoff the branch is a deliberate discontinuity
(`IB = IC = IE = 0`, `VE = 0`, `VB = VTH`), so `VB = VE + VBE` is not
expected to hold and must not be asserted there. `IE = IC + IB`,
`VC = VCC − IC·RC`, and `VCE = VC − VE` hold in all three branches.

### 9.4 Reference case (hand-derived)

`VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V`

| Quantity | Value |
|---|---|
| VTH | 2.163934 V |
| RTH | 18.032787 kΩ |
| IB | 12.298581 µA |
| IC | 1.229858 mA |
| IE | 1.242157 mA |
| VE | 1.242157 V |
| VB | 1.942157 V |
| VC | 9.294312 V |
| VCE | 8.052155 V |

These values are computed independently by hand/algebra, not by the app, and
are used in tests.

---

## 10. Interfaces (exact)

```python
# dc_bias.py
PARAMETERS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_PARAMETERS = ("r1", "r2", "rc", "re")
VCE_SATURATION_THRESHOLD = 0.30
VBE_TYPICAL_RANGE = (0.50, 0.90)
DEFAULTS: dict[str, str]

class BiasInputError(ValueError):
    errors: dict[str, str]

@dataclass(frozen=True)
class BiasResult:
    vcc: float; r1: float; r2: float; rc: float; re: float
    beta: float; vbe: float
    vth: float; rth: float
    ib: float; ic: float; ie: float
    vb: float; ve: float; vc: float; vce: float
    region: str                      # "active" | "cutoff" | "saturation"
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    # properties: ic_ma, ib_ua, ie_ma, power_q_mw, region_label

def parse_inputs(raw: Mapping[str, str]) -> dict[str, float]
def to_ohms(value: float, unit: str = "ohm") -> float
def solve_voltage_divider_bias(
    vcc: float, r1: float, r2: float, rc: float, re: float,
    beta: float, vbe: float,
) -> BiasResult
```

```python
# app.py
def create_app(test_config: dict | None = None) -> Flask
app: Flask
```

Routes:

- `GET /` → form with defaults, HTTP 200.
- `POST /calculate` and `POST /` → calculate or render errors.
- Valid POST → HTTP 200 with results.
- Invalid POST → HTTP 400 with field errors and preserved form values.

Template filters: `num3` (thousands separator, 3 decimals), `num0` (0 decimals).

---

## 11. Validation Rules

| Field | Rule | Error message (Thai) |
|---|---|---|
| all | missing/blank | `กรุณากรอกค่านี้` |
| all | non-numeric | `ต้องเป็นตัวเลข เช่น 12 หรือ 2.2` |
| all | non-finite | `ต้องเป็นจำนวนจริงที่มีค่าจำกัด` |
| `VCC` | `> 0` | `VCC ต้องมากกว่า 0 V` |
| `R1,R2,RC,RE` | `> 0` | `ความต้านทานต้องมากกว่า 0 Ω` |
| `β` | `> 0` | `β ต้องมากกว่า 0` |
| `VBE` | `0 ≤ VBE < VCC` | `VBE ต้องไม่ติดลบ` / `VBE ต้องน้อยกว่า VCC` |
| `r_unit` | `ohm` or `kohm` | `หน่วยความต้านทานไม่ถูกต้อง (เลือก Ω หรือ kΩ)` |

The server never returns a 500 for user input. Unexpected internal errors are
allowed to surface during development rather than being swallowed.

---

## 12. User Interface

One page, responsive:

1. **Header:** course/lab identifier, title, scope statement.
2. **Input card:** seven fields + resistance-unit selector; inline errors;
   `Calculate DC Bias` button; reset link.
3. **Schematic card:** inline SVG of the voltage-divider circuit with labeled
   nodes and components.
4. **Result card (after valid POST):**
   - Region badge: Active / Cutoff / Saturation.
   - Summary tiles: `VB`, `VE`, `VC`, `VCE`, `IC`.
   - Detail table: `VTH`, `RTH`, `IB`, `IE`, `VE`, `VB`, `VC`, `VCE`, `IC`,
     transistor dissipation.
   - Warnings list, if any.
   - Assumptions list.
5. **Equations card:** the model equations, unit note, and region thresholds.
6. **Footer:** lab/version note.

The design is a functional engineering tool, not a pixel copy of the handout
mock-up. Colors and spacing follow a navy/teal academic style; all labels are
Thai with standard electrical symbols.

---

## 13. Testing Strategy

### Engineering (`tests/test_dc_bias.py`)

1. Reference case matches all hand-derived values (VTH, RTH, IB, IC, IE, VE,
   VB, VC, VCE).
2. KCL/KVL identities in active/saturation: `IE = IC + IB`, `VB = VE + VBE`,
   `VC = VCC − IC·RC`, `VCE = VC − VE`. In cutoff assert the cutoff contract
   instead (`IB = IC = IE = 0`, `VE = 0`, `VB = VTH`, `VC = VCC`,
   `VCE = VCC`), because `VB = VE + VBE` is intentionally not satisfied.
3. Unit conversion: `100 kΩ → 100000 Ω`; invalid unit raises.
4. Invalid inputs: `R ≤ 0`, `β ≤ 0`, `VCC ≤ 0`, `VBE ≥ VCC` each raise
   `BiasInputError` with the right key.
5. Missing/non-numeric form values raise with one error per field.
6. Cutoff case (`VTH ≤ VBE`): region `cutoff`, zero currents, `VE=0`,
   `VC=VCC`, warning present.
7. Saturation case: region `saturation`, warning present, values still
   returned for inspection.
8. `VBE` outside 0.5–0.9 V adds a warning but still solves.

### Web (`tests/test_web.py`)

1. `GET /` → 200, HTML contains the form and all seven field names.
2. `POST /calculate` with reference values in kΩ → 200, page contains
   `1.942`, `9.294`, `8.052`, `1.230`, and `Active`.
3. `POST /` also works (acceptance allows either route).
4. `POST` with `R1=0` → 400, contains the resistance error, still renders the
   form.
5. `POST` with `β=abc` → 400, contains the numeric error.
6. Cutoff POST → 200, contains `Cutoff` warning.
7. Invalid unit → 400, contains the unit error.

### 13.1 Reflection questions (transcribed from the handout)

`docs/reflection.md` must answer the handout's individual questions in Thai,
with references to this project's own files and behaviour:

1. เหตุใดการเปิด `templates/index.html` ตรง ๆ จึงไม่เท่ากับการรัน Flask?
2. ฟอร์มส่งข้อมูลไป Python อย่างไร?
3. แก้สมการใน `dc_bias.py` แล้วต้องแก้ HTML หรือไม่?
4. ทำไมผลใน Region ที่แบบจำลองใช้ไม่ได้จึงต้องมี Warning?

The agent drafts the answers; the student reviews and owns the submitted text.

### Manual/browser checks

- Start `python -m flask --app app run --debug`, open
  `http://127.0.0.1:5000/`, submit the reference case, verify values.
- Submit an invalid value, verify inline error and preserved form.
- Submit a cutoff case, verify warning and region badge.
- Take screenshots for the submission.

---

## 14. Acceptance Mapping

| Criterion | Where satisfied |
|---|---|
| A1 GET / | `app.index`, `templates/index.html` |
| A2 POST calculate | `app.calculate`, `dc_bias.solve_...` |
| A3 Engineering reference | `tests/test_dc_bias.py` reference case, `docs/validation.md` |
| A4 Validation | `dc_bias.parse_inputs` + validation in `solve_...`; inline errors |
| A5 Region warnings | `BiasResult.region` + `warnings`; result card |
| A6 Tests | `tests/test_dc_bias.py` (≥3) + `tests/test_web.py` (≥1) |
| A7 GitHub reproducibility | `README.md`, `requirements.txt`, `.gitignore`, clean history |

---

## 15. Security, Privacy, and Data

- No accounts, personal data, database, or external API calls.
- The app binds to `127.0.0.1` only.
- No secrets or API keys are needed; `.env` and credentials are git-ignored.
- User inputs are validated and never executed, evaluated, or written to disk.
- Jinja autoescaping prevents HTML injection in echoed form values.

---

## 16. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Python 3.14 / Flask compatibility | Use current Flask 3.x; install in a venv; verify import before coding |
| No `python` alias on Windows | Document `py` and `python`; use `py` in this environment |
| Missing Git CLI | GitHub Desktop bundles Git; commits via GUI |
| Scope creep (AC, SPICE, other bias types) | Explicit non-goals; reject additions during execution |
| Floating-point presentation confusion | Display fixed decimals; tests use `assertAlmostEqual` |
| False confidence outside active region | Region badge + warning; validation report states limitations |
| TDD skipped under time pressure | Plan enforces RED→GREEN per task; verification before claims |

---

## 17. Decisions Left to the Builder

These do not change the product contract; the implementer may choose:

- Exact CSS palette, spacing, and typography within the stated academic style.
- Whether the schematic is inline SVG or a styled HTML/CSS diagram.
- Additional display-only values (e.g., power dissipation) if they do not
  change the calculation contract.
- Exact Thai wording of helper text, as long as validation/region meanings are
  preserved.

---

## 18. Commit Protocol (GitHub Desktop)

- Work on branch `lab02-dc-bias` (or `main` if the owner explicitly chooses).
- The agent prepares code and tests, runs the suite, and reports evidence.
- The owner reviews the diff in GitHub Desktop and commits with the suggested
  message.
- The agent never runs `git commit` or `git push`.
- Suggested milestones:
  1. `chore: scaffold Flask project and tooling`
  2. `feat: add BJT voltage-divider DC bias calculations`
  3. `feat: validate inputs and warn outside forward-active`
  4. `feat: add Flask form and DC bias results page`
  5. `test: cover engineering math and HTTP routes`
  6. `docs: add README, design note and validation report`

---

## 19. Definition of Done

- [ ] `GET /` returns 200 and shows the form.
- [ ] Valid POST returns 200 and shows all required values with units.
- [ ] Reference values match the independent calculation.
- [ ] Invalid inputs return 400 with readable errors and preserved form.
- [ ] Cutoff/saturation return warnings and do not claim model validity.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] README reproduces setup, run, and tests.
- [ ] Design note, validation report, and reflection exist.
- [ ] GitHub repository has a readable commit history and no secrets.
- [ ] A1–A7 demonstrated in the browser and test log.
