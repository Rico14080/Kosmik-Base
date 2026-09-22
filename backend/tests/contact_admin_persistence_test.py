#!/usr/bin/env python3
"""End-to-end Contact/Admin persistence checks for the local Kosmik backend."""
from __future__ import annotations

import base64
import http.cookiejar
import json
from pathlib import Path
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def request(opener, base: str, path: str, *, method: str = "GET", json_body=None, raw_body: bytes | None = None, headers=None):
    request_headers = {"Accept": "application/json"}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        request_headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body
    if headers:
        request_headers.update(headers)
    req = Request(base + path, data=data, headers=request_headers, method=method)
    try:
        with opener.open(req, timeout=5) as response:
            body = response.read()
            try:
                parsed = json.loads(body.decode())
            except Exception:
                parsed = body
            return response.status, dict(response.headers), parsed
    except HTTPError as exc:
        body = exc.read()
        try:
            parsed = json.loads(body.decode())
        except Exception:
            parsed = body
        return exc.code, dict(exc.headers), parsed


def start_server():
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread, f"http://127.0.0.1:{httpd.server_address[1]}"


def stop_server(httpd, thread) -> None:
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


def main() -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="kosmik-contact-admin-"))
    server.DATA = temp_root / "data"
    server.UPLOADS = temp_root / "uploads"
    server.DB = server.DATA / "kosmik-test.sqlite3"
    server.ADMIN_PASSWORD = "step4-test-password"
    server.PUBLIC_BASE_URL = ""
    server.SMTP_HOST = ""
    server.SMTP_FROM = ""
    server.COMMERCE_ENABLED = False
    server.RATE_BUCKETS.clear()
    server.DATA.mkdir(parents=True, exist_ok=True)
    server.UPLOADS.mkdir(parents=True, exist_ok=True)
    server.init_db()

    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    httpd, thread, base = start_server()

    try:
        status, _, result = request(
            opener,
            base,
            "/api/messages",
            method="POST",
            json_body={
                "name": "Step 4 Contact",
                "email": "step4@example.com",
                "message": "Contact message persistence check",
                "website": "",
            },
        )
        assert status == 202, (status, result)
        assert result == {"ok": True, "delivery": "saved"}, result

        status, _, login = request(
            opener,
            base,
            "/api/admin/login",
            method="POST",
            json_body={"password": "step4-test-password"},
        )
        assert status == 200, (status, login)
        csrf = login.get("csrfToken")
        assert isinstance(csrf, str) and csrf, login

        status, _, messages = request(opener, base, "/api/admin/messages")
        assert status == 200, (status, messages)
        assert any(item["email"] == "step4@example.com" for item in messages["messages"]), messages

        status, _, admin_content = request(opener, base, "/api/admin/content")
        assert status == 200, (status, admin_content)
        contact = dict(admin_content["content"]["contact"])
        contact["formIntro"] = "Step 4 persistence check"
        status, _, saved = request(
            opener,
            base,
            "/api/admin/content",
            method="POST",
            json_body={"section": "contact", "value": contact, "version": admin_content["version"]},
            headers={"X-CSRF-Token": csrf},
        )
        assert status == 200, (status, saved)
        assert saved["content"]["contact"]["formIntro"] == "Step 4 persistence check", saved

        status, _, upload = request(
            opener,
            base,
            "/api/admin/upload",
            method="POST",
            raw_body=PNG_1X1,
            headers={"Content-Type": "image/png", "X-CSRF-Token": csrf},
        )
        assert status == 201, (status, upload)
        uploaded_url = upload.get("url")
        assert isinstance(uploaded_url, str) and uploaded_url.startswith("/backend/uploads/"), upload
        assert (server.UPLOADS / uploaded_url.rsplit("/", 1)[-1]).is_file(), uploaded_url
    finally:
        stop_server(httpd, thread)

    # Simulate a real backend restart against the same persistent DB and upload directory.
    server.init_db()
    httpd, thread, base = start_server()
    try:
        status, _, content = request(opener, base, "/api/content")
        assert status == 200, (status, content)
        assert content["contact"]["formIntro"] == "Step 4 persistence check", content["contact"]

        status, _, messages = request(opener, base, "/api/admin/messages")
        assert status == 200, (status, messages)
        assert any(item["email"] == "step4@example.com" for item in messages["messages"]), messages

        status, _, _ = request(opener, base, uploaded_url)
        assert status == 200, (status, uploaded_url)
    finally:
        stop_server(httpd, thread)

    print("CONTACT / ADMIN / PERSISTENCE TEST PASS")


if __name__ == "__main__":
    main()
