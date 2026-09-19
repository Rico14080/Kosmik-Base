#!/usr/bin/env python3
"""HTTP-level regression checks for baseline security controls."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
import http.client
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
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert "frame-ancestors 'self'" in headers.get("Content-Security-Policy", "")
        assert "object-src 'none'" in headers.get("Content-Security-Policy", "")

        status, _, _ = get(base, "/backend/server.py")
        assert status == 404, status
        status, _, _ = get(base, "/backend/.env")
        assert status == 404, status

        assert "script-src 'self';" in headers.get('Content-Security-Policy','')
        for path in ("/api/admin/orders", "/api/admin/messages", "/api/admin/stats"):
            status, _, body = get(base, path)
            assert status == 401, (path, status, body)

        status, _, body = post(base, "/api/messages", b"{not-json")
        assert status == 400, (status, body)

        status, _, body = post(base, "/api/stripe/webhook", b"{}")
        assert status == 503, (status, body)

        for path in ('/backend/server.py','/backend/data/test.sqlite3','/backend/backups/test.zip','/.env','/.git/config','/README.md','/backend/tests/security_http_regression_test.py','/%62ackend/server.py','/backend/%64ata/test.sqlite3','/%2eenv','/../backend/server.py','/%2e%2e/backend/server.py','/%252e%252e/backend/server.py','/backend%5cserver.py','/gallery.html','/api/gallery/albums','/api/admin/gallery/albums'):
            for method in ('GET','HEAD'):
                conn=http.client.HTTPConnection('127.0.0.1',httpd.server_address[1],timeout=5)
                conn.request(method,path);response=conn.getresponse();assert response.status==404,(method,path,response.status)
                body=response.read();assert method!='HEAD' or body==b'';conn.close()
        for payload in (b'[]',b'null',b'"string"',b'123'):
            assert post(base,'/api/messages',payload)[0]==400
        assert post(base,'/api/messages',b'{}','text/plain')[0]==415
        for path in ('/api/messages',):
            conn=http.client.HTTPConnection('127.0.0.1',httpd.server_address[1],timeout=5)
            conn.request('POST',path,body=b'',headers={'Content-Length':str(server.MAX_BODY+1),'Content-Type':'application/json'})
            response=conn.getresponse();assert response.status==413;response.read();conn.close()
        conn=http.client.HTTPConnection('127.0.0.1',httpd.server_address[1],timeout=5)
        conn.request('POST','/api/stripe/webhook',body=b'',headers={'Content-Length':str(server.MAX_BODY+1),'Content-Type':'application/json'})
        response=conn.getresponse();assert response.status==503;response.read();conn.close()

        print("SECURITY HTTP REGRESSION TEST PASS")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()

