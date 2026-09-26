"""Versteckte Tests zu SPEC-0105 (FR-01 bis FR-06)."""
import unittest

from sddlib.score import MetricLeaf, ScoreNode


def leaf(name, wert, weight=1.0, reason=None):
    return MetricLeaf(name, None, wert, weight=weight, reason=reason)


class HiddenLeafTest(unittest.TestCase):
    def test_fr01_na_blatt(self):
        b = leaf("x", None, reason="kein Tool")
        self.assertIsNone(b.score())
        self.assertTrue(b.incomplete())
        self.assertFalse(b.renormalized())

    def test_fr01_null_ist_messwert(self):
        b = leaf("x", 0.0)
        self.assertEqual(b.score(), 0.0)
        self.assertFalse(b.incomplete())


class HiddenNodeTest(unittest.TestCase):
    def test_fr02_unbekannte_regel(self):
        with self.assertRaises(ValueError):
            ScoreNode("n", 1.0, [], policy="lenient")

    def test_fr03_renormalize(self):
        n = ScoreNode("n", 1.0, [leaf("a", 0.6, 1.0), leaf("b", None, 3.0), leaf("c", 0.0, 1.0)])
        self.assertAlmostEqual(n.score(), 0.3)
        self.assertTrue(n.renormalized())
        self.assertTrue(n.incomplete())

    def test_fr03_null_zaehlt_mit(self):
        n = ScoreNode("n", 1.0, [leaf("a", 1.0), leaf("b", 0.0)])
        self.assertAlmostEqual(n.score(), 0.5)
        self.assertFalse(n.renormalized())
        self.assertFalse(n.incomplete())

    def test_fr03_alle_na_und_leer(self):
        self.assertIsNone(ScoreNode("n", 1.0, [leaf("a", None)]).score())
        self.assertIsNone(ScoreNode("n", 1.0, []).score())

    def test_fr02_gewicht_null_ignoriert(self):
        n = ScoreNode("n", 1.0, [leaf("a", 0.4), leaf("b", 1.0, weight=0)])
        self.assertAlmostEqual(n.score(), 0.4)
        s = ScoreNode("s", 1.0, [leaf("a", 0.4), leaf("b", None, weight=0)], policy="strict")
        self.assertAlmostEqual(s.score(), 0.4)
        self.assertFalse(s.renormalized())
        self.assertIsNone(ScoreNode("z", 1.0, [leaf("b", 1.0, weight=0)]).score())

    def test_fr03_strict(self):
        n = ScoreNode("n", 1.0, [leaf("a", 0.9), leaf("b", None)], policy="strict")
        self.assertIsNone(n.score())
        voll = ScoreNode("n", 1.0, [leaf("a", 0.9), leaf("b", 0.5)], policy="strict")
        self.assertAlmostEqual(voll.score(), 0.7)

    def test_fr03_quorum_grenze(self):
        kinder = [leaf("a", 0.8), leaf("b", None), leaf("c", 0.4), leaf("d", None)]
        self.assertAlmostEqual(ScoreNode("n", 1.0, kinder, policy="quorum", quorum=0.5).score(),
                               0.6)
        self.assertIsNone(ScoreNode("n", 1.0, kinder, policy="quorum", quorum=0.49).score())

    def test_fr03_quorum_nenner_ohne_gewicht_null(self):
        kinder = [leaf("a", 0.8), leaf("b", None), leaf("x", None, weight=0),
                  leaf("y", None, weight=0)]
        self.assertAlmostEqual(ScoreNode("n", 1.0, kinder, policy="quorum", quorum=0.5).score(),
                               0.8)

    def test_fr03_clamping(self):
        self.assertEqual(ScoreNode("n", 1.0, [leaf("a", 1.7)]).score(), 1.0)
        self.assertEqual(ScoreNode("n", 1.0, [leaf("a", -0.3)]).score(), 0.0)

    def test_fr03_verschachtelt(self):
        innen = ScoreNode("innen", 2.0, [leaf("a", None)])
        aussen = ScoreNode("aussen", 1.0, [innen, leaf("b", 0.5)])
        self.assertAlmostEqual(aussen.score(), 0.5)
        self.assertTrue(aussen.renormalized())

    def test_fr04_incomplete_auch_bei_gewicht_null_und_rekursiv(self):
        n = ScoreNode("n", 1.0, [leaf("a", 0.5), leaf("b", None, weight=0)])
        self.assertFalse(n.renormalized())
        self.assertTrue(n.incomplete())
        innen = ScoreNode("innen", 1.0, [leaf("a", 0.5), leaf("b", None)])
        aussen = ScoreNode("aussen", 1.0, [innen])
        self.assertFalse(aussen.renormalized())
        self.assertTrue(aussen.incomplete())


