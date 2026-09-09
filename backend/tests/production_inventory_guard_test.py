#!/usr/bin/env python3
"""Production-gate inventory invariants.

These tests intentionally encode the production contract: stock=0 means unavailable,
and non-positive quantities are invalid. They are separate from the historical Phase 1
regression suite so a regression cannot be hidden by changing the older test semantics.
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


def product(stock: int) -> int:
    c = server.db()
    stamp = server.now()
    c.execute("DELETE FROM products")
    c.execute(
        "INSERT INTO products(name,meta,description,price_cents,image,alt,stock,reserved_stock,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("Production Test", "", "", 1000, "", "", stock, 0, 1, stamp, stamp),
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


def main():
    setup()
    pid = product(0)
    must_reject([{"productId": pid, "name": "Production Test", "quantity": 1, "priceCents": 1000}])

    pid = product(5)
    for quantity in (0, -1, -99):
        must_reject([{"productId": pid, "name": "Production Test", "quantity": quantity, "priceCents": 1000}])

    print("PRODUCTION INVENTORY GUARD PASS")


if __name__ == "__main__":
    main()
