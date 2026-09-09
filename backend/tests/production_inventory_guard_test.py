#!/usr/bin/env python3
"""Production-gate inventory invariants.

These tests encode the production contract: stock=0 means unavailable,
quantities must be integers in the 1..99 range, and reservations may never
exceed the currently available finite stock.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402


def setup():
    tmp = Path(tempfile.mkdtemp(prefix="kosmik-production-inventory-"))
    server.DATA = tmp / "data"
    server.UPLOADS = tmp / "uploads"
    server.MEDIA_DIR = tmp / "media"
    server.DB = server.DATA / "test.sqlite3"
    server.init_db()


def product(stock: int, reserved: int = 0) -> int:
    c = server.db()
    stamp = server.now()
    c.execute("DELETE FROM products")
    c.execute(
        "INSERT INTO products(name,meta,description,price_cents,image,alt,stock,reserved_stock,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("Production Test", "", "", 1000, "", "", stock, reserved, 1, stamp, stamp),
    )
    c.commit()
    pid = int(c.execute("SELECT id FROM products WHERE name='Production Test'").fetchone()[0])
    c.close()
    return pid


def must_reject(items):
    c = server.db()
    try:
        server.reserve_order_stock(c, items)
    except (ValueError, RuntimeError):
        c.rollback()
        return
    finally:
        c.close()
    raise AssertionError("Reservation unexpectedly succeeded")


def must_reserve(items, expected_reserved: int):
    c = server.db()
    try:
        server.reserve_order_stock(c, items)
        row = c.execute("SELECT reserved_stock FROM products WHERE id=?", (items[0]["productId"],)).fetchone()
        assert int(row[0]) == expected_reserved, (row[0], expected_reserved)
        c.rollback()
    finally:
        c.close()


def main():
    setup()

    # Zero stock is always unavailable.
    pid = product(0)
    must_reject([{"productId": pid, "name": "Production Test", "quantity": 1, "priceCents": 1000}])

    # Non-positive and out-of-contract quantities are rejected.
    pid = product(5)
    for quantity in (0, -1, -99, 100):
        must_reject([{"productId": pid, "name": "Production Test", "quantity": quantity, "priceCents": 1000}])

    # Exact stock and one-unit stock boundaries are valid.
    pid = product(1)
    must_reserve([{"productId": pid, "name": "Production Test", "quantity": 1, "priceCents": 1000}], 1)

    pid = product(5)
    must_reserve([{"productId": pid, "name": "Production Test", "quantity": 5, "priceCents": 1000}], 5)

    # A reservation cannot consume units already reserved by another order.
    pid = product(5, reserved=4)
    must_reject([{"productId": pid, "name": "Production Test", "quantity": 2, "priceCents": 1000}])
    must_reserve([{"productId": pid, "name": "Production Test", "quantity": 1, "priceCents": 1000}], 5)

    print("PRODUCTION INVENTORY GUARD PASS")


if __name__ == "__main__":
    main()
