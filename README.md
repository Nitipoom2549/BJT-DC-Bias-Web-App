# BJT Voltage-Divider DC Bias Web App

Lab 02 · ENG29 2121 · 2/2569

A small Flask + Python application that calculates the DC operating point of an
NPN Common-Emitter amplifier using **Voltage-Divider Bias**. The browser form
sends values to a Python backend; the backend validates them, solves the
forward-active model, and renders the result with units and region warnings.

## Scope

Included:

- NPN voltage-divider bias, DC only.
- Inputs: `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE`.
- Outputs: `VB`, `VE`, `VC`, `VCE`, `IC`, plus `VTH`, `RTH`, `IB`, `IE`.
- Input validation with readable Thai errors.
- Cutoff and saturation warnings.
- Unit handling: resistances in Ω or kΩ.

Not included: AC/small-signal analysis, gain, Bode plots, transient analysis,
SPICE, other bias types, FETs, or an interactive schematic editor.

## Project structure

```text
.
├── app.py                 # Flask app factory, routes, template filters
├── dc_bias.py             # pure engineering: parsing, validation, solver
├── templates/index.html   # server-rendered page
├── static/style.css       # responsive presentation
├── tests/
│   ├── test_dc_bias.py    # engineering and validation tests
│   └── test_web.py        # Flask test-client tests
├── docs/
│   ├── design-note.md     # architecture and decisions
│   ├── validation.md      # independent hand calculation + test map
│   ├── reflection.md      # answers to the handout questions
│   └── superpowers/       # design spec and implementation plan
├── requirements.txt
└── .gitignore
```

`dc_bias.py` must stay free of Flask, HTML, and HTTP imports. `app.py` owns
transport and rendering only.

## Requirements

- Python 3.11 or newer (developed with Python 3.14.2).
- Flask 3.x.
- No JavaScript, database, or external service.

On Windows the Python launcher is often `py` rather than `python`. Substitute
accordingly.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

Windows:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Linux/macOS:

```bash
python -m flask --app app run --debug
```

Open <http://127.0.0.1:5000/>. The server binds to localhost only.

## Test

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS:

```bash
python -m unittest discover -s tests -v
```

Expected: 34 tests pass, 0 failures, 0 errors.

## Reference case

`VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`,
`β = 100`, `VBE = 0.70 V`.

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

These values are derived independently by hand in
[`docs/validation.md`](docs/validation.md) and asserted by the tests.

## Model

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

### Region rules

| Condition | Region | Behaviour |
|---|---|---|
| `VTH ≤ VBE` | Cutoff | Currents set to zero, `VE = 0`, `VB = VTH`, `VC = VCE = VCC`, warning shown |
| `VCE ≤ 0.30 V` | Saturation | Forward-active values kept for inspection, warning shown |
| otherwise | Forward-Active | Values shown normally |

`VBE` outside `0.50–0.90 V` adds a warning but does not stop the calculation.
The `0.30 V` threshold flags model invalidity; it is not a SPICE model.

## Validation rules

| Input | Rule |
|---|---|
| all | required, ASCII decimal/scientific notation only |
| `VCC` | `> 0` |
| `R1`, `R2`, `RC`, `RE` | `> 0` |
| `β` | `> 0` |
| `VBE` | `0 ≤ VBE < VCC` |
| unit | `Ω` or `kΩ` |

Invalid submissions return HTTP 400 and re-render the form with Thai field
errors; valid submissions return HTTP 200.

## Assumptions and limitations

- Constant `β` and constant `VBE`.
- No Early effect, leakage current, temperature drift, or component tolerance.
- Forward-active equations are not valid in cutoff or saturation; the app warns
  instead of pretending otherwise.
- Local development server only.

## Commit protocol

Commits are made with GitHub Desktop (or, when the GUI is unavailable, the Git
binary bundled with it) on branch `lab02-dc-bias`. The agent reports changed
files and test evidence; the owner reviews the diff and pushes.
