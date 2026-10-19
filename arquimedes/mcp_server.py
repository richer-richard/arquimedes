"""Model Context Protocol (MCP) server for the Arquimedes Math Problem Database.

Implements standard MCP JSON-RPC 2.0 over stdio with zero external dependencies,
so it starts in <30ms in local environments (uv, Claude Desktop, Cursor) and
passes Glama automated Docker introspection checks out-of-the-box.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from arquimedes import __version__
from arquimedes.engine import ArquimedesEngine

SERVER_INFO = {
    "name": "arquimedes-mcp",
    "version": __version__,
}

TOOLS = [
    {
        "name": "arquimedes_stats",
        "description": (
            "Get summary statistics for the Arquimedes math problem database "
            "(1,038,963 problems across 9 datasets, categories, competitions, and solution kinds)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Database Statistics",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "arquimedes_search",
        "description": (
            "Full-text search across 1,038,963 competition and olympiad math problems "
            "by keyword, theorem name, or LaTeX expression, with optional filters for "
            "category, dataset, competition, and unified Mohs difficulty (1.0 to 10.0)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords, theorem name (e.g. 'Cauchy-Schwarz', 'pigeonhole'), or LaTeX snippet.",
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "algebra",
                        "arithmetic",
                        "combinatorics",
                        "geometry",
                        "logic-foundations",
                        "number-theory",
                        "probability",
                        "problem-solving-techniques",
                        "uncategorized",
                    ],
                    "description": "Optional subject category filter.",
                },
                "dataset": {
                    "type": "string",
                    "enum": [
                        "core",
                        "aops",
                        "cemc",
                        "olympiadbench",
                        "omnimath",
                        "math",
                        "deepmath",
                        "numina",
                        "bigmath",
                    ],
                    "description": "Optional source dataset slug filter.",
                },
                "competition": {
                    "type": "string",
                    "description": "Optional competition name (e.g. 'IMO', 'USAMO', 'AIME I', 'AMC 12A', 'HMMT February', 'Putnam').",
                },
                "min_mohs": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 10.0,
                    "description": "Minimum Mohs difficulty rating (1.0 = elementary, 5.0 = AIME, 8.5+ = IMO/Putnam).",
                },
                "max_mohs": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 10.0,
                    "description": "Maximum Mohs difficulty rating (1.0 to 10.0).",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Maximum number of problems to return (1-50, default 10).",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Search Math Problems",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "arquimedes_sample",
        "description": (
            "Sample random math problems matching topic, difficulty (Mohs 1-10), "
            "competition, contest year, multiple-choice, or diagram filters. Ideal for "
            "generating practice sets, mock olympiad tests, or evaluation benchmarks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "algebra",
                        "arithmetic",
                        "combinatorics",
                        "geometry",
                        "logic-foundations",
                        "number-theory",
                        "probability",
                        "problem-solving-techniques",
                    ],
                    "description": "Optional subject category filter.",
                },
                "dataset": {
                    "type": "string",
                    "enum": [
                        "core",
                        "aops",
                        "cemc",
                        "olympiadbench",
                        "omnimath",
                        "math",
                        "deepmath",
                        "numina",
                        "bigmath",
                    ],
                    "description": "Optional dataset filter.",
                },
                "competition": {
                    "type": "string",
                    "description": "Optional competition name (e.g. 'IMO', 'USAMO', 'AIME I', 'AMC 10A', 'Putnam').",
                },
                "year": {
                    "type": "integer",
                    "description": "Optional contest year filter (e.g. 2024).",
                },
                "min_mohs": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 10.0,
                    "description": "Minimum Mohs difficulty rating (1.0 to 10.0).",
                },
                "max_mohs": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 10.0,
                    "description": "Maximum Mohs difficulty rating (1.0 to 10.0).",
                },
                "has_choices": {
                    "type": "boolean",
                    "description": "If true, only multiple-choice problems; if false, only free-response/proof problems.",
                },
                "has_diagram": {
                    "type": "boolean",
                    "description": "If true, only problems with SVG/JPG geometry diagrams.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 5,
                    "description": "Number of problems to sample (default 5).",
                },
                "seed": {
                    "type": "integer",
                    "description": "Optional random seed for reproducible sampling.",
                },
            },
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Sample Math Problems",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
    {
        "name": "arquimedes_get_problem",
        "description": (
            "Fetch a single math problem by its ID (e.g. 'prob.ahsme-1950-p10' or 'prob.aops-000000'), "
            "returning the full LaTeX statement, answer choices, verified answer, progressive hints, "
            "written proof solutions, and diagram references."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem_id": {
                    "type": "string",
                    "description": "Unique problem identifier (e.g. 'prob.ahsme-1950-p10', 'prob.aops-000000').",
                },
                "include_solutions": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include written solutions and hints (default true).",
                },
                "include_traces": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include long-CoT R1 reasoning traces for deepmath records.",
                },
            },
            "required": ["problem_id"],
            "additionalProperties": False,
        },
        "annotations": {
            "title": "Get Math Problem by ID",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
]

RESOURCES = [
    {
        "uri": "arquimedes://index",
        "name": "Arquimedes Summary Index",
        "description": "Global problem counts by dataset, category, competition, and solution kind.",
        "mimeType": "application/json",
    },
]

PROMPTS = [
    {
        "name": "math-practice-set",
        "description": "Generate a calibrated math competition practice set with hints and solutions.",
        "arguments": [
            {"name": "category", "description": "Math topic (e.g. geometry, number-theory, algebra, combinatorics)", "required": True},
            {"name": "difficulty", "description": "Target Mohs difficulty (1.0 to 10.0, e.g. 5.0 for AIME, 8.0 for Olympiad)", "required": False},
        ],
    },
]


def _handle_tool_call(engine: ArquimedesEngine, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "arquimedes_stats":
        data = engine.get_stats()
        return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}

    if name == "arquimedes_search":
        query = args.get("query")
        if not query or not isinstance(query, str):
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Parameter 'query' is required and must be a non-empty string."}],
            }
        results = engine.search(
            query,
            category=args.get("category"),
            dataset=args.get("dataset"),
            competition=args.get("competition"),
            min_mohs=args.get("min_mohs"),
            max_mohs=args.get("max_mohs"),
            limit=args.get("limit", 10),
        )
        return {"content": [{"type": "text", "text": json.dumps(results, indent=2, ensure_ascii=False)}]}

    if name == "arquimedes_sample":
        results = engine.sample(
            category=args.get("category"),
            dataset=args.get("dataset"),
            competition=args.get("competition"),
            year=args.get("year"),
            min_mohs=args.get("min_mohs"),
            max_mohs=args.get("max_mohs"),
            has_choices=args.get("has_choices"),
            has_diagram=args.get("has_diagram"),
            limit=args.get("limit", 5),
            seed=args.get("seed"),
        )
        return {"content": [{"type": "text", "text": json.dumps(results, indent=2, ensure_ascii=False)}]}

    if name == "arquimedes_get_problem":
        pid = args.get("problem_id")
        if not pid or not isinstance(pid, str):
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Parameter 'problem_id' is required."}],
            }
        prob = engine.get_problem(
            pid,
            include_solutions=bool(args.get("include_solutions", True)),
            include_traces=bool(args.get("include_traces", False)),
        )
        if prob is None:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Problem '{pid}' not found. Use arquimedes_search or arquimedes_sample to discover valid IDs."}],
            }
        return {"content": [{"type": "text", "text": json.dumps(prob, indent=2, ensure_ascii=False)}]}

    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
    }


def handle_rpc_message(engine: ArquimedesEngine, msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no id and expect no response
    if msg_id is None:
        return None

    if method == "initialize":
        client_proto = params.get("protocolVersion") or "2024-11-05"
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": client_proto,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": SERVER_INFO,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        t_name = params.get("name", "")
        t_args = params.get("arguments") or {}
        res = _handle_tool_call(engine, t_name, t_args)
        return {"jsonrpc": "2.0", "id": msg_id, "result": res}

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"resources": RESOURCES}}

    if method == "resources/read":
        uri = params.get("uri", "")
        if uri == "arquimedes://index":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(engine.get_stats(), indent=2),
                        }
                    ]
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32602, "message": f"Unknown resource URI: {uri}"},
        }

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"prompts": PROMPTS}}

    if method == "prompts/get":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "math-practice-set":
            cat = args.get("category", "geometry")
            diff = args.get("difficulty", "5.0")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "description": f"Practice set for {cat} around Mohs {diff}",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": (
                                    f"Use `arquimedes_sample` to pull 5 `{cat}` problems near Mohs difficulty {diff} "
                                    f"(e.g. min_mohs={max(1.0, float(diff)-0.8):.1f}, max_mohs={min(10.0, float(diff)+0.8):.1f}) "
                                    "and present them as a clean practice worksheet before revealing the solutions."
                                ),
                            },
                        }
                    ],
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32602, "message": f"Unknown prompt: {name}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    engine = ArquimedesEngine()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_rpc_message(engine, msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
