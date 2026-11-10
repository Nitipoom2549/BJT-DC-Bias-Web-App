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


class SaturationSolutionTests(unittest.TestCase):
    """Saturation must be solved with VCE fixed, not with beta x IB."""

    def setUp(self):
        self.result = solve_voltage_divider_bias(
            vcc=12.0, r1=10_000.0, r2=10_000.0, rc=10_000.0,
            re=1_000.0, beta=100.0, vbe=0.70,
        )

    def test_saturation_currents_match_hand_calculation(self):
        r = self.result
        self.assertAlmostEqual(r.ic, 9.9846153846154e-4, places=11)
        self.assertAlmostEqual(r.ib, 7.1692307692308e-4, places=11)
        self.assertAlmostEqual(r.ie, 1.7153846153846e-3, places=11)

    def test_saturation_voltages_match_hand_calculation(self):
        r = self.result
        self.assertAlmostEqual(r.vce, 0.30, places=9)
        self.assertAlmostEqual(r.ve, 1.7153846153846, places=9)
        self.assertAlmostEqual(r.vc, 2.0153846153846, places=9)
        self.assertAlmostEqual(r.vb, 2.4153846153846, places=9)

    def test_saturation_satisfies_circuit_laws(self):
        r = self.result
        self.assertAlmostEqual(r.ie, r.ic + r.ib, places=12)
        self.assertAlmostEqual(r.vb, r.ve + r.vbe, places=9)
        self.assertAlmostEqual(r.vc, r.vcc - r.ic * r.rc, places=9)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=9)
        self.assertAlmostEqual(r.vth, r.ib * r.rth + r.vbe + r.ie * r.re, places=9)

    def test_saturation_outputs_are_physical(self):
        r = self.result
        self.assertGreater(r.ic, 0.0)
        self.assertGreater(r.ib, 0.0)
        self.assertGreater(r.ve, 0.0)
        self.assertLess(r.vc, r.vcc)
        self.assertGreater(r.power_q_mw, 0.0)

    def test_saturation_is_not_beta_controlled(self):
        r = self.result
        self.assertLess(r.ic / r.ib, r.beta)
        self.assertNotAlmostEqual(r.ic / r.ib, r.beta, places=1)

    def test_saturation_assumption_is_reported(self):
        self.assertTrue(any("VCE" in a for a in self.result.assumptions))

    def test_inconsistent_saturation_falls_back_to_cutoff(self):
        r = solve_voltage_divider_bias(
            vcc=12.0, r1=1_000.0, r2=100_000.0, rc=1_000.0,
            re=100_000.0, beta=100.0, vbe=0.0,
        )
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r.vb, r.vth)
        self.assertAlmostEqual(r.vc, r.vcc)
        self.assertTrue(any("Saturation" in w for w in r.warnings))


if __name__ == "__main__":
    unittest.main()
