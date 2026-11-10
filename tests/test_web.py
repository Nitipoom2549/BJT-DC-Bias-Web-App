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


if __name__ == "__main__":
    unittest.main()
