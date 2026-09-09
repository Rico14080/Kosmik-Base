#!/usr/bin/env python3
"""Kosmik Circles production-oriented local backend V1.15.

Standard-library only. SQLite for persistence, optional Stripe Checkout and SMTP.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import smtplib
import sqlite3
import time
import threading
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
BACKEND = Path(__file__).resolve().parent
DATA = BACKEND / "data"
UPLOADS = BACKEND / "uploads"
MEDIA_DIR = BACKEND / "media"
DB = DATA / "kosmik.db"
HOST = os.getenv("KOSMIK_HOST", "127.0.0.1")
PORT = int(os.getenv("KOSMIK_PORT", "8080"))
ADMIN_USER = os.getenv("KOSMIK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KOSMIK_ADMIN_PASSWORD", "")
SESSION_TTL = 12 * 60 * 60
STOCK_RESERVATION_TTL = 30 * 60
MAX_BODY = 1_500_000
MAX_UPLOAD = 5 * 1024 * 1024
MAX_MEDIA_UPLOAD = 1024 * 1024 * 1024
API_VERSION = "1.15"
ORDER_STATUSES = {"NEW", "PAID", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "REFUNDED"}

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SITE_OWNER_EMAIL = os.getenv("SITE_OWNER_EMAIL", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1").strip().lower() not in {"0", "false", "no"}
RATE_LOCK = threading.Lock()
RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}

DEFAULT_CONTENT = {
    "home": {
        "eyebrow": "Independent objects / Est. 2024",
        "titleLineOne": "Made for",
        "titleLineTwo": "elsewhere.",
        "intro": "Small-batch goods for people who keep looking up. Wearable signals, useful artifacts, and a little cosmic noise.",
        "cta": "Enter the orbit",
        "heroImage": "https://images.unsplash.com/photo-1534791547706-5c292f749e1b?auto=format&fit=crop&w=1200&q=85",
        "heroAlt": "Orange light cutting through a dark concert atmosphere",
        "signalText": "new objects for old souls",
        "orbitLabelTop": "38° 11′ 52″ N",
        "orbitLabelBottom": "signal / 001",
        "heroIndex": "01 / 04",
        "sectionNumber": "[ 001 ]",
        "signalStripLabel": "Currently transmitting",
        "introEyebrow": "The short version",
        "introTitleLineOne": "Good things can",
        "introTitleLineTwo": "still feel unknown.",
        "introDescription": "Kosmik Circles is a design studio making limited-run pieces with a point of view. We work slowly, source carefully, and leave enough room for the weirdness to get in."
    },
    "pages": {
        "shop": {"eyebrow": "Available now / Dispatching worldwide", "titleLineOne": "Objects with", "titleLineTwo": "an orbit.", "note": "Four small-batch pieces. No restocks promised."},
        "gallery": {"eyebrow": "Visual archive / Field notes", "titleLineOne": "See the", "titleLineTwo": "signal.", "note": "Fragments from the orbit."},
        "live": {"eyebrow": "Transmission schedule / 2026", "titleLineOne": "Come", "titleLineTwo": "through.", "note": "Night flights, deep rooms, high frequencies."},
        "contact": {"eyebrow": "Open frequency / hello@kosmikcircles.com", "titleLineOne": "Send a", "titleLineTwo": "signal.", "note": ""},
        "us": {"eyebrow": "A very small studio", "titleLineOne": "We make", "titleLineTwo": "signals.", "note": ""},
        "cart": {"eyebrow": "Your selected objects", "titleLineOne": "Enter the", "titleLineTwo": "cart.", "note": "Leave your email and send the order signal."}
    },
    "ticker": {"text": "NEW TRANSMISSION SOON ✳ KOSMIK CIRCLES / SMALL BATCH / LIVE AUDIOVISUAL SIGNALS", "speed": 28, "fontSize": 11},
    "matrix": {"speed": 0.45},
    "gallery": [{"image": "", "alt": "", "caption": f"{i:03d} / Empty frequency"} for i in range(1, 6)],
    "contact": {
        "email": "hello@kosmikcircles.com",
        "instagram": "Instagram",
        "instagramUrl": "",
        "description": "Kosmik Circles offers live electronic music, audiovisual performances, DJ sets, and sound direction for clubs, festivals, brands, and private spaces. Tell us what you are building and we will shape the frequency with you.",
        "serviceTitleOne": "We create",
        "serviceTitleTwo": "signals.",
        "formIntro": "Start with an email. We answer within 2-3 Earth days."
    },
    "live": [
        {"date":"18.10.24","isoDate":"2024-10-18","location":"Milano, IT","venue":"Magazzini Generali / 23:00","signal":"Circles / 01","detail":"Full live set","action":"Tickets","ticketUrl":"","past":True},
        {"date":"02.11.24","isoDate":"2024-11-02","location":"Berlin, DE","venue":"Ritter Butzke / 00:30","signal":"Night Channel","detail":"2 hour live set","action":"Tickets","ticketUrl":"","past":True},
        {"date":"24.01.25","isoDate":"2025-01-24","location":"Lisboa, PT","venue":"Lux Frágil / 01:00","signal":"Outer Room","detail":"Live + visual show","action":"Tickets","ticketUrl":"","past":True},
        {"date":"31.08.24","isoDate":"2024-08-31","location":"Paris, FR","venue":"La Machine / 23:30","signal":"Soft Landing","detail":"Archive recording","action":"Archive","ticketUrl":"","past":True}
    ],
    "shop": [
        {"name": "Moon Phase Tee", "meta": "Heavy cotton / ink black", "description": "240 gsm organic cotton tee with a front orbit mark and relaxed fit.", "price": "€ 48", "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=85", "alt": "Black graphic t-shirt on a dark studio floor", "stock": 0},
        {"name": "Signal Cap", "meta": "Five-panel / orange mark", "description": "Adjustable five-panel cap with embroidered Kosmik Circles signal.", "price": "€ 36", "image": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=900&q=85", "alt": "Black cap lit with warm orange light", "stock": 0},
        {"name": "Red Planet Mug", "meta": "Stoneware / 330 ml", "description": "Hand-finished ceramic mug made for long nights and slow conversations.", "price": "€ 26", "image": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=85", "alt": "Ceramic mug on a minimal table", "stock": 0},
        {"name": "Field Notes 001", "meta": "Risograph print / A3", "description": "A numbered studio print mapping our first transmission into the night.", "price": "€ 18", "image": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=85", "alt": "Starry night sky above a dark horizon", "stock": 0}
    ],
    "us": {
        "sectionNumber": "[ 002 ]",
        "statement": "There is a lot of noise out there. We like the kind that means something.",
        "description": "Kosmik Circles started with two friends, a stack of old astronomy books, and a shared belief that everyday things deserve a little mystery. We make products in limited runs, with honest materials, and an unreasonable amount of attention.",
        "photo": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1000&q=85",
        "photoAlt": "Kosmik Circles studio",
        "studioLabel": "KC",
        "soundEyebrow": "The sound / Live frequency",
        "soundTitleLineOne": "Built for",
        "soundTitleLineTwo": "the room.",
        "soundDescription": "Our sound moves between hypnotic low-end, psychedelic textures, and long-form tension. These images are fragments from the places where the signal becomes physical.",
        "soundImages": [
            {"image": "https://images.unsplash.com/photo-1524365252-6f0b8f4e8f7a?auto=format&fit=crop&w=1000&q=85", "alt": "DJ performing under red stage lights", "caption": "01 / Low light"},
            {"image": "/WhatsApp Image 2026-08-11 at 00.52.13 (13).webp", "alt": "Abstract concert lights in a dark room", "caption": "02 / Deep signal"},
            {"image": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1000&q=85", "alt": "Crowd moving beneath concert lights", "caption": "03 / Shared frequency"}
        ],
        "valuesEyebrow": "Our coordinates",
        "valuesTitleLineOne": "Slow things.",
        "valuesTitleLineTwo": "Strange things.",
        "valuesTitleLineThree": "Good things.",
        "valuesDescription": "Designed in Milan. Made with people we know. Packed by hand. Every object has a trace of where it came from."
    },
    "visuals": {"liveBackgroundImage": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=85"},
    "siteText": {
        "skipToContent": "Skip to content",
        "liveUpdates": "Live updates",
        "nav": {"home": "Home", "shop": "Shop", "us": "Us", "live": "Live", "gallery": "Gallery", "contact": "Contact", "bag": "Bag", "cart": "Cart"},
        "home": {"currentlyTransmitting": "Currently transmitting"},
        "shop": {"addToCart": "Add to cart"},
        "gallery": {"emptyImage": "Drop image here"},
        "live": {"date": "Date", "location": "Location", "signal": "Signal", "noTicket": "Tickets"},
        "contact": {"name": "Your name", "email": "Your email", "message": "Your message", "submit": "Transmit"},
        "cart": {"yourName": "Your name", "yourEmail": "Your email", "phone": "Phone", "address": "Address", "city": "City", "postcode": "Postcode", "country": "Country", "sendOrder": "Send order", "remove": "Remove", "empty": "Your cart is orbiting empty.", "sending": "Sending order…", "quantity": "quantity", "total": "Total"},
        "footer": {"tagline": "Made on Earth, for now", "homeCta": "Say hello", "shopCta": "Say hello", "galleryCta": "Send a signal", "liveCta": "Book a transmission", "usCta": "Say hello", "contactCta": "Browse objects", "cartCta": "Back to shop"}
    }
}


def deep_merge(base: object, saved: object) -> object:
    if isinstance(base, dict):
        result = copy.deepcopy(base)
        if isinstance(saved, dict):
            for key, value in saved.items():
                result[key] = deep_merge(result.get(key), value) if key in result else copy.deepcopy(value)
        return result
    if isinstance(base, list):
        return copy.deepcopy(saved) if isinstance(saved, list) else copy.deepcopy(base)
    return copy.deepcopy(saved) if saved is not None else copy.deepcopy(base)


def merge_content_defaults(saved: dict | None) -> dict:
    return deep_merge(DEFAULT_CONTENT, saved if isinstance(saved, dict) else {})


def normalize_asset_path(value: object) -> str:
    s = str(value or '').strip()
    if s.startswith('backend/uploads/'):
        return '/' + s
    return s


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def price_cents(value: object) -> int:
    s = re.sub(r"[^0-9,.]", "", str(value or "0"))
    if not s:
        return 0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return max(0, round(float(s) * 100))
    except ValueError:
        return 0


def new_status_token() -> str:
    return secrets.token_urlsafe(32)


def init_db() -> None:
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS site_content (id INTEGER PRIMARY KEY CHECK(id=1), content TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, meta TEXT, description TEXT, price_cents INTEGER NOT NULL DEFAULT 0, image TEXT, alt TEXT, stock INTEGER NOT NULL DEFAULT 0, reserved_stock INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, iso_date TEXT, location TEXT, venue TEXT, signal TEXT, detail TEXT, action TEXT, ticket_url TEXT, past INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS gallery (id INTEGER PRIMARY KEY AUTOINCREMENT, image TEXT, alt TEXT, caption TEXT, sort_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS gallery_albums (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE, date TEXT, location TEXT, venue TEXT, description TEXT, cover_image TEXT, sort_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS gallery_media (id INTEGER PRIMARY KEY AUTOINCREMENT, album_id INTEGER NOT NULL, original_name TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE, media_type TEXT NOT NULL, mime_type TEXT NOT NULL, size_bytes INTEGER NOT NULL DEFAULT 0, sort_order INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, FOREIGN KEY(album_id) REFERENCES gallery_albums(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT NOT NULL, phone TEXT, address TEXT, city TEXT, postcode TEXT, country TEXT, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, customer_id INTEGER, email TEXT NOT NULL, total_cents INTEGER NOT NULL, status TEXT NOT NULL, payment_status TEXT NOT NULL, shipping_status TEXT NOT NULL, items_json TEXT NOT NULL, stripe_session_id TEXT, stock_applied INTEGER NOT NULL DEFAULT 0, stock_reserved INTEGER NOT NULL DEFAULT 0, reservation_expires_at TEXT, status_token TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new', created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
    """)
    pcols = {r[1] for r in c.execute("PRAGMA table_info(products)").fetchall()}
    if "reserved_stock" not in pcols:
        c.execute("ALTER TABLE products ADD COLUMN reserved_stock INTEGER NOT NULL DEFAULT 0")
    ocols = {r[1] for r in c.execute("PRAGMA table_info(orders)").fetchall()}
    if "stripe_session_id" not in ocols:
        c.execute("ALTER TABLE orders ADD COLUMN stripe_session_id TEXT")
    if "stock_applied" not in ocols:
        c.execute("ALTER TABLE orders ADD COLUMN stock_applied INTEGER NOT NULL DEFAULT 0")
    if "stock_reserved" not in ocols:
        c.execute("ALTER TABLE orders ADD COLUMN stock_reserved INTEGER NOT NULL DEFAULT 0")
    if "reservation_expires_at" not in ocols:
        c.execute("ALTER TABLE orders ADD COLUMN reservation_expires_at TEXT")
    if "status_token" not in ocols:
        c.execute("ALTER TABLE orders ADD COLUMN status_token TEXT")
    legacy_status_rows = c.execute("SELECT id FROM orders WHERE status_token IS NULL OR status_token='' ").fetchall()
    for r in legacy_status_rows:
        c.execute("UPDATE orders SET status_token=? WHERE id=?", (new_status_token(), r["id"]))
    row = c.execute("SELECT content FROM site_content WHERE id=1").fetchone()
    if not row:
        c.execute("INSERT INTO site_content VALUES(1,?,?)", (json.dumps(DEFAULT_CONTENT, ensure_ascii=False), now()))
    else:
        saved_content = json.loads(row["content"])
        legacy_schema = "siteText" not in saved_content and "visuals" not in saved_content
        merged = merge_content_defaults(saved_content)
        if legacy_schema and not saved_content.get("live"):
            merged["live"] = copy.deepcopy(DEFAULT_CONTENT["live"])
        c.execute("UPDATE site_content SET content=?,updated_at=? WHERE id=1", (json.dumps(merged, ensure_ascii=False), now()))
    if c.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"] == 0:
        stamp = now()
        for p in DEFAULT_CONTENT["shop"]:
            c.execute("INSERT INTO products(name,meta,description,price_cents,image,alt,stock,reserved_stock,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (p["name"], p["meta"], p["description"], price_cents(p["price"]), p["image"], p["alt"], 0, 0, 1, stamp, stamp))
    release_expired_reservations(c)
    c.commit()
    c.close()


def content_from_db(c: sqlite3.Connection) -> dict:
    row = c.execute("SELECT content FROM site_content WHERE id=1").fetchone()
    return json.loads(row["content"])


def persist_image(value: object, prefix: str = "image") -> str:
    value = str(value or "").strip()
    m = re.match(r"^data:image/(png|jpe?g|webp|gif);base64,(.+)$", value, re.I)
    if not m:
        if value.startswith(("/backend/uploads/", "https://")):
            return value[:4000]
        return value[:4000]
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except Exception:
        return ""
    if len(raw) > MAX_UPLOAD:
        return ""
    ext = "jpg" if m.group(1).lower() in {"jpg", "jpeg"} else m.group(1).lower()
    name = f"{prefix}-{secrets.token_hex(8)}.{ext}"
    (UPLOADS / name).write_bytes(raw)
    return f"/backend/uploads/{name}"


def normalize_content_images(content: dict) -> dict:
    content = json.loads(json.dumps(content, ensure_ascii=False))
    content = merge_content_defaults(content)
    content.setdefault("home", {})["heroImage"] = persist_image(normalize_asset_path(content["home"].get("heroImage", "")), "hero")
    content.setdefault("us", {})["photo"] = persist_image(normalize_asset_path(content["us"].get("photo", "")), "studio")
    for item in content.get("us", {}).get("soundImages", []):
        item["image"] = persist_image(normalize_asset_path(item.get("image", "")), "sound")
    for p in content.get("shop", []):
        p["image"] = persist_image(normalize_asset_path(p.get("image", "")), "product")
    for g in content.get("gallery", []):
        g["image"] = persist_image(normalize_asset_path(g.get("image", "")), "gallery")
    content.setdefault("visuals", {})["liveBackgroundImage"] = persist_image(normalize_asset_path(content.get("visuals", {}).get("liveBackgroundImage", "")), "live-bg")
    return content


def local_upload_urls(content: dict) -> set[str]:
    urls: set[str] = set()
    def add(value: object) -> None:
        s = normalize_asset_path(value)
        if s.startswith("/backend/uploads/"):
            urls.add(s)
    add(content.get("home", {}).get("heroImage", ""))
    add(content.get("us", {}).get("photo", ""))
    for item in content.get("us", {}).get("soundImages", []):
        add(item.get("image", ""))
    for item in content.get("shop", []):
        add(item.get("image", ""))
    for item in content.get("gallery", []):
        add(item.get("image", ""))
    add(content.get("visuals", {}).get("liveBackgroundImage", ""))
    return urls


def _safe_upload_path(url: str) -> Path | None:
    name = Path(url).name
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:png|jpe?g|webp|gif)", name, re.I):
        return None
    target = (UPLOADS / name).resolve()
    try:
        target.relative_to(UPLOADS.resolve())
    except ValueError:
        return None
    return target


