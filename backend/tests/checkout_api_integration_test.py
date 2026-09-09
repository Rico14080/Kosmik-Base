#!/usr/bin/env python3
"""HTTP-level checkout flow tests with a temporary SQLite database."""
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


def setup_test_db() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="kosmik-checkout-api-"))
    server.DATA = tmp / "data"
    server.UPLOADS = tmp / "uploads"
    server.MEDIA_DIR = tmp / "media"
    server.DB = server.DATA / "test.sqlite3"
    server.init_db()
    c = server.db()
    stamp = server.now()
    c.execute(
        "INSERT INTO products(name,meta,description,price_cents,image,alt,stock,reserved_stock,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("Integration Product", "", "", 1250, "", "", 2, 0, 1, stamp, stamp),
    )
    c.commit()
    c.close()


def request_json(base: str, payload: dict) -> tuple[int, dict]:
    req = Request(
        f"{base}/api/checkout",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def get_status(base: str, order_id: str, status_token: str | None = None) -> tuple[int, dict]:
    url = f"{base}/api/orders/status?id={order_id}"
    if status_token is not None:
        url += f"&token={status_token}"
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main() -> None:
    setup_test_db()
    original_stripe = server.create_stripe_checkout
    server.create_stripe_checkout = lambda *_args, **_kwargs: None
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        status, body = request_json(
            base,
            {
                "email": "buyer@example.com",
                "customer": {"name": "Test Buyer", "country": "Italy"},
                "items": [{"name": "Integration Product", "price": "€ 9999", "quantity": 1}],
            },
        )
        assert status == 201, (status, body)
        assert body["ok"] is True and body["paymentRequired"] is False
        assert body["totalCents"] == 1250, body
        order_id = body["orderId"]
        status_token = body["statusToken"]
        assert order_id.startswith("KC-") and len(order_id) >= 18, order_id
        assert isinstance(status_token, str) and len(status_token) >= 32, status_token

        c = server.db()
        product = c.execute("SELECT stock,reserved_stock FROM products WHERE name=?", ("Integration Product",)).fetchone()
        order = c.execute("SELECT status,payment_status,stock_reserved,status_token FROM orders WHERE id=?", (order_id,)).fetchone()
        c.close()
        assert tuple(product) == (2, 0), tuple(product)
        assert tuple(order[:3]) == ("NEW", "UNPAID", 0), tuple(order)
        assert order["status_token"] == status_token

        status, body = get_status(base, order_id)
        assert status == 400, (status, body)

        status, body = get_status(base, order_id, "wrong-token")
        assert status == 404, (status, body)

        status, body = get_status(base, order_id, status_token)
        assert status == 200, (status, body)
        assert body["orderId"] == order_id
        assert body["paymentStatus"] == "UNPAID"

        status, body = request_json(
            base,
            {
                "email": "buyer@example.com",
                "items": [{"name": "Integration Product", "quantity": 3}],
            },
        )
        assert status == 409 and "stock" in body["error"].lower(), (status, body)
    finally:
        server.create_stripe_checkout = original_stripe
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    print("CHECKOUT API INTEGRATION TEST PASS")


if __name__ == "__main__":
    main()
