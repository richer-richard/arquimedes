import json
import os
import subprocess
import sys
import unittest

from arquimedes import __version__
from arquimedes.engine import ArquimedesEngine
from arquimedes.mcp_server import TOOL_ALIASES, handle_rpc_message
from tests.fixture import roots

TOOL_NAMES = ["arquimedes_get_stats", "arquimedes_search_problems", "arquimedes_sample_problems", "arquimedes_get_problem"]


class McpHandlerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = ArquimedesEngine(root=roots()["lean"])

    def rpc(self, method, params=None, msg_id=1):
        return handle_rpc_message(self.engine, {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})

    def call(self, name, arguments):
        return self.rpc("tools/call", {"name": name, "arguments": arguments})["result"]

    def payload(self, result):
        self.assertFalse(result.get("isError"), result)
        return json.loads(result["content"][0]["text"])

    def test_initialize(self):
        res = self.rpc("initialize", {"protocolVersion": "2025-06-18"})["result"]
        self.assertEqual(res["protocolVersion"], "2025-06-18")
        self.assertEqual(res["serverInfo"], {"name": "arquimedes-mcp", "version": __version__})
        self.assertEqual(self.rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"], "2025-11-25")

    def test_tools_list(self):
        tools = self.rpc("tools/list")["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], TOOL_NAMES)
        for tool in tools:
            self.assertNotIn("{", tool["description"], tool["name"])
            self.assertTrue(tool["annotations"]["readOnlyHint"])

    def test_tools_answer(self):
        self.assertEqual(self.payload(self.call("arquimedes_get_stats", {}))["totalProblems"], 5)
        hits = self.payload(self.call("arquimedes_search_problems", {"query": "divisors"}))
        self.assertEqual([h["id"] for h in hits], ["prob.aime-i-2020-p1"])
        sample = self.payload(self.call("arquimedes_sample_problems", {"has_choices": True}))
        self.assertEqual([p["id"] for p in sample], ["prob.amc-12a-2020-p2"])
        prob = self.payload(self.call("arquimedes_get_problem", {"problem_id": "prob.aime-i-2020-p1"}))
        self.assertEqual(prob["answer"]["value"], "12")
        self.assertEqual(len(prob["solutions"]), 1)

    def test_pre_1_0_names_still_work(self):
        args_for = {"arquimedes_search_problems": {"query": "divisors"}, "arquimedes_sample_problems": {"seed": 3}}
        for old, new in TOOL_ALIASES.items():
            args = args_for.get(new, {})
            self.assertEqual(self.call(old, args), self.call(new, args))

    def test_tool_errors_are_results(self):
        self.assertTrue(self.call("arquimedes_get_problem", {"problem_id": "prob.core-999999"})["isError"])
        self.assertTrue(self.call("arquimedes_search_problems", {})["isError"])
        self.assertTrue(self.call("arquimedes_search_problems", {"query": "x", "limit": "many"})["isError"])
        self.assertTrue(self.call("arquimedes_get_problem", "prob.aime-i-2020-p1")["isError"])
        self.assertTrue(self.call("arquimedes_nope", {})["isError"])

    def test_resources_and_prompts(self):
        self.assertEqual(self.rpc("resources/templates/list")["result"], {"resourceTemplates": []})
        self.assertEqual([r["uri"] for r in self.rpc("resources/list")["result"]["resources"]], ["arquimedes://index"])
        index = json.loads(self.rpc("resources/read", {"uri": "arquimedes://index"})["result"]["contents"][0]["text"])
        self.assertEqual(index["totalProblems"], 5)
        self.assertEqual(self.rpc("resources/read", {"uri": "arquimedes://nope"})["error"]["code"], -32602)
        prompt = self.rpc("prompts/get", {"name": "math-practice-set", "arguments": {"category": "algebra", "difficulty": "6.5"}})
        self.assertIn("arquimedes_sample_problems", prompt["result"]["messages"][0]["content"]["text"])
        bad = self.rpc("prompts/get", {"name": "math-practice-set", "arguments": {"difficulty": "hard"}})
        self.assertEqual(bad["error"]["code"], -32602)

    def test_protocol_errors(self):
        self.assertIsNone(handle_rpc_message(self.engine, {"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(self.rpc("nope/nope")["error"]["code"], -32601)
        self.assertEqual(handle_rpc_message(self.engine, [1, 2])["error"]["code"], -32600)
        self.assertEqual(self.rpc("ping"), {"jsonrpc": "2.0", "id": 1, "result": {}})


class McpStdioTest(unittest.TestCase):

    def test_server_survives_bad_input(self):
        lines = [
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
            "not json",
            '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"arquimedes_sample_problems","arguments":{"limit":"x"}}}',
            '{"jsonrpc":"2.0","method":"notifications/initialized"}',
            '{"jsonrpc":"2.0","id":3,"method":"tools/list"}',
        ]
        env = dict(os.environ, ARQUIMEDES_ROOT=str(roots()["full"]))
        out = subprocess.run([sys.executable, "-m", "arquimedes.mcp_server"], input="\n".join(lines) + "\n",
                             capture_output=True, text=True, env=env, timeout=60, check=True).stdout
        replies = [json.loads(line) for line in out.splitlines()]
        self.assertEqual([r.get("id") for r in replies], [1, None, 2, 3])
        self.assertEqual(replies[1]["error"]["code"], -32700)
        self.assertTrue(replies[2]["result"]["isError"])
        self.assertEqual(len(replies[3]["result"]["tools"]), 4)


if __name__ == "__main__":
    unittest.main()
