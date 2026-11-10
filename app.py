"""Flask entry point for the BJT DC Bias web application.

Routes intentionally contain no physics.  They parse the HTTP request, call
the engineering module ``dc_bias.py`` and render a Jinja template.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    BiasInputError,
    DEFAULTS,
    PARAMETERS,
    RESISTOR_PARAMETERS,
    parse_inputs,
    solve_voltage_divider_bias,
    to_ohms,
)


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory used by both ``flask run`` and the tests."""
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    @app.template_filter("num3")
    def num3(value: float) -> str:
        return f"{float(value):,.3f}"

    @app.template_filter("num0")
    def num0(value: float) -> str:
        return f"{float(value):,.0f}"

    def render_calculator(
        form_values: dict[str, str],
        unit: str,
        result=None,
        errors: dict[str, str] | None = None,
        status: int = 200,
    ):
        unit_factor = 1_000.0 if unit == "kohm" else 1.0
        unit_label = "kΩ" if unit == "kohm" else "Ω"
        return (
            render_template(
                "index.html",
                form=form_values,
                result=result,
                errors=errors or {},
                r_unit_factor=unit_factor,
                r_unit_label=unit_label,
            ),
            status,
        )

    @app.get("/")
    def index():
        return render_calculator(dict(DEFAULTS), DEFAULTS["r_unit"])

    @app.post("/")
    @app.post("/calculate")
    def calculate():
        raw = request.form
        unit = raw.get("r_unit", "ohm")
        form_values = {name: raw.get(name, "") for name in PARAMETERS}
        form_values["r_unit"] = unit

        try:
            parsed = parse_inputs(raw)
            converted = {
                name: (
                    to_ohms(parsed[name], unit)
                    if name in RESISTOR_PARAMETERS
                    else parsed[name]
                )
                for name in PARAMETERS
            }
            result = solve_voltage_divider_bias(**converted)
        except BiasInputError as exc:
            # 400 is the correct HTTP status for invalid client input, while
            # still rendering a complete, readable page (the app never crashes).
            return render_calculator(form_values, unit, errors=exc.errors, status=400)

        return render_calculator(form_values, unit, result=result)

    return app


app = create_app()


if __name__ == "__main__":
    # Development server only.  Never expose this server to a public network.
    app.run(host="127.0.0.1", port=5000, debug=True)
