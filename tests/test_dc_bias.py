import unittest

from dc_bias import DEFAULTS, BiasInputError, parse_inputs, to_ohms


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


if __name__ == "__main__":
    unittest.main()
