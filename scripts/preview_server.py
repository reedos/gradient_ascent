"""Serve the built site privately, under the same base path GitHub Pages will use.

    python scripts/preview_server.py --host 127.0.0.1 --port 4360

The site is built with base `/gradient_ascent/`, so every link in `site/dist` points there. A
plain file server rooted at `site/dist` would break them; this one mounts `site/dist` at the base
path and redirects `/` to it. It serves files only, sends `X-Robots-Tag: noindex`, and binds to
the one address you give it. Bind it to a private address (loopback, or a VPN address) to read the
real site on another device before it is public. Build first: `npm run build` in `site/`.
"""

from __future__ import annotations

import argparse
import posixpath
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "site" / "dist"


class Handler(SimpleHTTPRequestHandler):
    base = "/gradient_ascent/"

    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if not path.startswith(self.base):
            return str(DIST / "__outside_base__")
        rel = posixpath.normpath("/" + path[len(self.base):]).lstrip("/")
        return str(DIST / rel) if rel not in ("", ".") else str(DIST)

    def do_GET(self) -> None:  # noqa: N802
        bare = self.path.split("?", 1)[0]
        if bare in ("/", self.base.rstrip("/")):
            self.send_response(302)
            self.send_header("Location", self.base)
            self.end_headers()
            return
        super().do_GET()

    def send_error(self, code, message=None, explain=None):  # noqa: ANN001
        page = DIST / "404.html"
        if code == 404 and page.exists():
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def end_headers(self) -> None:
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1", help="address to bind (default: loopback only)")
    parser.add_argument("--port", type=int, default=4360)
    parser.add_argument("--base", default="/gradient_ascent/", help="base path the site was built with")
    args = parser.parse_args()
    if not (DIST / "index.html").exists():
        parser.error(f"no built site at {DIST}; run `npm run build` in site/ first")
    Handler.base = "/" + args.base.strip("/") + "/"
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(DIST)))
    print(f"serving {DIST} at http://{args.host}:{args.port}{Handler.base}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
