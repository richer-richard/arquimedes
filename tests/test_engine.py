import unittest

from arquimedes.engine import ArquimedesEngine
from tests.fixture import ALL_IDS, roots

MODES = ("full", "lean", "none")


class EngineModesTest(unittest.TestCase):
    """The same questions must get the same answers with a full, lean, or missing database."""

    @classmethod
    def setUpClass(cls):
        cls.engines = {mode: ArquimedesEngine(root=root) for mode, root in roots().items()}

    def test_modes_detected(self):
        self.assertEqual(self.engines["full"].db_mode, "full")
        self.assertEqual(self.engines["lean"].db_mode, "lean")
        self.assertFalse(self.engines["none"].has_sqlite)

    def test_get_problem_identical_across_modes(self):
        for pid in ALL_IDS:
            for sols in (True, False):
                for traces in (True, False):
                    views = {m: self.engines[m].get_problem(pid, include_solutions=sols, include_traces=traces)
                             for m in MODES}
                    with self.subTest(pid=pid, solutions=sols, traces=traces):
                        self.assertIsNotNone(views["full"])
                        self.assertEqual(views["full"], views["lean"])
                        self.assertEqual(views["full"], views["none"])

    def test_get_problem_shape(self):
        p = self.engines["full"].get_problem("prob.aime-i-2020-p1")
        self.assertEqual(list(p), ["id", "title", "category", "subjects", "concepts", "source", "difficulty",
                                   "estimatedMinutes", "statement", "answerChoices", "answer", "solutions", "images"])
        self.assertEqual(p["source"]["number"], 1)
        self.assertEqual(p["answer"], {"letter": None, "value": "12"})
        self.assertEqual(p["solutions"][0]["hints"], ["Factor 2020.", "Count exponent choices."])
        self.assertEqual(list(p["solutions"][0]), ["id", "kind", "text", "hints"])
        self.assertEqual(self.engines["lean"].get_problem("prob.hmmt-feb-guts-2019-ph-4")["source"]["number"], "H4")
        mc = self.engines["lean"].get_problem("prob.amc-12a-2020-p2")
        self.assertEqual(mc["answer"]["letter"], "c")
        self.assertEqual([c["label"] for c in mc["answerChoices"]], list("ABCDE"))

    def test_traces_only_on_request(self):
        for mode in MODES:
            engine = self.engines[mode]
            with self.subTest(mode=mode):
                self.assertEqual(engine.get_problem("prob.deepmath-000000")["solutions"], [])
                kinds = [s["kind"] for s in engine.get_problem("prob.deepmath-000000", include_traces=True)["solutions"]]
                self.assertEqual(kinds, ["model-reasoning"] * 3)
                self.assertEqual(engine.get_problem("prob.aime-i-2020-p1", include_solutions=False)["solutions"], [])

    def test_unknown_id(self):
        for mode in MODES:
            self.assertIsNone(self.engines[mode].get_problem("prob.core-999999"), mode)

    def test_search(self):
        for mode in MODES:
            engine = self.engines[mode]
            with self.subTest(mode=mode):
                hits = engine.search("divisors")
                self.assertEqual([h["id"] for h in hits], ["prob.aime-i-2020-p1"])
                self.assertEqual(hits[0]["number"], 1)
                self.assertEqual(engine.search("divisors", category="geometry"), [])
                self.assertEqual([h["id"] for h in engine.search("pigeonhole", min_mohs=6.5)], ["prob.aops-000000"])
        summaries = {m: self.engines[m].search("square") for m in MODES}
        self.assertEqual(summaries["full"], summaries["lean"])
        self.assertEqual(summaries["full"], summaries["none"])

    def test_sample_filters(self):
        cases = [
            ({}, set(ALL_IDS)),
            ({"has_choices": True}, {"prob.amc-12a-2020-p2"}),
            ({"has_choices": False}, set(ALL_IDS) - {"prob.amc-12a-2020-p2"}),
            ({"has_diagram": True}, {"prob.amc-12a-2020-p2"}),
            ({"dataset": "deepmath"}, {"prob.deepmath-000000"}),
            ({"min_mohs": 6.0}, {"prob.aops-000000", "prob.deepmath-000000"}),
            ({"year": 2020, "category": "geometry"}, {"prob.amc-12a-2020-p2"}),
            ({"competition": "Putnam"}, set()),
        ]
        for mode in MODES:
            for filters, expected in cases:
                with self.subTest(mode=mode, filters=filters):
                    got = self.engines[mode].sample(limit=10, **filters)
                    self.assertEqual({p["id"] for p in got}, expected)
                    self.assertEqual(len(got), len(expected))

    def test_sample_seeded(self):
        for mode in MODES:
            engine = self.engines[mode]
            with self.subTest(mode=mode):
                first = engine.sample(limit=2, seed=11)
                self.assertEqual(len(first), 2)
                self.assertEqual(first, engine.sample(limit=2, seed=11))

    def test_stats(self):
        for mode in MODES:
            stats = self.engines[mode].get_stats()
            with self.subTest(mode=mode):
                self.assertEqual(stats["totalProblems"], 5)
                self.assertEqual(stats["solutionKinds"], {"model-reasoning": 3, "proof-sketch": 3})
                self.assertEqual(stats["sqliteReady"], mode != "none")


if __name__ == "__main__":
    unittest.main()