def remove_orphaned_uploads(old_content: dict, new_content: dict) -> None:
    old_urls = local_upload_urls(old_content)
    new_urls = local_upload_urls(new_content)
    for url in old_urls - new_urls:
        target = _safe_upload_path(url)
        if target:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass


def prune_unreferenced_uploads(content: dict) -> None:
    refs = local_upload_urls(content)
    try:
        c = db()
        refs.update(str(r[0]) for r in c.execute("SELECT cover_image FROM gallery_albums WHERE cover_image LIKE '/backend/uploads/%'").fetchall() if r[0])
        c.close()
    except Exception:
        pass
    for path in UPLOADS.iterdir():
        if not path.is_file() or path.name.startswith('.'):
            continue
        url = f"/backend/uploads/{path.name}"
        if url in refs:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:png|jpe?g|webp|gif)", path.name, re.I):
            continue
        try:
            path.unlink()
        except OSError:
            pass


def save_content(c: sqlite3.Connection, content: dict) -> dict:
    previous = merge_content_defaults(content_from_db(c))
    content = normalize_content_images(content)
    stamp = now()
    existing_rows = c.execute("SELECT id,name,stock,reserved_stock,created_at FROM products").fetchall()
    existing_by_name = {r["name"]: r for r in existing_rows}
    active_names = set()
    c.execute("UPDATE site_content SET content=?,updated_at=? WHERE id=1", (json.dumps(content, ensure_ascii=False), stamp))
    for p in content.get("shop", []):
        name = str(p.get("name", "")).strip()[:160]
        if not name:
            continue
        active_names.add(name)
        old = existing_by_name.get(name)
        requested_stock = p.get("stock")
        try:
            stock = int(requested_stock)
        except (TypeError, ValueError):
            stock = int(old["stock"] if old else 0)
        stock = max(0, stock)
        reserved = int(old["reserved_stock"] or 0) if old else 0
        if stock > 0 and stock < reserved:
            raise ValueError(f"Stock for {name} cannot be lower than reserved quantity ({reserved}).")
        values = (str(p.get("meta", ""))[:200], str(p.get("description", ""))[:2000], price_cents(p.get("price")), str(p.get("image", ""))[:4000], str(p.get("alt", ""))[:300], stock, stamp)
        if old:
            c.execute("UPDATE products SET meta=?,description=?,price_cents=?,image=?,alt=?,stock=?,active=1,updated_at=? WHERE id=?", (*values, old["id"]))
        else:
            c.execute("INSERT INTO products(name,meta,description,price_cents,image,alt,stock,reserved_stock,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (name, *values, 0, 1, stamp))
    for old in existing_rows:
        if old["name"] not in active_names:
            c.execute("UPDATE products SET active=0,updated_at=? WHERE id=?", (stamp, old["id"]))
    c.execute("DELETE FROM events")
    for e in content.get("live", []):
        c.execute("INSERT INTO events(date,iso_date,location,venue,signal,detail,action,ticket_url,past,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (str(e.get("date", ""))[:30], str(e.get("isoDate", ""))[:20], str(e.get("location", ""))[:160], str(e.get("venue", ""))[:200], str(e.get("signal", ""))[:160], str(e.get("detail", ""))[:500], str(e.get("action", "Tickets"))[:80], str(e.get("ticketUrl", ""))[:2000], 1 if e.get("past") else 0, stamp, stamp))
    c.execute("DELETE FROM gallery")
    for i, g in enumerate(content.get("gallery", [])):
        c.execute("INSERT INTO gallery(image,alt,caption,sort_order,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (str(g.get("image", ""))[:4000], str(g.get("alt", ""))[:300], str(g.get("caption", ""))[:500], i, 1, stamp, stamp))
    c.commit()
    remove_orphaned_uploads(previous, content)
    prune_unreferenced_uploads(content)
    return content


def release_expired_reservations(c: sqlite3.Connection) -> int:
    now_dt = datetime.now(timezone.utc)
    rows = c.execute("SELECT id,items_json,stock_reserved,reservation_expires_at,status FROM orders WHERE stock_reserved>0 AND reservation_expires_at IS NOT NULL AND reservation_expires_at<?", (now_dt.isoformat(),)).fetchall()
    released = 0
    for row in rows:
        try:
            items = json.loads(row["items_json"])
        except Exception:
            items = []
        for item in items:
            qty = max(0, int(item.get("quantity", 0)))
            if qty <= 0:
                continue
            c.execute("UPDATE products SET reserved_stock=MAX(0,reserved_stock-?),updated_at=? WHERE id=?", (qty, now(), int(item.get("productId", 0))))
        c.execute("UPDATE orders SET stock_reserved=0,reservation_expires_at=NULL,updated_at=? WHERE id=?", (now(), row["id"]))
        released += 1
    return released


def reservation_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=STOCK_RESERVATION_TTL)).isoformat()


def reserve_order_stock(c: sqlite3.Connection, items: list[dict]) -> str:
    c.execute("BEGIN IMMEDIATE")
    release_expired_reservations(c)
    for item in items:
        product = c.execute("SELECT id,stock,reserved_stock FROM products WHERE id=? AND active=1", (int(item["productId"]),)).fetchone()
        if not product:
            raise ValueError(f"Product unavailable: {item['name']}")
        stock = int(product["stock"])
        reserved = int(product["reserved_stock"] or 0)
        qty = int(item["quantity"])
        if qty <= 0 or qty > 99:
            raise ValueError(f"Invalid quantity: {item['name']}")
        if stock <= 0:
            raise ValueError(f"Product out of stock: {item['name']}")
        if qty > max(0, stock - reserved):
            raise RuntimeError(f"Insufficient stock: {item['name']}")
    for item in items:
        c.execute("UPDATE products SET reserved_stock=reserved_stock+?,updated_at=? WHERE id=?", (int(item["quantity"]), now(), int(item["productId"])))
    return reservation_expiry()


def release_order_reservation(c: sqlite3.Connection, order_id: str) -> bool:
    row = c.execute("SELECT items_json,stock_reserved FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row or int(row["stock_reserved"] or 0) <= 0:
        return False
    try:
        items = json.loads(row["items_json"])
    except Exception:
        items = []
    for item in items:
        qty = max(0, int(item.get("quantity", 0)))
        if qty <= 0:
            continue
        c.execute("UPDATE products SET reserved_stock=MAX(0,reserved_stock-?),updated_at=? WHERE id=?", (qty, now(), int(item.get("productId", 0))))
    c.execute("UPDATE orders SET stock_reserved=0,reservation_expires_at=NULL,updated_at=? WHERE id=?", (now(), order_id))
    return True


def gallery_slug(title: str, album_id: int | None = None) -> str:
    base = re.sub(r'[^a-z0-9]+', '-', str(title or '').strip().lower()).strip('-')[:80] or 'night-archive'
    return f'{base}-{album_id}' if album_id else base

def media_record(c: sqlite3.Connection, row: sqlite3.Row) -> dict:
    mid=int(row['id'])
    return {'id':mid,'albumId':int(row['album_id']),'originalName':row['original_name'],'mediaType':row['media_type'],'mimeType':row['mime_type'],'sizeBytes':int(row['size_bytes']),'mediaUrl':f'/backend/media/{mid}','downloadUrl':f'/api/gallery/media/{mid}/download'}

def album_record(c: sqlite3.Connection, row: sqlite3.Row, include_media: bool=False) -> dict:
    aid=int(row['id'])
    out={'id':aid,'title':row['title'],'date':row['date'] or '','location':row['location'] or '','venue':row['venue'] or '','description':row['description'] or '','coverImage':row['cover_image'] or '','sortOrder':int(row['sort_order']),'mediaCount':int(c.execute('SELECT COUNT(*) FROM gallery_media WHERE album_id=? AND active=1',(aid,)).fetchone()[0])}
    if include_media:
        out['media']=[media_record(c,r) for r in c.execute('SELECT * FROM gallery_media WHERE album_id=? AND active=1 ORDER BY sort_order,id',(aid,))]
    return out

def list_gallery_albums(c: sqlite3.Connection, public: bool=True) -> list[dict]:
    where='WHERE active=1' if public else ''
    rows=c.execute(f'SELECT * FROM gallery_albums {where} ORDER BY sort_order,id DESC').fetchall()
    return [album_record(c,r,include_media=not public) for r in rows]

def save_gallery_album(c: sqlite3.Connection, album: dict) -> dict:
    stamp=now(); aid=int(album.get('id') or 0); title=str(album.get('title') or 'Untitled night')[:180].strip() or 'Untitled night'
    date=str(album.get('date') or '')[:40]; location=str(album.get('location') or '')[:160]; venue=str(album.get('venue') or '')[:200]; description=str(album.get('description') or '')[:2000]
    cover=normalize_asset_path(album.get('coverImage',''))[:4000]
    if aid:
        old=c.execute('SELECT * FROM gallery_albums WHERE id=?',(aid,)).fetchone()
        if not old: raise ValueError('Archive folder not found')
        title=title or old['title']; cover=cover or (old['cover_image'] or '')
        c.execute('UPDATE gallery_albums SET title=?,slug=?,date=?,location=?,venue=?,description=?,cover_image=?,updated_at=? WHERE id=?',(title,gallery_slug(title,aid),date,location,venue,description,cover,stamp,aid))
    else:
        c.execute('INSERT INTO gallery_albums(title,slug,date,location,venue,description,cover_image,sort_order,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(title,'',date,location,venue,description,cover,0,1,stamp,stamp));aid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        c.execute('UPDATE gallery_albums SET slug=? WHERE id=?',(gallery_slug(title,int(aid)),int(aid)))
    row=c.execute('SELECT * FROM gallery_albums WHERE id=?',(aid,)).fetchone();return album_record(c,row,include_media=True)

def delete_gallery_album(c: sqlite3.Connection, aid: int) -> bool:
    rows=c.execute('SELECT stored_name FROM gallery_media WHERE album_id=?',(aid,)).fetchall()
    exists=c.execute('SELECT id FROM gallery_albums WHERE id=?',(aid,)).fetchone()
    if not exists:return False
    c.execute('DELETE FROM gallery_albums WHERE id=?',(aid,));c.commit()
    for r in rows:
        target=_safe_media_path(r['stored_name'])
        if target:
            try: target.unlink(missing_ok=True)
            except OSError: pass
    return True

def _safe_media_path(value: str) -> Path | None:
    name=Path(str(value or '')).name
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:png|jpe?g|webp|gif|mp4|webm|mov|avi)',name,re.I):return None
    target=(MEDIA_DIR/name).resolve()
    try: target.relative_to(MEDIA_DIR.resolve())
    except ValueError:return None
    return target

def delete_gallery_media(c: sqlite3.Connection, mid: int) -> bool:
    row=c.execute('SELECT stored_name FROM gallery_media WHERE id=?',(mid,)).fetchone()
    if not row:return False
    c.execute('DELETE FROM gallery_media WHERE id=?',(mid,));c.commit();target=_safe_media_path(row['stored_name'])
    if target:
        try: target.unlink(missing_ok=True)
        except OSError: pass
    return True

def json_bytes(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def send(handler: SimpleHTTPRequestHandler, status: int, obj: dict, headers: dict | None = None) -> None:
    body = json_bytes(obj)
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    for k, v in (headers or {}).items():
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body)


def security_headers(handler: SimpleHTTPRequestHandler) -> None:
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "SAMEORIGIN")
    handler.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
    handler.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    handler.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self' 'unsafe-inline'; connect-src 'self' https://api.stripe.com; form-action 'self' https://checkout.stripe.com")
    if handler.headers.get("X-Forwarded-Proto", "").lower() == "https":
        handler.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


def session_ok(handler: SimpleHTTPRequestHandler) -> bool:
    token = handler.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return False
    c = db()
    row = c.execute("SELECT expires_at FROM sessions WHERE token=?", (token,)).fetchone()
    c.close()
    return bool(row and row["expires_at"] > int(time.time()))


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def rate_limited(scope: str, client: str, limit: int, window: int) -> bool:
    key = (scope, client)
    current = time.time()
    with RATE_LOCK:
        values = [t for t in RATE_BUCKETS.get(key, []) if current - t < window]
        limited = len(values) >= limit
        if not limited:
            values.append(current)
        RATE_BUCKETS[key] = values
        return limited


def send_mail(subject: str, text: str, to: str | None = None) -> bool:
    recipient = (to or SITE_OWNER_EMAIL).strip()
    if not SMTP_HOST or not SMTP_FROM or not recipient:
        return False
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(text)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        print("Email delivery failed:", exc)
        return False


def stripe_request(method: str, endpoint: str, params: dict) -> dict:
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not configured")
    body = urlencode(params).encode("utf-8")
    req = Request("https://api.stripe.com/v1/" + endpoint, data=body, method=method)
    req.add_header("Authorization", f"Bearer {STRIPE_SECRET_KEY}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stripe error: {detail[:500]}") from exc
    except URLError as exc:
        raise RuntimeError("Unable to reach Stripe") from exc


def create_stripe_checkout(order_id: str, email: str, items: list[dict]) -> dict:
    if not STRIPE_SECRET_KEY:
        return {}
    if not PUBLIC_BASE_URL.startswith("https://"):
        raise RuntimeError("PUBLIC_BASE_URL must be an HTTPS URL before enabling Stripe")
    params = {
        "mode": "payment",
        "customer_email": email,
        "success_url": f"{PUBLIC_BASE_URL}/cart.html?payment=success&order={order_id}",
        "cancel_url": f"{PUBLIC_BASE_URL}/cart.html?payment=cancelled&order={order_id}",
        "metadata[order_id]": order_id,
    }
    for i, item in enumerate(items):
        prefix = f"line_items[{i}]"
        params[f"{prefix}[quantity]"] = str(item["quantity"])
        params[f"{prefix}[price_data][currency]"] = "eur"
        params[f"{prefix}[price_data][unit_amount]"] = str(item["priceCents"])
        params[f"{prefix}[price_data][product_data][name]"] = item["name"]
    return stripe_request("POST", "checkout/sessions", params)


def verify_stripe_signature(payload: bytes, header: str) -> bool:
    if not STRIPE_WEBHOOK_SECRET:
        return False
    parts = {}
    for part in header.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            parts.setdefault(k, []).append(v)
    try:
        timestamp = int(parts.get("t", ["0"])[0])
    except ValueError:
        return False
    if abs(int(time.time()) - timestamp) > 300:
        return False
    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


def apply_paid_order(c: sqlite3.Connection, order_id: str, session_id: str = "") -> bool:
    release_expired_reservations(c)
    row = c.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        return False
    if row["stock_applied"]:
        c.execute("UPDATE orders SET status='PAID',payment_status='PAID',stripe_session_id=COALESCE(?,stripe_session_id),stock_reserved=0,reservation_expires_at=NULL,updated_at=? WHERE id=?", (session_id or None, now(), order_id))
        return True
    items = json.loads(row["items_json"])
    savepoint = f"paid_{secrets.token_hex(4)}"
    c.execute(f"SAVEPOINT {savepoint}")
    try:
        for item in items:
            product = c.execute("SELECT stock,reserved_stock FROM products WHERE id=?", (item["productId"],)).fetchone()
            if product and product["stock"] > 0:
                qty = int(item["quantity"])
                reserved = int(product["reserved_stock"] or 0)
                if row["stock_reserved"] >= qty and reserved >= qty:
                    c.execute("UPDATE products SET stock=stock-?,reserved_stock=MAX(0,reserved_stock-?),updated_at=? WHERE id=?", (qty, qty, now(), item["productId"]))
                else:
                    available = int(product["stock"]) - reserved
                    if available < qty:
                        raise RuntimeError("Insufficient stock at payment confirmation")
                    c.execute("UPDATE products SET stock=stock-?,updated_at=? WHERE id=?", (qty, now(), item["productId"]))
        c.execute("UPDATE orders SET status='PAID',payment_status='PAID',stripe_session_id=COALESCE(?,stripe_session_id),stock_applied=1,stock_reserved=0,reservation_expires_at=NULL,updated_at=? WHERE id=?", (session_id or None, now(), order_id))
        c.execute(f"RELEASE SAVEPOINT {savepoint}")
        return True
    except Exception:
        c.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        c.execute(f"RELEASE SAVEPOINT {savepoint}")
        return False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def end_headers(self):
        security_headers(self)
        super().end_headers()

    def read_json(self, max_body: int = MAX_BODY) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid content length")
        if length <= 0:
            raise ValueError("Empty request body")
        if length > max_body:
            try:
                self.rfile.read(length)
            except Exception:
                pass
            raise ValueError("Payload too large")
        raw = self.rfile.read(length)
        return json.loads(raw)

    def blocked_static(self, path: str) -> bool:
        normalized = "/" + path.lstrip("/")
        blocked = (
            normalized.startswith("/backend/data"),
            normalized.startswith("/backend/__pycache__"),
            normalized in {"/backend/server.py", "/backend/requirements.txt", "/backend/.env", "/backend/.env.example", "/backend/README.md"},
        )
        return any(blocked)

    def do_GET(self):
        path = urlparse(self.path).path
        if self.blocked_static(path):
            return send(self, 404, {"error": "Not found"})
        if path == "/api/health":
            c = db(); release_expired_reservations(c); c.commit(); c.close()
            return send(self, 200, {"ok": True, "service": "kosmik-circles", "version": API_VERSION, "time": now(), "stripeConfigured": bool(STRIPE_SECRET_KEY), "emailConfigured": bool(SMTP_HOST and SMTP_FROM)})
        if path == "/api/config":
            return send(self, 200, {"paymentProvider": "stripe" if STRIPE_SECRET_KEY else None, "paymentsEnabled": bool(STRIPE_SECRET_KEY and PUBLIC_BASE_URL.startswith("https://"))})
        if path == "/api/orders/status":
            query = parse_qs(urlparse(self.path).query)
            oid = query.get("id", [""])[0].strip()[:80]
            status_token = query.get("token", [""])[0].strip()[:200]
            if not oid or not status_token:
                return send(self, 400, {"error": "Missing order credentials"})
            c = db(); row = c.execute("SELECT id,status,payment_status,shipping_status FROM orders WHERE id=? AND status_token=?", (oid, status_token)).fetchone(); c.close()
            if not row:
                return send(self, 404, {"error": "Order not found"})
            return send(self, 200, {"orderId": row["id"], "status": row["status"], "paymentStatus": row["payment_status"], "shippingStatus": row["shipping_status"]})
        if path == "/api/gallery/albums":
            c=db();albums=list_gallery_albums(c,public=True);c.close();return send(self,200,{"albums":albums})
        m=re.fullmatch(r"/api/gallery/albums/(\d+)",path)
        if m:
            c=db();row=c.execute('SELECT * FROM gallery_albums WHERE id=? AND active=1',(int(m.group(1)),)).fetchone()
            if not row:c.close();return send(self,404,{"error":"Archive folder not found"})
            album=album_record(c,row,include_media=True);c.close();return send(self,200,{"album":album})
        m=re.fullmatch(r"/api/gallery/media/(\d+)/download",path)
        if m:
            c=db();row=c.execute('SELECT * FROM gallery_media WHERE id=? AND active=1',(int(m.group(1)),)).fetchone();c.close()
            if not row:return send(self,404,{"error":"Media not found"})
            target=_safe_media_path(row['stored_name'])
            if not target or not target.is_file():return send(self,404,{"error":"Media file not found"})
            data=target.read_bytes();disp=quote(str(row['original_name'] or target.name).replace('\\','_').replace('/','_'))
            self.send_response(200);self.send_header('Content-Type',row['mime_type']);self.send_header('Content-Length',str(len(data)));self.send_header('Content-Disposition',f"attachment; filename*=UTF-8''{disp}");self.send_header('Cache-Control','private, max-age=3600');self.end_headers();self.wfile.write(data);return
        if path.startswith('/backend/media/'):
            try:mid=int(Path(path).name)
            except ValueError:return send(self,404,{"error":"Media not found"})
            c=db();row=c.execute('SELECT * FROM gallery_media WHERE id=? AND active=1',(mid,)).fetchone();c.close()
            if not row:return send(self,404,{"error":"Media not found"})
            target=_safe_media_path(row['stored_name'])
            if not target or not target.is_file():return send(self,404,{"error":"Media file not found"})
            size=target.stat().st_size; self.send_response(200);self.send_header('Content-Type',row['mime_type']);self.send_header('Content-Length',str(size));self.send_header('Content-Disposition','inline');self.send_header('Cache-Control','public, max-age=86400');self.end_headers();
            with target.open('rb') as f:
                while True:
                    chunk=f.read(1024*1024)
                    if not chunk:break
                    self.wfile.write(chunk)
            return
        if path == "/api/content":
            c = db(); release_expired_reservations(c); c.commit()
            data = merge_content_defaults(content_from_db(c))
            products = [dict(r) for r in c.execute("SELECT id,name,meta,description,price_cents,image,alt,stock,reserved_stock,active FROM products WHERE active=1 ORDER BY id")]
            events = [dict(r) for r in c.execute("SELECT id,date,iso_date,location,venue,signal,detail,action,ticket_url,past FROM events ORDER BY iso_date,id")]
            gallery = [dict(r) for r in c.execute("SELECT id,image,alt,caption,sort_order FROM gallery WHERE active=1 ORDER BY sort_order,id")]
            c.close()
            data["shop"] = [{**p, "price": f"€ {p['price_cents']/100:.2f}", "stock": p["stock"], "reservedStock": p["reserved_stock"], "availableStock": (None if p["stock"] == 0 else max(0, p["stock"] - p["reserved_stock"]))} for p in products] or data.get("shop", [])
            data["live"] = events or data.get("live", [])
            data["gallery"] = gallery or data.get("gallery", [])
            return send(self, 200, {"content": data})
        if path == "/api/admin/gallery/albums":
            if not session_ok(self): return send(self,401,{"error":"Unauthorized"})
            c=db();albums=list_gallery_albums(c,public=False);c.close();return send(self,200,{"albums":albums})
        if path == "/api/admin/orders":
            if not session_ok(self): return send(self, 401, {"error": "Unauthorized"})
            c = db(); release_expired_reservations(c); c.commit(); rows = [dict(r) for r in c.execute("SELECT o.*, c.name,c.phone,c.address,c.city,c.postcode,c.country FROM orders o LEFT JOIN customers c ON c.id=o.customer_id ORDER BY o.created_at DESC")]; c.close()
            return send(self, 200, {"orders": rows})
        if path == "/api/admin/messages":
            if not session_ok(self): return send(self, 401, {"error": "Unauthorized"})
            c = db(); rows = [dict(r) for r in c.execute("SELECT * FROM messages ORDER BY created_at DESC")]; c.close()
            return send(self, 200, {"messages": rows})
        if path == "/api/admin/stats":
            if not session_ok(self): return send(self, 401, {"error": "Unauthorized"})
            c = db(); stats = {
                "orders": c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"],
                "paidOrders": c.execute("SELECT COUNT(*) n FROM orders WHERE payment_status='PAID'").fetchone()["n"],
                "messages": c.execute("SELECT COUNT(*) n FROM messages WHERE status='new'").fetchone()["n"],
                "products": c.execute("SELECT COUNT(*) n FROM products WHERE active=1").fetchone()["n"],
                "revenueCents": c.execute("SELECT COALESCE(SUM(total_cents),0) n FROM orders WHERE payment_status='PAID'").fetchone()["n"],
            }; c.close(); return send(self, 200, {"stats": stats})
        if path.startswith("/backend/uploads/"):
            target = _safe_upload_path(path)
            if target is None or not target.is_file():
                return send(self, 404, {"error": "Image not found"})
            data = target.read_bytes()
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(target.suffix.lower(), "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def read_raw_upload(self) -> tuple[bytes, str]:
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('Invalid content length')
        if length<=0 or length>MAX_UPLOAD:
            raise ValueError('Image exceeds the 5 MB limit or is empty')
        content_type=self.headers.get('Content-Type','').split(';',1)[0].strip().lower()
        allowed={'image/png':'png','image/jpeg':'jpg','image/webp':'webp','image/gif':'gif'}
        if content_type not in allowed:raise ValueError('Unsupported image type')
        raw=self.rfile.read(length)
        if len(raw)!=length:raise ValueError('Incomplete image upload')
        signatures={'image/png':raw.startswith(b'\x89PNG\r\n\x1a\n'),'image/jpeg':raw.startswith(b'\xff\xd8\xff'),'image/webp':len(raw)>=12 and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP','image/gif':raw.startswith((b'GIF87a',b'GIF89a'))}
        if not signatures.get(content_type,False):raise ValueError('Image content does not match its declared type')
        return raw,allowed[content_type]

    def stream_media_upload(self) -> tuple[str,str,str,int]:
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('Invalid content length')
        if length<=0 or length>MAX_MEDIA_UPLOAD:raise ValueError('Media exceeds the 1 GB limit or is empty')
        mime=self.headers.get('Content-Type','').split(';',1)[0].strip().lower()
        allowed={'image/png':'png','image/jpeg':'jpg','image/webp':'webp','image/gif':'gif','video/mp4':'mp4','video/webm':'webm','video/quicktime':'mov','video/x-msvideo':'avi'}
        if mime not in allowed:raise ValueError('Unsupported media type')
        ext=allowed[mime]; name=f'media-{secrets.token_hex(10)}.{ext}'; target=MEDIA_DIR/name; tmp=MEDIA_DIR/f'.{name}.part'
        remaining=length; first=b''
        try:
            with tmp.open('wb') as f:
                while remaining>0:
                    chunk=self.rfile.read(min(1024*1024,remaining))
                    if not chunk:raise ValueError('Incomplete media upload')
                    if len(first)<64:first += chunk[:64-len(first)]
                    f.write(chunk);remaining-=len(chunk)
            valid=(mime=='image/png' and first.startswith(b'\x89PNG\r\n\x1a\n')) or (mime=='image/jpeg' and first.startswith(b'\xff\xd8\xff')) or (mime=='image/webp' and len(first)>=12 and first[:4]==b'RIFF' and first[8:12]==b'WEBP') or (mime=='image/gif' and first.startswith((b'GIF87a',b'GIF89a'))) or (mime in {'video/mp4','video/quicktime'} and len(first)>=8 and first[4:8]==b'ftyp') or (mime=='video/webm' and first.startswith(b'\x1a\x45\xdf\xa3')) or (mime=='video/x-msvideo' and first[:4]==b'RIFF')
            if not valid:raise ValueError('Media content does not match its declared type')
            tmp.replace(target)
            return name,mime,ext,length
        except Exception:
            try:tmp.unlink(missing_ok=True)
            except OSError:pass
            raise

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/stripe/webhook":
            payload = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if not verify_stripe_signature(payload, self.headers.get("Stripe-Signature", "")):
                return send(self, 400, {"error": "Invalid webhook signature"})
            try:
                event = json.loads(payload)
                obj = event.get("data", {}).get("object", {})
                event_type = event.get("type", "")
                if event_type == "checkout.session.completed" and obj.get("payment_status") == "paid":
                    order_id = obj.get("metadata", {}).get("order_id", "")
                    c = db(); applied = apply_paid_order(c, order_id, obj.get("id", "")); c.commit();
                    paid = c.execute("SELECT email,total_cents FROM orders WHERE id=?", (order_id,)).fetchone() if applied else None
                    c.close()
                    if order_id and applied:
                        send_mail(f"Kosmik Circles — payment received {order_id}", f"Order {order_id} has been paid.\n\nTotal: € {((paid['total_cents'] if paid else 0)/100):.2f}\n", SITE_OWNER_EMAIL)
                        if paid:
                            send_mail(f"Kosmik Circles — order confirmed {order_id}", f"Your order {order_id} has been paid and confirmed.\n\nTotal: € {paid['total_cents']/100:.2f}\n\nThank you for your order.\n", paid["email"])
                elif event_type == "checkout.session.expired":
                    order_id = obj.get("metadata", {}).get("order_id", "")
                    if order_id:
                        c = db(); release_order_reservation(c, order_id); c.commit(); c.close()
                return send(self, 200, {"received": True})
            except Exception as exc:
                print("Webhook error:", exc)
                return send(self, 500, {"error": "Webhook processing failed"})
        if path == "/api/admin/upload":
            if not session_ok(self):
                return send(self, 401, {"error": "Unauthorized"})
            try:
                raw, ext = self.read_raw_upload()
            except Exception as exc:
                return send(self, 400, {"error": str(exc)})
            qs = parse_qs(urlparse(self.path).query)
            prefix = re.sub(r"[^a-z0-9_-]+", "", str(qs.get("prefix", ["image"])[0]).lower())[:24] or "image"
            name = f"{prefix}-{secrets.token_hex(8)}.{ext}"
            (UPLOADS / name).write_bytes(raw)
            return send(self, 201, {"ok": True, "image": f"/backend/uploads/{name}"})
        if path == "/api/admin/logout":
            token = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            c = db(); c.execute("DELETE FROM sessions WHERE token=?", (token,)); c.commit(); c.close(); return send(self, 200, {"ok": True})
        if path == "/api/admin/gallery/media/upload":
            if not session_ok(self):return send(self,401,{"error":"Unauthorized"})
            qs=parse_qs(urlparse(self.path).query);album_id=int(qs.get('album_id',['0'])[0] or 0);c=db();album=c.execute('SELECT id FROM gallery_albums WHERE id=?',(album_id,)).fetchone()
            if not album:c.close();return send(self,404,{"error":"Archive folder not found"})
            try:
                stored,mime,ext,size=self.stream_media_upload(); original=str(qs.get('filename',['media'])[0] or 'media')[:240]
                sort=int(c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 FROM gallery_media WHERE album_id=?',(album_id,)).fetchone()[0]);stamp=now()
                c.execute('INSERT INTO gallery_media(album_id,original_name,stored_name,media_type,mime_type,size_bytes,sort_order,active,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(album_id,original,stored,mime,mime,size,sort,1,stamp));mid=c.execute('SELECT last_insert_rowid()').fetchone()[0];c.commit();c.close();return send(self,201,{"ok":True,"media": {"id":int(mid),"mediaUrl":f"/backend/media/{int(mid)}","downloadUrl":f"/api/gallery/media/{int(mid)}/download","originalName":original,"mediaType":mime,"sizeBytes":size}})
            except Exception as exc:
                c.close();return send(self,400,{"error":str(exc)})
        try:
            data = self.read_json()
        except Exception:
            return send(self, 400, {"error": "Invalid JSON or payload too large"})
        if path == "/api/admin/login":
            if rate_limited("login", self.client_address[0], 8, 300):
                return send(self, 429, {"error": "Too many login attempts. Try again later."})
            password = str(data.get("password", ""))
            if not ADMIN_PASSWORD or not hmac.compare_digest(password, ADMIN_PASSWORD):
                return send(self, 401, {"error": "Invalid credentials"})
            token = secrets.token_urlsafe(36); expires = int(time.time()) + SESSION_TTL
            c = db(); c.execute("DELETE FROM sessions WHERE expires_at<?", (int(time.time()),)); c.execute("INSERT INTO sessions VALUES(?,?)", (token, expires)); c.commit(); c.close()
            return send(self, 200, {"token": token, "expiresAt": expires})
        if path == "/api/messages":
            if rate_limited("message", self.client_address[0], 5, 600):
                return send(self, 429, {"error": "Too many messages. Try again later."})
            name = str(data.get("name", "")).strip()[:120]; email = str(data.get("email", "")).strip()[:200]; message = str(data.get("message", "")).strip()[:4000]
            if data.get("website"): return send(self, 200, {"ok": True})
            if not name or not valid_email(email) or not message: return send(self, 400, {"error": "Invalid contact data"})
            c = db(); mid = "MSG-" + secrets.token_hex(6).upper(); c.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (mid,name,email,message,"new",now())); c.commit(); c.close()
            send_mail(f"Kosmik Circles — new message from {name}", f"From: {name}\nEmail: {email}\n\n{message}\n", SITE_OWNER_EMAIL)
            return send(self, 201, {"ok": True, "id": mid})
        if path == "/api/checkout":
            if rate_limited("checkout", self.client_address[0], 20, 600):
                return send(self, 429, {"error": "Too many checkout attempts. Try again later."})
            email = str(data.get("email", "")).strip()[:200]; items = data.get("items", []); customer = data.get("customer", {}) or {}
            if not valid_email(email) or not isinstance(items, list) or not items or len(items) > 50: return send(self, 400, {"error": "Invalid order"})
            c = db(); clean = []; total = 0; reservation_started = False; oid = ""; status_token = ""
            try:
                for item in items:
                    name = str(item.get("name", "")).strip()[:160]
                    raw_qty = item.get("quantity")
                    try:
                        if isinstance(raw_qty, bool):
                            raise ValueError
                        qty = int(raw_qty)
                    except (TypeError, ValueError):
                        return send(self, 400, {"error": f"Invalid quantity: {name}"})
                    if qty <= 0 or qty > 99:
                        return send(self, 400, {"error": f"Invalid quantity: {name}"})
                    row = c.execute("SELECT * FROM products WHERE name=? AND active=1", (name,)).fetchone()
                    if not row: return send(self, 400, {"error": f"Product unavailable: {name}"})
                    total += row["price_cents"] * qty
                    clean.append({"productId": row["id"], "name": row["name"], "quantity": qty, "priceCents": row["price_cents"]})
                expires_at = reserve_order_stock(c, clean)
                reservation_started = True
                oid = "KC-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
                status_token = new_status_token()
                cur = c.cursor(); cur.execute("INSERT INTO customers(name,email,phone,address,city,postcode,country,created_at) VALUES(?,?,?,?,?,?,?,?)", (str(customer.get("name", ""))[:160], email, str(customer.get("phone", ""))[:60], str(customer.get("address", ""))[:250], str(customer.get("city", ""))[:120], str(customer.get("postcode", ""))[:20], str(customer.get("country", ""))[:80], now())); cid = cur.lastrowid
                cur.execute("INSERT INTO orders(id,customer_id,email,total_cents,status,payment_status,shipping_status,items_json,stock_reserved,reservation_expires_at,status_token,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (oid,cid,email,total,"NEW","UNPAID","UNFULFILLED",json.dumps(clean),sum(int(i["quantity"]) for i in clean),expires_at,status_token,now(),now())); c.commit()
            except ValueError as exc:
                c.rollback(); c.close(); return send(self, 400, {"error": str(exc)})
            except RuntimeError as exc:
                c.rollback(); c.close(); return send(self, 409, {"error": str(exc)})
            except Exception:
                c.rollback(); c.close(); return send(self, 500, {"error": "Unable to create order"})
            finally:
                try:
                    c.close()
                except Exception:
                    pass
            try:
                session = create_stripe_checkout(oid, email, clean)
            except RuntimeError as exc:
                if reservation_started:
                    c = db(); release_order_reservation(c, oid); c.commit(); c.close()
                return send(self, 503, {"error": str(exc), "orderId": oid})
            if session:
                c = db(); c.execute("UPDATE orders SET stripe_session_id=?,updated_at=? WHERE id=?", (session.get("id"), now(), oid)); c.commit(); c.close()
                return send(self, 201, {"ok": True, "orderId": oid, "statusToken": status_token, "totalCents": total, "checkoutUrl": session.get("url"), "paymentRequired": True})
            if reservation_started:
                c = db(); release_order_reservation(c, oid); c.commit(); c.close()
            return send(self, 201, {"ok": True, "orderId": oid, "statusToken": status_token, "totalCents": total, "paymentRequired": False, "message": "Payment provider is not configured yet."})
        if path == "/api/orders":
            return send(self, 410, {"error": "Use /api/checkout"})
        if path == "/api/admin/gallery/albums/save":
            if not session_ok(self):return send(self,401,{"error":"Unauthorized"})
            try:
                c=db();album=save_gallery_album(c,data.get('album') or {});c.commit();c.close();return send(self,200,{"ok":True,"album":album})
            except Exception as exc:return send(self,400,{"error":str(exc)})
        if path.startswith("/api/admin/"):
            if not session_ok(self): return send(self, 401, {"error": "Unauthorized"})
            if path == "/api/admin/content":
                content = data.get("content", DEFAULT_CONTENT)
                c = db()
                try:
                    normalized = save_content(c, content)
                except Exception as exc:
                    c.rollback(); c.close(); return send(self, 400, {"error": str(exc)})
                c.close(); return send(self, 200, {"ok": True, "content": normalized})
            if path == "/api/admin/orders/status":
                oid = str(data.get("id", "")); status = str(data.get("status", "NEW")).upper()
                if status not in ORDER_STATUSES: return send(self, 400, {"error": "Invalid status"})
                if status == "PAID": return send(self, 409, {"error": "PAID is provider-confirmed and cannot be set manually."})
                c = db(); row = c.execute("SELECT status,payment_status,stock_reserved FROM orders WHERE id=?", (oid,)).fetchone()
                if not row: c.close(); return send(self, 404, {"error": "Order not found"})
                if row["payment_status"] != "PAID" and status not in {"NEW", "CANCELLED"}:
                    c.close(); return send(self, 409, {"error": "Unpaid orders can only be NEW or CANCELLED."})
                c.execute("UPDATE orders SET status=?,updated_at=? WHERE id=?", (status, now(), oid))
                if status in {"CANCELLED", "REFUNDED"} and row["stock_reserved"]:
                    release_order_reservation(c, oid)
                c.commit(); c.close(); return send(self, 200, {"ok": True})
        return send(self, 404, {"error": "Not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not session_ok(self): return send(self, 401, {"error": "Unauthorized"})
        q = parse_qs(urlparse(self.path).query); c = db()
        if path.startswith("/api/admin/gallery/media/"):
            m=re.fullmatch(r"/api/admin/gallery/media/(\d+)",path)
            if not m:
                c.close(); return send(self,404,{"error":"Media not found"})
            mid=int(m.group(1));ok=delete_gallery_media(c,mid);c.close();return send(self,200 if ok else 404,{"ok":ok} if ok else {"error":"Media not found"})
        if path == "/api/admin/gallery/albums/delete":
            aid=int(q.get('id',['0'])[0] or 0);ok=delete_gallery_album(c,aid);c.close();return send(self,200 if ok else 404,{"ok":ok} if ok else {"error":"Archive folder not found"})
        if path == "/api/admin/messages":
            c.execute("DELETE FROM messages WHERE id=?", (q.get("id", [""])[0],)); c.commit(); c.close(); return send(self, 200, {"ok": True})
        c.close(); return send(self, 404, {"error": "Not found"})


if __name__ == "__main__":
    init_db()
    print(f"Kosmik Circles server: http://{HOST}:{PORT}")
    print("Admin password must be set with KOSMIK_ADMIN_PASSWORD.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
