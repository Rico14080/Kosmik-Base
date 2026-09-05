#!/usr/bin/env python3
"""Small production smoke test for a running Kosmik Circles backend.
Usage: python backend/tests/smoke_test.py [base_url]
"""
from __future__ import annotations
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")

def request(path: str, method: str = "GET", body: object | None = None, headers: dict | None = None):
    raw = None if body is None else json.dumps(body).encode()
    h = {"Accept": "application/json"}
    if body is not None:
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(BASE + path, data=raw, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
            try:
                return r.status, r.headers, json.loads(data.decode())
            except Exception:
                return r.status, r.headers, data
    except urllib.error.HTTPError as e:
        data = e.read()
        try:
            data = json.loads(data.decode())
        except Exception:
            pass
        return e.code, e.headers, data

status, headers, health = request("/api/health")
assert status == 200 and health.get("ok") is True
status, _, content = request("/api/content")
assert status == 200
payload = content.get("content", {})
for key in ("home", "pages", "shop", "gallery", "live", "contact", "us", "visuals", "siteText"):
    assert key in payload, key
for header in ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy", "Content-Security-Policy"):
    assert headers.get(header), header
for path in ("/backend/server.py", "/backend/data/kosmik.db", "/backend/.env"):
    assert request(path)[0] == 404, path
print(f"SMOKE PASS — {BASE} — backend {health.get('version')}")
