"""Flask routes for the BJT DC bias calculator (divider, fixed, emitter)."""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    BIAS_MODES,
    INVALID_MODE_MESSAGE,
    MODE_DEFAULTS,
    OUTPUT_UNITS,
    REGION_LABELS,
    BiasInputError,
    parse_inputs,
    solve_bias,
)

MODE_LABELS = {
    "divider": "Voltage-Divider Bias",
    "fixed": "Fixed Bias (RB ตัวเดียว)",
    "emitter": "Emitter Bias (RB + RE)",
}

# ลำดับการแสดงผลในตารางรายละเอียด (คีย์ผลลัพธ์, ป้ายกำกับ)
DISPLAY_ROWS = (
    ("vth_v", "VTH"),
    ("rth_kohm", "RTH"),
    ("ib_ua", "IB"),
    ("ic_ma", "IC"),
    ("ie_ma", "IE"),
    ("ve_v", "VE"),
    ("vb_v", "VB"),
    ("vc_v", "VC"),
    ("vce_v", "VCE"),
    ("power_q_mw", "กำลังสูญเสียที่ Q"),
)

TILE_KEYS = (
    ("vb_v", "VB"),
    ("ve_v", "VE"),
    ("vc_v", "VC"),
    ("vce_v", "VCE"),
    ("ic_ma", "IC"),
)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    @app.template_filter("num3")
    def num3(value: float) -> str:
        return f"{value:,.3f}"

    def render_page(
        form,
        mode: str = "divider",
        result: dict | None = None,
        errors: dict[str, str] | None = None,
        status: int = 200,
    ):
        rows = []
        tiles = []
        region_label = ""
        if result:
            values = result["values"]
            rows = [
                {"label": label, "value": values[key], "unit": OUTPUT_UNITS[key]}
                for key, label in DISPLAY_ROWS
                if key in values
            ]
            tiles = [
                {"label": label, "value": values[key], "unit": OUTPUT_UNITS[key]}
                for key, label in TILE_KEYS
                if key in values
            ]
            region_label = REGION_LABELS.get(result["region"], result["region"])

        return (
            render_template(
                "index.html",
                form=form,
                mode=mode,
                mode_labels=MODE_LABELS,
                result=result,
                rows=rows,
                tiles=tiles,
                region_label=region_label,
                errors=errors or {},
            ),
            status,
        )

    @app.get("/")
    def index():
        mode = request.args.get("mode", "divider")
        if mode not in BIAS_MODES:
            return render_page(
                MODE_DEFAULTS["divider"],
                "divider",
                errors={"mode": INVALID_MODE_MESSAGE},
                status=400,
            )
        return render_page(MODE_DEFAULTS[mode], mode)

    @app.post("/calculate")
    @app.post("/")
    def calculate():
        submitted = request.form
        mode = submitted.get("mode", "divider")
        if mode not in BIAS_MODES:
            return render_page(
                MODE_DEFAULTS["divider"],
                "divider",
                errors={"mode": INVALID_MODE_MESSAGE},
                status=400,
            )
        try:
            values = parse_inputs(submitted, mode)
            result = solve_bias(mode, values)
        except BiasInputError as exc:
            return render_page(submitted, mode, errors=exc.errors, status=400)
        return render_page(submitted, mode, result=result)

    return app


app = create_app()
