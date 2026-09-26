"""TST-0105: Score-Baum (SPEC-0105 FR-01, FR-03)."""
import unittest

from sddlib.score import MetricLeaf, ScoreNode


class ScoreTest(unittest.TestCase):
    def test_fr01_blatt(self):
        self.assertEqual(MetricLeaf("cov", 80.0, 0.8).score(), 0.8)

    def test_fr03_gewichteter_mittelwert(self):
        knoten = ScoreNode("wartbarkeit", 1.0, [
            MetricLeaf("a", None, 1.0, weight=3.0),
            MetricLeaf("b", None, 0.0, weight=1.0),
        ])
        self.assertAlmostEqual(knoten.score(), 0.75)


if __name__ == "__main__":
    unittest.main()
