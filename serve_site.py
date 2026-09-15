# -*- coding: utf-8 -*-
"""极简静态文件服务器（不 import http.server，避免 getcwd 权限问题）。

用法：python3 serve_site.py [端口] [目录]
"""

import mimetypes
import socket
import socketserver
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

PORT: int = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
ROOT: Path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "site"

TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}


class Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            request = self.request.recv(65536).decode("utf-8", "replace")
            path = unquote(urlparse(request.splitlines()[0].split(" ")[1]).path)
        except (IndexError, OSError):
            return
        if path.endswith("/"):
            path += "index.html"
        target = (ROOT / path.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT.resolve())) or not target.is_file():
            body = b"<h1>404 Not Found</h1>"
            self._send(b"404 Not Found", b"text/html; charset=utf-8", body)
            return
        ctype = TYPES.get(target.suffix.lower()) or mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send(b"200 OK", ctype.encode(), target.read_bytes())

    def _send(self, status: bytes, ctype: bytes, body: bytes) -> None:
        header = (
            b"HTTP/1.1 " + status + b"\r\n"
            b"Content-Type: " + ctype + b"\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            # 每个连接只处理一个请求，显式告知浏览器不要复用连接
            b"Connection: close\r\n"
            b"Cache-Control: no-store\r\n\r\n"
        )
        try:
            self.request.sendall(header + body)
        except OSError:
            pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as srv:
        print(f"serving {ROOT} at http://localhost:{PORT}", flush=True)
        srv.serve_forever()
