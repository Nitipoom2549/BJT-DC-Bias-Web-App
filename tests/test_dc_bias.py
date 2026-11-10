import unittest

from dc_bias import (
    DEFAULTS,
    BiasInputError,
    parse_inputs,
    solve_voltage_divider_bias,
    to_ohms,
)


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


if __name__ == "__main__":
    unittest.main()
