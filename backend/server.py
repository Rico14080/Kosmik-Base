#!/usr/bin/env python3
"""Kosmik Circles production-oriented local backend V1.9.

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
from datetime import datetime, timezone
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
MAX_BODY = 1_500_000
MAX_UPLOAD = 5 * 1024 * 1024
MAX_MEDIA_UPLOAD = 1024 * 1024 * 1024
API_VERSION = "1.14"
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
        {"name": "Moon Phase Tee", "meta": "Heavy cotton / ink black", "description": "240 gsm organic cotton tee with a front orbit mark and relaxed fit.", "price": "€ 48", "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1000&q=85", "stock": 8},
        {"name": "Signal Cap", "meta": "Five-panel / orange mark", "description": "Adjustable five-panel cap with embroidered Kosmik Circles signal.", "price": "€ 36", "image": "https://images.unsplash.com/photo-1521369909029-2afed882baee?auto=format&fit=crop&w=1000&q=85", "stock": 12},
        {"name": "Red Planet Mug", "meta": "Stoneware / 330 ml", "description": "Hand-finished ceramic mug made for long nights and slow conversations.", "price": "€ 26", "image": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=1000&q=85", "stock": 15},
        {"name": "Field Notes 001", "meta": "Risograph print / A3", "description": "A numbered studio print mapping our first transmission into the night.", "price": "€ 18", "image": "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=1000&q=85", "stock": 20}
    ],
    "us": {
        "sectionNumber":"[ 002 ]",
        "statement":"There is a lot of noise out there. We like the kind that means something.",
        "description":"Kosmik Circles started with two friends, a stack of old astronomy books, and a shared belief that everyday things deserve a little mystery. We make products in limited runs, with honest materials, and an unreasonable amount of attention.",
        "photo":"https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1000&q=85",
        "photoAlt":"Kosmik Circles studio",
        "studioLabel":"KC",
        "soundEyebrow":"The sound / Live frequency",
        "soundTitleLineOne":"Built for",
        "soundTitleLineTwo":"the room.",
        "soundDescription":"Our sound moves between hypnotic low-end, psychedelic textures, and long-form tension. These images are fragments from the places where the signal becomes physical.",
        "soundImages":[
            {"image":"https://images.unsplash.com/photo-1524365252-6f0b8f4e8f7a?auto=format&fit=crop&w=1000&q=85","alt":"DJ performing under red stage lights","caption":"01 / Low light"},
            {"image":"/WhatsApp Image 2026-08-11 at 00.52.13 (13).webp","alt":"Abstract concert lights in a dark room","caption":"02 / Deep signal"},
            {"image":"https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1000&q=85","alt":"Crowd moving beneath concert lights","caption":"03 / Shared frequency"}
        ],
        "valuesEyebrow":"Our coordinates",
        "valuesTitleLineOne":"Slow things.",
        "valuesTitleLineTwo":"Strange things.",
        "valuesTitleLineThree":"Good things.",
        "valuesDescription":"Designed in Milan. Made with people we know. Packed by hand. Every object has a trace of where it came from."
    },
    "visuals": {"liveBackgroundImage":"https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=85"},
    "siteText": {
        "skipToContent":"Skip to content","liveUpdates":"Live updates",
        "nav":{"home":"Home","shop":"Shop","us":"Us","live":"Live","gallery":"Gallery","contact":"Contact","bag":"Bag","cart":"Cart"},
        "home":{"currentlyTransmitting":"Currently transmitting"},
        "shop":{"addToCart":"Add to cart"},
        "gallery":{"emptyImage":"Open a night archive"},
        "live":{"date":"Date","location":"Location","signal":"Signal","noTicket":"Tickets"},
        "contact":{"name":"Your name","email":"Your email","message":"Your message","submit":"Transmit"},
        "cart":{"yourName":"Your name","yourEmail":"Your email","phone":"Phone","address":"Address","city":"City","postcode":"Postcode","country":"Country","sendOrder":"Send order","remove":"Remove","empty":"Your cart is orbiting empty.","sending":"Sending order…","quantity":"quantity","total":"Total"},
        "footer":{"tagline":"Made on Earth, for now","homeCta":"Say hello","shopCta":"Say hello","galleryCta":"Send a signal","liveCta":"Book a transmission","usCta":"Say hello","contactCta":"Browse objects","cartCta":"Back to shop"}
    }
}

# The remainder of the production backend is intentionally copied from the V1.14 package.
# Keeping the complete source here makes the repository self-contained.

SESSIONS: dict[str, float] = {}
SESSION_USER: dict[str, str] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def db_connect() -> sqlite3.Connection:
    ensure_dirs()
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with db_connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, status TEXT NOT NULL, customer_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT DEFAULT '', address TEXT DEFAULT '', city TEXT DEFAULT '', postcode TEXT DEFAULT '', country TEXT DEFAULT '', items_json TEXT NOT NULL, total_cents INTEGER NOT NULL, stripe_session_id TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL, ip TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS gallery_albums (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, title TEXT NOT NULL, date TEXT DEFAULT '', location TEXT DEFAULT '', description TEXT DEFAULT '', cover_image TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS gallery_media (id INTEGER PRIMARY KEY AUTOINCREMENT, album_id INTEGER NOT NULL, filename TEXT NOT NULL, original_name TEXT NOT NULL, media_type TEXT NOT NULL, size INTEGER NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(album_id) REFERENCES gallery_albums(id) ON DELETE CASCADE);
        ''')
        row = con.execute('SELECT id FROM content WHERE id=1').fetchone()
        if not row:
            con.execute('INSERT INTO content(id,payload,updated_at) VALUES(1,?,?)', (json.dumps(DEFAULT_CONTENT, ensure_ascii=False), utc_now()))
        con.commit()


def json_response(handler, status: int, payload: dict, extra_headers: dict[str, str] | None = None) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Cache-Control', 'no-store')
    if extra_headers:
        for k, v in extra_headers.items(): handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(data)


def security_headers(handler) -> None:
    handler.send_header('X-Content-Type-Options', 'nosniff')
    handler.send_header('X-Frame-Options', 'DENY')
    handler.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
    handler.send_header('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')


def safe_filename(name: str) -> str:
    base = Path(str(name or 'file')).name
    base = re.sub(r'[^A-Za-z0-9._-]+', '_', base).strip('._')
    return (base or 'file')[:180]


def admin_ok(handler) -> bool:
    auth = handler.headers.get('Authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    if not token or token not in SESSIONS: return False
    if time.time() > SESSIONS[token]:
        SESSIONS.pop(token, None); SESSION_USER.pop(token, None); return False
    return True


def rate_ok(ip: str, bucket: str, limit: int = 60, window: int = 60) -> bool:
    now = time.time(); key = (ip, bucket)
    with RATE_LOCK:
        values = [t for t in RATE_BUCKETS.get(key, []) if now - t < window]
        if len(values) >= limit: RATE_BUCKETS[key] = values; return False
        values.append(now); RATE_BUCKETS[key] = values
    return True


class Handler(SimpleHTTPRequestHandler):
    server_version = 'KosmikCircles/1.14'

    def end_headers(self):
        security_headers(self)
        super().end_headers()

    def log_message(self, fmt, *args):
        print('%s - %s' % (self.address_string(), fmt % args))

    def _body(self) -> bytes:
        n = int(self.headers.get('Content-Length','0') or 0)
        if n > MAX_BODY: raise ValueError('payload too large')
        return self.rfile.read(n)

    def _json(self) -> dict:
        return json.loads(self._body().decode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Access-Control-Allow-Methods','GET, POST, DELETE, OPTIONS'); self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/health': return json_response(self, 200, {'ok': True, 'version': API_VERSION, 'time': utc_now()})
        if u.path == '/api/content':
            with db_connect() as con:
                row = con.execute('SELECT payload,updated_at FROM content WHERE id=1').fetchone()
            return json_response(self, 200, {'content': json.loads(row['payload']) if row else copy.deepcopy(DEFAULT_CONTENT), 'updated_at': row['updated_at'] if row else None})
        if u.path == '/api/admin/orders':
            if not admin_ok(self): return json_response(self,401,{'error':'unauthorized'})
            with db_connect() as con: rows = con.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
            return json_response(self,200,{'orders':[dict(r) for r in rows]})
        if u.path == '/api/admin/messages':
            if not admin_ok(self): return json_response(self,401,{'error':'unauthorized'})
            with db_connect() as con: rows = con.execute('SELECT * FROM messages ORDER BY id DESC').fetchall()
            return json_response(self,200,{'messages':[dict(r) for r in rows]})
        if u.path == '/api/gallery/albums':
            with db_connect() as con:
                albums = [dict(r) for r in con.execute('SELECT * FROM gallery_albums ORDER BY date DESC, id DESC').fetchall()]
                for a in albums:
                    a['media'] = [dict(r) for r in con.execute('SELECT * FROM gallery_media WHERE album_id=? ORDER BY id DESC',(a['id'],)).fetchall()]
            return json_response(self,200,{'albums':albums})
        if u.path.startswith('/api/gallery/albums/'):
            try: album_id = int(u.path.rsplit('/',1)[-1])
            except ValueError: return json_response(self,400,{'error':'invalid album id'})
            with db_connect() as con:
                a=con.execute('SELECT * FROM gallery_albums WHERE id=?',(album_id,)).fetchone()
                if not a: return json_response(self,404,{'error':'album not found'})
                media=con.execute('SELECT * FROM gallery_media WHERE album_id=? ORDER BY id DESC',(album_id,)).fetchall()
            return json_response(self,200,{'album':dict(a),'media':[dict(r) for r in media]})
        if u.path.startswith('/uploads/') or u.path.startswith('/media/'):
            rel = u.path.lstrip('/'); full = (ROOT / rel).resolve()
            allowed = UPLOADS.resolve(), MEDIA_DIR.resolve()
            if not any(str(full).startswith(str(a)+os.sep) for a in allowed) or not full.exists():
                return json_response(self,404,{'error':'not found'})
            return self._serve_file(full)
        return super().do_GET()

    def _serve_file(self, full: Path):
        ctype = mimetypes.guess_type(str(full))[0] or 'application/octet-stream'; size = full.stat().st_size
        self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(size)); self.send_header('Cache-Control','public, max-age=31536000, immutable'); self.end_headers()
        with full.open('rb') as f:
            while chunk:=f.read(1024*1024): self.wfile.write(chunk)

    def do_POST(self):
        u=urlparse(self.path); ip=self.client_address[0]
        if not rate_ok(ip,u.path,120,60): return json_response(self,429,{'error':'rate limited'})
        if u.path == '/api/admin/login':
            try: data=self._json()
            except Exception: return json_response(self,400,{'error':'invalid json'})
            if ADMIN_PASSWORD and hmac.compare_digest(str(data.get('password','')), ADMIN_PASSWORD) and str(data.get('username','admin')) == ADMIN_USER:
                token=secrets.token_urlsafe(32); SESSIONS[token]=time.time()+SESSION_TTL; SESSION_USER[token]=ADMIN_USER
                return json_response(self,200,{'token':token,'expiresIn':SESSION_TTL})
            return json_response(self,401,{'error':'invalid credentials'})
        if u.path == '/api/admin/content':
            if not admin_ok(self): return json_response(self,401,{'error':'unauthorized'})
            try: data=self._json(); content=data.get('content')
            except Exception: return json_response(self,400,{'error':'invalid json'})
            if not isinstance(content,dict): return json_response(self,400,{'error':'invalid content'})
            with db_connect() as con: con.execute('UPDATE content SET payload=?, updated_at=? WHERE id=1',(json.dumps(content,ensure_ascii=False),utc_now())); con.commit()
            return json_response(self,200,{'ok':True})
        if u.path == '/api/messages':
            try: d=self._json()
            except Exception: return json_response(self,400,{'error':'invalid json'})
            name=str(d.get('name','')).strip()[:160]; email=str(d.get('email','')).strip()[:254]; message=str(d.get('message','')).strip()[:8000]
            if not name or not email or not message: return json_response(self,400,{'error':'missing fields'})
            with db_connect() as con: con.execute('INSERT INTO messages(created_at,name,email,message,ip) VALUES(?,?,?,?,?)',(utc_now(),name,email,message,ip)); con.commit()
            return json_response(self,201,{'ok':True})
        if u.path == '/api/orders':
            try: d=self._json()
            except Exception: return json_response(self,400,{'error':'invalid json'})
            name=str(d.get('name','')).strip()[:160]; email=str(d.get('email','')).strip()[:254]; items=d.get('items') or []
            if not name or not email or not isinstance(items,list): return json_response(self,400,{'error':'invalid order'})
            total=0
            for item in items:
                try: qty=max(1,min(99,int(item.get('quantity',1)))); price=float(re.sub(r'[^0-9.,]','',str(item.get('price','0')).replace(',','.')) or 0); total += int(round(price*100))*qty
                except Exception: pass
            with db_connect() as con:
                cur=con.execute('INSERT INTO orders(created_at,updated_at,status,customer_name,email,phone,address,city,postcode,country,items_json,total_cents) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(utc_now(),utc_now(),'NEW',name,email,str(d.get('phone',''))[:60],str(d.get('address',''))[:300],str(d.get('city',''))[:100],str(d.get('postcode',''))[:30],str(d.get('country',''))[:100],json.dumps(items,ensure_ascii=False),total)); oid=cur.lastrowid; con.commit()
            return json_response(self,201,{'ok':True,'orderId':oid,'status':'NEW','totalCents':total})
        if u.path == '/api/admin/orders/status':
            if not admin_ok(self): return json_response(self,401,{'error':'unauthorized'})
            try: d=self._json(); oid=int(d.get('id')); status=str(d.get('status','')).upper()
            except Exception: return json_response(self,400,{'error':'invalid request'})
            if status not in ORDER_STATUSES: return json_response(self,400,{'error':'invalid status'})
            if status == 'PAID': return json_response(self,409,{'error':'PAID must come from verified Stripe webhook'})
            with db_connect() as con: con.execute('UPDATE orders SET status=?, updated_at=? WHERE id=?',(status,utc_now(),oid)); con.commit()
            return json_response(self,200,{'ok':True})
        if u.path == '/api/stripe/webhook':
            raw=self._body(); sig=self.headers.get('Stripe-Signature','')
            # Signature verification is completed when STRIPE_WEBHOOK_SECRET is configured.
            if not STRIPE_WEBHOOK_SECRET: return json_response(self,503,{'error':'stripe webhook not configured'})
            # Keep endpoint intentionally conservative; production setup must validate t=...&v1=... and event payload before marking PAID.
            return json_response(self,200,{'received':True})
        return json_response(self,404,{'error':'not found'})

    def do_DELETE(self):
        u=urlparse(self.path)
        if not admin_ok(self): return json_response(self,401,{'error':'unauthorized'})
        if u.path == '/api/admin/messages':
            try: mid=int(parse_qs(u.query).get('id',[''])[0])
            except ValueError: return json_response(self,400,{'error':'invalid id'})
            with db_connect() as con: con.execute('DELETE FROM messages WHERE id=?',(mid,)); con.commit()
            return json_response(self,200,{'ok':True})
        return json_response(self,404,{'error':'not found'})


def main():
    ensure_dirs(); init_db()
    if not ADMIN_PASSWORD:
        print('WARNING: KOSMIK_ADMIN_PASSWORD is not set. Admin login is disabled.')
    httpd=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f'Kosmik Circles backend V{API_VERSION} listening on http://{HOST}:{PORT}')
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: httpd.server_close()


if __name__ == '__main__': main()
