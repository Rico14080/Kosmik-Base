#!/usr/bin/env python3
"""Phase 1 checkout/inventory regression tests."""
from __future__ import annotations

import json
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402


def setup_module():
    tmp = Path(tempfile.mkdtemp(prefix="kosmik-phase1-"))
    server.DATA = tmp / "data"
    server.UPLOADS = tmp / "uploads"
    server.MEDIA_DIR = tmp / "media"
    server.DB = server.DATA / "test.sqlite3"
    server.init_db()


def fresh_product(stock: int = 5):
    c = server.db()
    c.execute("DELETE FROM products")
    stamp = server.now()
    c.execute(
        "INSERT INTO products(name,meta,description,price_cents,image,alt,stock,reserved_stock,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("Test Product", "", "", 1000, "", "", stock, 0, 1, stamp, stamp),
    )
    c.commit()
    pid = c.execute("SELECT id FROM products WHERE name='Test Product'").fetchone()[0]
    c.close()
    return pid


def test_atomic_concurrent_reservation():
    pid = fresh_product(5)
    outcomes = []
    lock = threading.Lock()

    def worker(order_id: str):
        c = server.db()
        try:
            server.reserve_order_stock(c, [{"productId": pid, "name": "Test Product", "quantity": 3, "priceCents": 1000}])
            expiry = server.reservation_expiry()
            c.execute(
                "INSERT INTO orders(id,email,total_cents,status,payment_status,shipping_status,items_json,stock_reserved,reservation_expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (order_id, "test@example.com", 3000, "NEW", "UNPAID", "UNFULFILLED", json.dumps([{"productId": pid, "quantity": 3}]), 3, expiry, server.now(), server.now()),
            )
            c.commit()
            result = "success"
        except Exception:
            c.rollback()
            result = "fail"
        finally:
            c.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker, args=(f"T{i}",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["fail", "success"], outcomes

    c = server.db()
    row = c.execute("SELECT stock,reserved_stock FROM products WHERE id=?", (pid,)).fetchone()
    assert row["stock"] == 5 and row["reserved_stock"] == 3
    order = c.execute("SELECT id FROM orders WHERE stock_reserved=3").fetchone()
    assert order is not None
    ok = server.apply_paid_order(c, order["id"], "cs_test")
    c.commit()
    assert ok is True
    row = c.execute("SELECT stock,reserved_stock FROM products WHERE id=?", (pid,)).fetchone()
    assert row["stock"] == 2 and row["reserved_stock"] == 0
    paid = c.execute("SELECT status,payment_status,stock_applied,stock_reserved FROM orders WHERE id=?", (order["id"],)).fetchone()
    assert tuple(paid) == ("PAID", "PAID", 1, 0)
    c.close()


def test_expired_reservation_is_released():
    pid = fresh_product(2)
    c = server.db()
    expiry = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    c.execute(
        "INSERT INTO orders(id,email,total_cents,status,payment_status,shipping_status,items_json,stock_reserved,reservation_expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("EXPIRED", "test@example.com", 1000, "NEW", "UNPAID", "UNFULFILLED", json.dumps([{"productId": pid, "quantity": 1}]), 1, expiry, server.now(), server.now()),
    )
    c.execute("UPDATE products SET reserved_stock=1 WHERE id=?", (pid,))
    released = server.release_expired_reservations(c)
    c.commit()
    assert released == 1
    product = c.execute("SELECT reserved_stock FROM products WHERE id=?", (pid,)).fetchone()
    order = c.execute("SELECT status,stock_reserved,reservation_expires_at FROM orders WHERE id='EXPIRED'").fetchone()
    assert product["reserved_stock"] == 0
    # Expiry releases the inventory reservation; order status remains NEW until an explicit cancellation.
    assert order["status"] == "NEW" and order["stock_reserved"] == 0 and order["reservation_expires_at"] is None
    c.close()


if __name__ == "__main__":
    setup_module()
    test_atomic_concurrent_reservation()
    test_expired_reservation_is_released()
    print("PHASE1 CHECKOUT TEST PASS")
