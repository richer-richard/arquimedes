"""Model Context Protocol (MCP) server for the Arquimedes Math Problem Database.

Implements standard MCP JSON-RPC 2.0 over stdio with zero external dependencies,
so it starts in <30ms in local environments (uv, Claude Desktop, Cursor) and
passes Glama automated Docker introspection checks out-of-the-box.
"""

from __future__ import annotations

import copy
import json
import sys
from typing import Any

from arquimedes import __version__
from arquimedes.engine import ArquimedesEngine

SERVER_INFO = {
    "name": "arquimedes-mcp",
    "version": __version__,
}

# Newest first; an unknown client version is answered with the newest.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

# Names used before 1.0. Still accepted by tools/call, but not listed.
TOOL_ALIASES = {
    "arquimedes_stats": "arquimedes_get_stats",
    "arquimedes_search": "arquimedes_search_problems",
    "arquimedes_sample": "arquimedes_sample_problems",
}

TOOLS = [
    {
        "name": "arquimedes_get_stats",
        "description": (
            "Summarize what the Arquimedes math problem database holds: {corpus}, with problem "
            "counts by dataset, category, and competition, and written-solution counts by kind. "
            "Call it first to learn which category, dataset, and competition values exist before "
            "filtering arquimedes_search_problems or arquimedes_sample_problems. Takes no arguments."
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
        "name": "arquimedes_search_problems",
        "description": (
            "Find problems by keyword in {problems}. Full-text search returns problems whose "
            "statement or title contains all the query words: a topic, a theorem name such as "
            "'Cauchy-Schwarz', or a LaTeX fragment. Optional filters narrow by category, dataset, "
            "competition, and Mohs difficulty (1.0 to 10.0). Results are summaries (id, title, "
            "competition, year, difficulty, answer, statement) without solutions; pass an id to "
            "arquimedes_get_problem for solutions and hints. To get random problems instead of "
            "keyword matches, use arquimedes_sample_problems."
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
        "name": "arquimedes_sample_problems",
        "description": (
            "Draw random problems from {problems}, uniformly among those matching optional filters: "
            "category, dataset, competition, contest year, Mohs difficulty range (1.0 to 10.0), "
            "multiple-choice only, or with a diagram. Use it to build practice sets, mock contests, "
            "or evaluation samples; pass the same seed to repeat a draw. Results are summaries "
            "without solutions; pass an id to arquimedes_get_problem for solutions. To find "
            "problems about a specific topic or keyword, use arquimedes_search_problems."
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
            "Fetch one problem by its id, as returned by arquimedes_search_problems or "
            "arquimedes_sample_problems (e.g. 'prob.ahsme-1950-p10', 'prob.numina-000369'). Returns "
            "the full record: LaTeX statement, answer choices, answer, written solutions with "
            "progressive hints, difficulty, source, and diagram references. Ids cannot be guessed; "
            "an unknown id returns an error, so discover ids with search or sample first."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem_id": {
                    "type": "string",
                    "description": "Problem id from a search or sample result (e.g. 'prob.ahsme-1950-p10', 'prob.aops-000000').",
                },
                "include_solutions": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include written solutions and their hints (default true). Set false to quiz without spoilers.",
                },
                "include_traces": {
                    "type": "boolean",
                    "default": False,
                    "description": "Also include the three long model-reasoning traces stored with deepmath problems (default false; each trace is typically over 10,000 characters).",
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


def _tools_for(engine: ArquimedesEngine) -> list[dict[str, Any]]:
    """Fill the description templates with what this server can actually search."""
    tools = copy.deepcopy(TOOLS)
    available: list[str] | None = None
    if engine.has_sqlite:
        stats = engine.get_stats()
        total = f"{stats.get('totalProblems', 0):,}"
        corpus = f"{total} problems across {len(stats.get('datasets') or {})} datasets"
        problems = f"{total} competition and olympiad math problems"
    else:
        available = engine.fallback_datasets()
        corpus = (
            "the problems this server can search (it is running without its SQLite index, "
            "so that is only part of the full corpus)"
        )
        problems = (
            "the competition and olympiad math problems this server can scan (it is running "
            "without its SQLite index; call arquimedes_get_stats for exact coverage)"
        )
    for tool in tools:
        tool["description"] = tool["description"].replace("{corpus}", corpus).replace("{problems}", problems)
        dataset = tool["inputSchema"]["properties"].get("dataset")
        if dataset is not None and available:
            dataset["enum"] = [d for d in dataset["enum"] if d in available]
    return tools


def _handle_tool_call(engine: ArquimedesEngine, name: str, args: dict[str, Any]) -> dict[str, Any]:
    name = TOOL_ALIASES.get(name, name)
    if not isinstance(args, dict):
        return {"isError": True, "content": [{"type": "text", "text": "Tool arguments must be a JSON object."}]}

    if name == "arquimedes_get_stats":
        data = engine.get_stats()
        return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}

    if name == "arquimedes_search_problems":
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

    if name == "arquimedes_sample_problems":
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
                "content": [{"type": "text", "text": f"Problem '{pid}' not found. Use arquimedes_search_problems or arquimedes_sample_problems to discover valid ids."}],
            }
        return {"content": [{"type": "text", "text": json.dumps(prob, indent=2, ensure_ascii=False)}]}

    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
    }


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _practice_set_prompt(args: dict[str, Any]) -> dict[str, Any] | None:
    """Messages for the math-practice-set prompt, or None if the difficulty is not a number."""
    cat = args.get("category") or "geometry"
    try:
        diff = min(10.0, max(1.0, float(args.get("difficulty", 5.0))))
    except (TypeError, ValueError):
        return None
    text = (
        f"Use `arquimedes_sample_problems` to draw 5 `{cat}` problems near Mohs difficulty {diff:.1f} "
        f"(min_mohs={max(1.0, diff - 0.8):.1f}, max_mohs={min(10.0, diff + 0.8):.1f}) and present them "
        "as a clean practice worksheet. When asked for answers, fetch each problem with "
        "`arquimedes_get_problem` and give its hints first, then the solution."
    )
    return {
        "description": f"Practice set for {cat} around Mohs {diff:.1f}",
        "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
    }


def handle_rpc_message(engine: ArquimedesEngine, msg: Any) -> dict[str, Any] | None:
    if not isinstance(msg, dict):
        return _error(None, -32600, "Invalid request: expected a JSON-RPC object")
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no id and expect no response
    if msg_id is None:
        return None
    if not isinstance(method, str):
        return _error(msg_id, -32600, "Invalid request: missing method")
    if not isinstance(params, dict):
        return _error(msg_id, -32602, "Invalid params: expected an object")

    if method == "initialize":
        client_proto = params.get("protocolVersion")
        proto = client_proto if client_proto in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
        return _result(msg_id, {
            "protocolVersion": proto,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": SERVER_INFO,
        })

    if method == "ping":
        return _result(msg_id, {})

    if method == "tools/list":
        return _result(msg_id, {"tools": _tools_for(engine)})

    if method == "tools/call":
        t_name = params.get("name", "")
        t_args = params.get("arguments")
        try:
            res = _handle_tool_call(engine, t_name, {} if t_args is None else t_args)
        except Exception as exc:  # report bad arguments to the caller instead of exiting
            res = {"isError": True, "content": [{"type": "text", "text": f"{t_name} failed: {exc}"}]}
        return _result(msg_id, res)

    if method == "resources/list":
        return _result(msg_id, {"resources": RESOURCES})

    if method == "resources/templates/list":
        return _result(msg_id, {"resourceTemplates": []})

    if method == "resources/read":
        uri = params.get("uri", "")
        if uri == "arquimedes://index":
            return _result(msg_id, {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(engine.get_stats(), indent=2),
                }],
            })
        return _error(msg_id, -32602, f"Unknown resource URI: {uri}")

    if method == "prompts/list":
        return _result(msg_id, {"prompts": PROMPTS})

    if method == "prompts/get":
        name = params.get("name")
        if name == "math-practice-set":
            prompt = _practice_set_prompt(params.get("arguments") or {})
            if prompt is None:
                return _error(msg_id, -32602, "difficulty must be a number from 1.0 to 10.0")
            return _result(msg_id, prompt)
        return _error(msg_id, -32602, f"Unknown prompt: {name}")

    return _error(msg_id, -32601, f"Method not found: {method}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if args[:1] == ["fetch"]:
        from arquimedes.fetch import main as fetch_main
        return fetch_main(args[1:])

    engine = ArquimedesEngine()
    if not engine.has_sqlite and not engine.fallback_datasets():
        print(
            f"Arquimedes has no corpus at {engine.root}. "
            "Download it with: uvx arquimedes-mcp fetch",
            file=sys.stderr,
        )
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = _error(None, -32700, "Parse error: invalid JSON")
        else:
            try:
                resp = handle_rpc_message(engine, msg)
            except Exception as exc:
                msg_id = msg.get("id") if isinstance(msg, dict) else None
                resp = _error(msg_id, -32603, f"Internal error: {exc}") if msg_id is not None else None
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