class HiddenReasonTest(unittest.TestCase):
    def test_fr05_kein_grund_bei_score(self):
        self.assertIsNone(ScoreNode("n", 1.0, [leaf("a", 0.5), leaf("b", None, reason="x")])
                          .na_reason())

    def test_fr05_eigener_grund_vor_kindern(self):
        n = ScoreNode("n", 1.0, [leaf("a", None, reason="kind")], reason="eigener")
        self.assertEqual(n.na_reason(), "eigener")

    def test_fr05_gruende_dedupliziert_rekursiv(self):
        innen = ScoreNode("innen", 1.0, [leaf("x", None, reason="kein mypy"),
                                         leaf("y", None, reason="kein mypy")])
        n = ScoreNode("n", 1.0, [leaf("a", None, reason="kein ruff"), leaf("b", None),
                                 innen, leaf("c", None, reason="kein ruff"),
                                 leaf("z", None, weight=0, reason="ignoriert")])
        self.assertEqual(n.na_reason(), "kein ruff; kein mypy")

    def test_fr05_strict_grund_der_fehlenden(self):
        n = ScoreNode("n", 1.0, [leaf("a", 0.9), leaf("b", None, reason="kein Tool")],
                      policy="strict")
        self.assertEqual(n.na_reason(), "kein Tool")

    def test_fr05_keine_messwerte(self):
        self.assertEqual(ScoreNode("n", 1.0, []).na_reason(), "keine Messwerte")
        self.assertEqual(ScoreNode("n", 1.0, [leaf("a", None)]).na_reason(), "keine Messwerte")
        self.assertEqual(ScoreNode("n", 1.0, [leaf("a", 1.0, weight=0)]).na_reason(),
                         "keine Messwerte")


class HiddenDictTest(unittest.TestCase):
    def test_fr06_knoten_mit_kindern_und_metriken(self):
        innen = ScoreNode("innen", 0.5, [leaf("a", 1 / 3)])
        n = ScoreNode("gesamt", 1.0, [innen, MetricLeaf("b", 12.0, None, reason="n/a")])
        d = n.to_dict()
        self.assertEqual(d["name"], "gesamt")
        self.assertEqual(d["weight"], 1.0)
        self.assertEqual(d["score"], 0.3333)
        self.assertIs(d["renormalized"], True)
        self.assertNotIn("reason", d)
        self.assertEqual(d["children"][0]["metrics"][0],
                         {"name": "a", "raw": None, "normalized": 0.3333, "weight": 1.0})
        self.assertEqual(d["metrics"], [{"name": "b", "raw": 12.0, "normalized": None,
                                         "weight": 1.0, "reason": "n/a"}])

    def test_fr06_optionale_schluessel_fehlen(self):
        d = ScoreNode("n", 1.0, [leaf("a", 0.5)]).to_dict()
        self.assertNotIn("renormalized", d)
        self.assertNotIn("reason", d)
        self.assertNotIn("children", d)
        self.assertEqual(ScoreNode("leer", 1.0, []).to_dict(),
                         {"name": "leer", "weight": 1.0, "score": None,
                          "reason": "keine Messwerte"})


if __name__ == "__main__":
    unittest.main()
