"""Flask routes for the BJT voltage-divider DC bias calculator."""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    DEFAULTS,
    BiasInputError,
    parse_inputs,
    solve_voltage_divider_bias,
)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    @app.template_filter("num3")
    def num3(value: float) -> str:
        return f"{value:,.3f}"

    @app.template_filter("num0")
    def num0(value: float) -> str:
        return f"{value:,.0f}"

    def render_page(
        form,
        result=None,
        errors: dict[str, str] | None = None,
        status: int = 200,
    ):
        return (
            render_template(
                "index.html",
                form=form,
                result=result,
                errors=errors or {},
            ),
            status,
        )

    @app.get("/")
    def index():
        return render_page(DEFAULTS)

    @app.post("/calculate")
    @app.post("/")
    def calculate():
        submitted = request.form
        try:
            values = parse_inputs(submitted)
            result = solve_voltage_divider_bias(**values)
        except BiasInputError as exc:
            return render_page(submitted, errors=exc.errors, status=400)
        return render_page(submitted, result=result)

    return app


app = create_app()
