import unittest

from tools.lib.rights import load_catalog, rights_for, stamp


def rec(dataset, collection=None, tags=None, rid="prob.x"):
    return {
        "id": rid,
        "source": {
            "dataset": dataset,
            "collection": collection,
            "tags": tags or [],
        },
    }


class RightsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def rights(self, dataset, collection=None, tags=None):
        return rights_for(rec(dataset, collection, tags), self.catalog)

    def test_contest_parts(self):
        self.assertEqual(self.rights("core", "HMMT February")["part"], "hmmt")
        self.assertEqual(self.rights("core", "HMMT Invitational")["part"], "hmmt")
        self.assertEqual(self.rights("core", "IMO")["part"], "imo")
        self.assertEqual(self.rights("core", "AMC 12A")["part"], "maa")
        self.assertEqual(self.rights("core", "AHSME")["part"], "maa")
        self.assertEqual(self.rights("core", "USA TSTST")["part"], "maa")
        self.assertIsNone(self.rights("core", "AIME")["distribution"])
        self.assertEqual(self.rights("aops", "IMO Shortlist")["part"], "imo-shortlist")
        self.assertEqual(self.rights("aops", "APMO")["part"], "apmo")
        self.assertEqual(self.rights("aops", "Canadian MO")["part"], "cmo")
        self.assertEqual(self.rights("aops", "Putnam")["part"], "maa")
        self.assertEqual(self.rights("aops", "USAJMO")["part"], "maa")
        cemc = self.rights("cemc", "Gauss")
        self.assertEqual(cemc["distribution"], "CC-BY-NC-4.0")
        self.assertEqual(cemc["use"], "noncommercial")

    def test_passed_through_parts(self):
        tagged = self.rights("numina", tags=["amc_aime", "Mathematics -> Algebra"])
        self.assertEqual(tagged["part"], "numina/amc_aime")
        self.assertEqual(tagged["holder"], "Mathematical Association of America")
        self.assertEqual(tagged["distribution"], "Apache-2.0")
        self.assertEqual(self.rights("bigmath", tags=["gsm8k"])["part"], "bigmath/gsm8k")
        self.assertEqual(self.rights("math")["distribution"], "MIT")
        self.assertEqual(self.rights("deepmath")["use"], "pass-through")
        self.assertEqual(self.rights("olympiadbench")["part"], "olympiadbench")
        self.assertEqual(self.rights("omnimath")["part"], "omnimath")

    def test_stamp_leaves_the_original_alone(self):
        original = rec("core", "IMO")
        stamped = stamp(original, self.catalog)
        self.assertNotIn("rights", original)
        self.assertEqual(stamped["rights"]["part"], "imo")
        self.assertEqual(stamped["source"], original["source"])

    def test_unknown_origin_is_an_error(self):
        with self.assertRaises(KeyError):
            rights_for(rec("numina", tags=["Mathematics -> Algebra"]), self.catalog)
        with self.assertRaises(KeyError):
            rights_for(rec("numina", tags=["not-a-real-source"]), self.catalog)

    def test_catalog_fields(self):
        for part, entry in self.catalog["parts"].items():
            self.assertEqual(set(entry), {"holder", "distribution", "use", "url", "notice"})
            self.assertIn(entry["use"], {"notice-only", "noncommercial", "pass-through"})
            self.assertTrue(entry["holder"])
            self.assertTrue(entry["notice"])
            if entry["use"] == "notice-only":
                self.assertIsNone(entry["distribution"])
            else:
                self.assertIsNotNone(entry["distribution"])
