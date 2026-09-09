#!/usr/bin/env python3
"""HTTP-level regression checks for baseline security controls."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402


def get(base: str, path: str):
    try:
        with urlopen(f"{base}{path}", timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def post(base: str, path: str, payload: bytes, content_type: str = "application/json"):
    req = Request(
        f"{base}{path}",
        data=payload,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def setup_test_db() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="kosmik-security-http-"))
    server.DATA = tmp / "data"
    server.UPLOADS = tmp / "uploads"
    server.MEDIA_DIR = tmp / "media"
    server.DB = server.DATA / "test.sqlite3"
    server.init_db()


def main() -> None:
    setup_test_db()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        status, headers, _ = get(base, "/api/health")
        assert status == 200
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "frame-ancestors 'self'" in headers.get("Content-Security-Policy", "")
        assert "object-src 'none'" in headers.get("Content-Security-Policy", "")

        status, _, _ = get(base, "/backend/server.py")
        assert status == 404, status
        status, _, _ = get(base, "/backend/.env")
        assert status == 404, status

        for path in ("/api/admin/orders", "/api/admin/messages", "/api/admin/stats", "/api/admin/gallery/albums"):
            status, _, body = get(base, path)
            assert status == 401, (path, status, body)

        status, _, body = post(base, "/api/messages", b"{not-json")
        assert status == 400, (status, body)

        status, _, body = post(base, "/api/stripe/webhook", b"{}")
        assert status == 400, (status, body)

        print("SECURITY HTTP REGRESSION TEST PASS")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
