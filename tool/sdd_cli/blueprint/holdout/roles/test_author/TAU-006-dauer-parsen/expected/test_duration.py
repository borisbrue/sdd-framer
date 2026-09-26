import unittest

from timebox.duration import DurationError, parse_duration


class ParseDurationTest(unittest.TestCase):
    # FR-01
    def test_fr01_single_units(self):
        self.assertEqual(parse_duration("2d"), 172800)
        self.assertEqual(parse_duration("3h"), 10800)
        self.assertEqual(parse_duration("7m"), 420)
        self.assertEqual(parse_duration("9s"), 9)

    def test_fr01_combined(self):
        self.assertEqual(parse_duration("1h30m"), 5400)
        self.assertEqual(parse_duration("1d2h3m4s"), 86400 + 7200 + 180 + 4)

    def test_fr01_plain_number_and_zero(self):
        self.assertEqual(parse_duration("45"), 45)
        self.assertEqual(parse_duration("0s"), 0)

    def test_fr01_whitespace_and_case(self):
        self.assertEqual(parse_duration(" 2H "), 7200)
        self.assertEqual(parse_duration("1H5M"), 3900)

    # FR-02
    def test_fr02_error_is_value_error(self):
        self.assertTrue(issubclass(DurationError, ValueError))

    def test_fr02_invalid_inputs(self):
        for text in ("", "   ", "5w", "h", "1h30", "-5s", "1.5h", "1h 30m", "1m1h", "1h1h",
                     "10x"):
            with self.subTest(text=text), self.assertRaises(DurationError):
                parse_duration(text)


if __name__ == "__main__":
    unittest.main()
