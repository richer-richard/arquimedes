import json
import shutil
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from arquimedes.cli import main as cli_main
from arquimedes.engine import ArquimedesEngine
from arquimedes.fetch import fetch, select_files, wanted
from arquimedes.mcp_server import main as mcp_main
from arquimedes.paths import user_data_dir
from tests.fixture import RECORDS
from tools.lib.shards import write_shards


class _Files(BaseHTTPRequestHandler):
    def do_GET(self):
        key = urllib.parse.unquote(self.path.split("?", 1)[0]).lstrip("/")
        body = self.server.files.get(key)
        if body is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class FetchTest(unittest.TestCase):
    def test_file_filter(self):
        self.assertTrue(wanted("problems/core/shard-00000.jsonl.gz"))
        self.assertTrue(wanted("images/abc.svg"))
        self.assertTrue(wanted("rights.json"))
        self.assertFalse(wanted("README.md"))
        self.assertFalse(wanted(".gitattributes"))
        files = select_files([
            {"rfilename": "README.md", "size": 10},
            {"rfilename": "problems/core/shard-00000.jsonl.gz", "size": 20},
        ])
        self.assertEqual([item["rfilename"] for item in files], ["problems/core/shard-00000.jsonl.gz"])
        with self.assertRaises(SystemExit):
            select_files([{"rfilename": "README.md", "size": 1}])

    def test_download_and_lean_index(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        source = tmp / "src"
        shard = write_shards(RECORDS["core"][:1], source / "problems" / "core")[0]
        body = shard.read_bytes()
        name = shard.relative_to(source).as_posix()
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Files)
        server.files = {name: body}
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}/"
        dest = tmp / "corpus"
        code = fetch(dest, files=[{"rfilename": name, "size": len(body)}], base_url=url)
        self.assertEqual(code, 0)
        engine = ArquimedesEngine(root=dest)
        self.assertTrue(engine.has_sqlite)
        self.assertEqual(engine.db_mode, "lean")
        found = engine.search("divisors")
        self.assertEqual([item["id"] for item in found], ["prob.aime-i-2020-p1"])
        shown = engine.get_problem("prob.aime-i-2020-p1")
        self.assertIn("Factor 2020.", shown["solutions"][0]["hints"])
        server.shutdown()
        self.assertEqual(fetch(dest, files=[{"rfilename": name, "size": len(body)}], base_url=url), 0)

    def test_empty_root_points_at_fetch(self):
        empty = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty)
        stats = ArquimedesEngine(root=empty).get_stats()
        self.assertEqual(stats["totalProblems"], 0)
        self.assertIn("fetch", stats["note"])
        self.assertFalse(stats["sqliteReady"])

    def test_user_data_dir(self):
        self.assertEqual(user_data_dir().name, "arquimedes")

    def test_cli_fetch_uses_the_user_directory_by_default(self):
        with patch("arquimedes.fetch.fetch", return_value=0) as mocked:
            code = cli_main(["fetch"])
        self.assertEqual(code, 0)
        self.assertEqual(mocked.call_args.args[0], user_data_dir())

    def test_mcp_fetch_argv(self):
        with patch("arquimedes.fetch.main", return_value=0) as mocked:
            code = mcp_main(["fetch", "--help"])
        self.assertEqual(code, 0)
        self.assertEqual(mocked.call_args.args[0], ["--help"])

    def test_marker_records_the_source(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        source = tmp / "src"
        shard = write_shards(RECORDS["core"][:1], source / "problems" / "core")[0]
        name = shard.relative_to(source).as_posix()
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Files)
        server.files = {name: shard.read_bytes()}
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        dest = tmp / "corpus"
        fetch(
            dest,
            files=[{"rfilename": name, "size": shard.stat().st_size}],
            base_url=f"http://127.0.0.1:{server.server_port}/",
        )
        marker = json.loads((dest / "data" / "fetch.json").read_text(encoding="utf-8"))
        self.assertEqual(marker["index"], "lean")
        self.assertIn("richard01172000/arquimedes", marker["source"])
