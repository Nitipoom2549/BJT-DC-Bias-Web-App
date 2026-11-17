# AGENTS.md — conventions for AI coding agents

This project is a teaching lab. Correctness and clarity outrank cleverness.

## Architecture boundary

- `dc_bias.py` is the engineering core. It must not import Flask, Jinja, HTML,
  or HTTP libraries.
- `app.py` owns routes, form reading, and rendering. It must not contain
  engineering equations.
- `templates/index.html` displays values and documentation. It must not compute
  physics or hard-code answers.
- `static/style.css` affects presentation only.

## Test-driven development

- No production code without a failing test first.
- Run the suite before claiming a task is complete:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

- Engineering behavior belongs in `tests/test_dc_bias.py`.
- HTTP behavior belongs in `tests/test_web.py`.

## UI rules

- Thai labels and error messages; standard electrical symbols and units.
- Every displayed value carries a unit.
- No JavaScript framework, build pipeline, or client-side calculation.
- Server-rendered HTML only.

## Scope

DC Bias only. Do not add AC, transient, SPICE, other bias types, FET support, or
an interactive schematic editor. If a request implies one of these, confirm the
scope change before writing code.

## Commit protocol

- Work on `lab02-dc-bias`.
- The owner reviews diffs in GitHub Desktop.
- Never commit `.venv/`, `__pycache__/`, `.env`, keys, or credentials.
- Do not run `git push`; the owner pushes.
