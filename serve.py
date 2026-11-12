#!/usr/bin/env python3
"""Local preview with auto-rebuild. Edit content/ or data/ and refresh the browser.

    python serve.py           http://localhost:8080
    python serve.py 3000      another port
"""
import http.server
import importlib
import sys
import threading
import time
import traceback
from functools import partial
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent
WATCH = ["content", "data", "src", "static", "build.py"]
PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8080


def snapshot():
    files = []
    for name in WATCH:
        path = ROOT / name
        files.extend(path.rglob("*") if path.is_dir() else [path])
    return {p: p.stat().st_mtime for p in files if p.is_file()}


def watch():
    last = snapshot()
    while True:
        time.sleep(1)
        now = snapshot()
        if now != last:
            last = now
            try:
                importlib.reload(build)  # pick up edits to build.py itself
                build.build(drafts=True)
            except Exception:
                traceback.print_exc()


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        page = build.DIST / "404.html"
        if code == 404 and page.exists():
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().send_error(code, message, explain)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    build.build(drafts=True)
    threading.Thread(target=watch, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(build.DIST)))
    print(f"Serving on http://localhost:{PORT}  (drafts shown, Ctrl+C to stop)")
    server.serve_forever()
