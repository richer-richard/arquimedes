import contextlib
import io
import json
import os
import unittest

from arquimedes.cli import main
from tests.fixture import roots


class CliTest(unittest.TestCase):

    def run_cli(self, *argv, mode="lean"):
        out, err = io.StringIO(), io.StringIO()
        old = os.environ.get("ARQUIMEDES_ROOT")
        os.environ["ARQUIMEDES_ROOT"] = str(roots()[mode])
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(list(argv))
        finally:
            if old is None:
                del os.environ["ARQUIMEDES_ROOT"]
            else:
                os.environ["ARQUIMEDES_ROOT"] = old
        return code, out.getvalue(), err.getvalue()

    def test_json_commands(self):
        for mode in ("full", "lean", "none"):
            with self.subTest(mode=mode):
                code, out, _ = self.run_cli("stats", "--json", mode=mode)
                self.assertEqual((code, json.loads(out)["totalProblems"]), (0, 5))
                code, out, _ = self.run_cli("search", "divisors", "--json", mode=mode)
                self.assertEqual([p["id"] for p in json.loads(out)], ["prob.aime-i-2020-p1"])
                code, out, _ = self.run_cli("sample", "-n", "2", "--seed", "1", "--json", mode=mode)
                self.assertEqual(len(json.loads(out)), 2)
                code, out, _ = self.run_cli("show", "prob.amc-12a-2020-p2", "--json", mode=mode)
                self.assertEqual(json.loads(out)["answer"], {"letter": "c", "value": "9"})

    def test_text_output(self):
        code, out, _ = self.run_cli("show", "prob.aime-i-2020-p1")
        self.assertEqual(code, 0)
        self.assertIn("Answer:", out)
        self.assertIn("Count exponent choices.", out)
        code, out, _ = self.run_cli("stats")
        self.assertIn("5", out)

    def test_unknown_problem(self):
        code, _, err = self.run_cli("show", "prob.core-999999")
        self.assertEqual(code, 1)
        self.assertIn("not found", err)


if __name__ == "__main__":
    unittest.main()
