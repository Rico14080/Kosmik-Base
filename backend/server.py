#!/usr/bin/env python3
"""KOSMIK functional MVP: stdlib HTTP, SQLite, hosted Stripe Checkout and SMTP."""
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
import threading
import time
from contextlib import closing
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
BACKEND = Path(__file__).resolve().parent
DATA = Path(os.getenv('KOSMIK_DATA_DIR', str(BACKEND / 'data'))).resolve()
UPLOADS = Path(os.getenv('KOSMIK_UPLOAD_DIR', str(BACKEND / 'uploads'))).resolve()
DB = DATA / 'kosmik.db'
HOST = os.getenv('KOSMIK_HOST', '127.0.0.1')
PORT = int(os.getenv('KOSMIK_PORT', '8080'))
ADMIN_PASSWORD = os.getenv('KOSMIK_ADMIN_PASSWORD', '')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '').strip()
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
SMTP_HOST = os.getenv('SMTP_HOST', '').strip()
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '').strip()
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_FROM = os.getenv('SMTP_FROM', '').strip()
SITE_OWNER_EMAIL = os.getenv('SITE_OWNER_EMAIL', 'gus@kosmikcircles.com').strip()
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', '1').lower() not in {'0','false','no'}
TRUSTED_PROXIES = set(filter(None, os.getenv('KOSMIK_TRUSTED_PROXIES', '').split(',')))
SESSION_TTL = 12 * 3600
STOCK_RESERVATION_TTL = 3600
MAX_BODY = 1_500_000
MAX_UPLOAD = 5 * 1024 * 1024
API_VERSION = '2.0'
RATE_LOCK = threading.Lock()
RATE_BUCKETS = {}
MAIL_LOCK = threading.Lock()

# The original CMS defaults are retained below, then migrated without losing saved text.


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

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

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

def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))

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
        print("Email delivery uncertain:", type(exc).__name__)
        return False

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

SEED_PRODUCTS = DEFAULT_CONTENT.pop('shop')
DEFAULT_CONTENT.pop('gallery', None)
DEFAULT_CONTENT['pages'].pop('gallery', None)
DEFAULT_CONTENT['siteText'].pop('gallery', None)
DEFAULT_CONTENT['siteText']['nav'].pop('gallery', None)
DEFAULT_CONTENT['siteText']['footer'].pop('galleryCta', None)
DEFAULT_CONTENT['contact']['email'] = 'gus@kosmikcircles.com'
DEFAULT_CONTENT['live'] = []
DEFAULT_CONTENT['legal'] = {'privacy':'', 'terms':'', 'shipping':'', 'returns':''}
DEFAULT_SETTINGS = {
    'domain':'kosmikcircles.com', 'businessEmail':'gus@kosmikcircles.com',
    'links':{'soundcloud':'','youtube':'','instagram':'','tiktok':'','facebook':''},
    'shipping':{'zones':[], 'freeThresholdCents':None,
                'pickupEnabled':True,'pickupAddress':'','pickupInstructions':''}
}

class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def integer(value, label='Value', minimum=0, maximum=10_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ApiError(f'{label} must be an integer between {minimum} and {maximum}')
    return value

def text(value, label='Text', maximum=4000, required=False):
    if not isinstance(value, str) or len(value) > maximum:
        raise ApiError(f'Invalid {label}')
    value=value.strip()
    if required and not value:
        raise ApiError(f'{label} is required')
    return value

def external_url(value):
    value=text(value, 'URL', 2000)
    if value and (urlparse(value).scheme != 'https' or not urlparse(value).hostname or urlparse(value).username):
        raise ApiError('Use a complete HTTPS URL')
    return value

def db():
    DATA.mkdir(parents=True, exist_ok=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB, timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def add_columns(c, table, columns):
    existing={r[1] for r in c.execute(f'PRAGMA table_info({table})')}
    for name, definition in columns.items():
        if name not in existing:
            c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')

def init_db():
    with closing(db()) as c, c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS site_content(id INTEGER PRIMARY KEY CHECK(id=1),content TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,meta TEXT,description TEXT,price_cents INTEGER NOT NULL DEFAULT 0,image TEXT,alt TEXT,stock INTEGER NOT NULL DEFAULT 0,reserved_stock INTEGER NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT NOT NULL,phone TEXT,address TEXT,city TEXT,postcode TEXT,country TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,customer_id INTEGER,email TEXT NOT NULL,total_cents INTEGER NOT NULL,status TEXT NOT NULL,payment_status TEXT NOT NULL,shipping_status TEXT NOT NULL,items_json TEXT NOT NULL,stripe_session_id TEXT,stock_applied INTEGER NOT NULL DEFAULT 0,stock_reserved INTEGER NOT NULL DEFAULT 0,reservation_expires_at TEXT,status_token TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'new',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS variants(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER NOT NULL REFERENCES products(id),sku TEXT UNIQUE NOT NULL,size TEXT NOT NULL DEFAULT '',color TEXT NOT NULL DEFAULT '',stock INTEGER NOT NULL DEFAULT 0,reserved_stock INTEGER NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stock_history(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL,variant_id INTEGER,delta INTEGER NOT NULL,reason TEXT NOT NULL,reference TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY,action TEXT NOT NULL,reference TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),content TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS webhook_events(id TEXT PRIMARY KEY,type TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS mail_outbox(id TEXT PRIMARY KEY,recipient TEXT NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
        ''')
        add_columns(c,'products',{'reserved_stock':'INTEGER NOT NULL DEFAULT 0','sku':'TEXT','version':'INTEGER NOT NULL DEFAULT 1'})
        add_columns(c,'site_content',{'version':'INTEGER NOT NULL DEFAULT 1'})
        add_columns(c,'sessions',{'csrf':'TEXT'})
        add_columns(c,'orders',{'stripe_session_id':'TEXT','stock_applied':'INTEGER NOT NULL DEFAULT 0','stock_reserved':'INTEGER NOT NULL DEFAULT 0','reservation_expires_at':'TEXT','status_token':'TEXT','payment_intent':'TEXT','checkout_url':'TEXT','request_key':'TEXT','request_hash':'TEXT','shipping_method':"TEXT NOT NULL DEFAULT 'shipping'",'shipping_cents':'INTEGER NOT NULL DEFAULT 0','tracking':"TEXT NOT NULL DEFAULT ''",'notes':"TEXT NOT NULL DEFAULT ''",'issue':"TEXT NOT NULL DEFAULT ''",'refund_id':'TEXT'})
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS order_request_key ON orders(request_key)')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS product_sku ON products(sku)')
        c.execute("UPDATE products SET sku='KC-' || id WHERE sku IS NULL OR sku=''")
        c.execute("UPDATE orders SET shipping_status=CASE WHEN status='PROCESSING' THEN 'PREPARING' WHEN status IN ('SHIPPED','DELIVERED') THEN status ELSE 'NEW' END WHERE shipping_status NOT IN ('NEW','PREPARING','SHIPPED','DELIVERED')")
        c.execute("UPDATE orders SET payment_status='PENDING' WHERE payment_status='UNPAID'")
        for row in c.execute("SELECT id FROM orders WHERE status_token IS NULL OR status_token=''").fetchall():
            c.execute('UPDATE orders SET status_token=? WHERE id=?',(new_status_token(),row['id']))
        saved=c.execute('SELECT content FROM site_content WHERE id=1').fetchone()
        content=merge_content_defaults(json.loads(saved['content']) if saved else {})
        # Migrate legacy event rows only once; camelCase is the sole public contract.
        if saved and 'live' not in json.loads(saved['content']) and c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'").fetchone():
            content['live']=[{'id':r['id'],'date':r['date'],'isoDate':r['iso_date'],'location':r['location'],'venue':r['venue'],'signal':r['signal'],'detail':r['detail'],'action':r['action'],'ticketUrl':r['ticket_url'],'past':bool(r['past']),'visible':True} for r in c.execute('SELECT * FROM events ORDER BY id')]
        for key in ('gallery','shop'): content.pop(key,None)
        content.get('pages',{}).pop('gallery',None)
        content.get('siteText',{}).pop('gallery',None)
        content.get('siteText',{}).get('nav',{}).pop('gallery',None)
        content.get('siteText',{}).get('footer',{}).pop('galleryCta',None)
        if content.get('contact',{}).get('email')=='hello@kosmikcircles.com': content['contact']['email']='gus@kosmikcircles.com'
        if saved: c.execute('UPDATE site_content SET content=? WHERE id=1',(json.dumps(content,ensure_ascii=False),))
        else: c.execute('INSERT INTO site_content(id,content,updated_at) VALUES(1,?,?)',(json.dumps(content,ensure_ascii=False),now()))
        if not c.execute('SELECT id FROM products LIMIT 1').fetchone():
            for i,p in enumerate(SEED_PRODUCTS):
                c.execute('INSERT INTO products(name,sku,meta,description,price_cents,image,alt,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(p['name'],f'KC-{i+1}',p['meta'],p['description'],price_cents(p['price']),p['image'],p['alt'],now(),now()))
        c.execute('INSERT OR IGNORE INTO settings(id,content) VALUES(1,?)',(json.dumps(DEFAULT_SETTINGS),))
        # A process that died during SMTP may already have delivered: require operator review.
        c.execute("UPDATE mail_outbox SET state='uncertain' WHERE state='sending'")

def activity(c, action, reference=''):
    c.execute('INSERT INTO activity_log(action,reference,created_at) VALUES(?,?,?)',(action,str(reference)[:200],now()))

def content_from_db(c):
    return json.loads(c.execute('SELECT content FROM site_content WHERE id=1').fetchone()['content'])

def settings_from_db(c):
    row=c.execute('SELECT * FROM settings WHERE id=1').fetchone()
    return json.loads(row['content']),row['version']

def catalog(c, admin=False):
    result=[]
    for row in c.execute('SELECT * FROM products '+('' if admin else 'WHERE active=1 ')+'ORDER BY id'):
        p=dict(row)
        p.update(priceCents=p['price_cents'],price=f"€ {p['price_cents']/100:.2f}",availableStock=max(0,p['stock']-p['reserved_stock']))
        p['variants']=[dict(v) | {'availableStock':max(0,v['stock']-v['reserved_stock'])} for v in c.execute('SELECT * FROM variants WHERE product_id=? '+('' if admin else 'AND active=1 ')+'ORDER BY id',(p['id'],))]
        p['hasVariants']=bool(c.execute('SELECT 1 FROM variants WHERE product_id=? LIMIT 1',(p['id'],)).fetchone())
        result.append(p)
    return result

def validate_tree(value, depth=0):
    if depth>8: raise ApiError('Content nesting too deep')
    if isinstance(value,dict):
        if len(value)>100: raise ApiError('Too many fields')
        for k,v in value.items():
            if k in {'__proto__','constructor','prototype'}: raise ApiError('Invalid field')
            validate_tree(v,depth+1)
    elif isinstance(value,list):
        if len(value)>100: raise ApiError('Too many rows')
        for v in value: validate_tree(v,depth+1)
    elif isinstance(value,str):
        if len(value)>20000: raise ApiError('Text too long')
    elif value is not None and type(value) not in (bool,int,float): raise ApiError('Invalid content')

def save_content(c, payload):
    section=payload.get('section')
    if section not in DEFAULT_CONTENT: raise ApiError('Unknown content section')
    value=payload.get('value')
    if type(value) is not type(DEFAULT_CONTENT[section]): raise ApiError('Invalid section type')
    validate_tree(value)
    if section=='live':
        seen=set()
        for event in value:
            if not isinstance(event,dict): raise ApiError('Invalid event')
            for key in ('title','date','isoDate','location','venue','signal','detail','action'):
                if key in event: text(event[key],key,4000)
            external_url(event.get('ticketUrl',''))
            if event.get('isoDate'):
                try: datetime.fromisoformat(event['isoDate'])
                except ValueError: raise ApiError('Invalid event date')
            if 'visible' in event and type(event['visible']) is not bool: raise ApiError('Invalid event visibility')
            event.setdefault('id',secrets.token_hex(8))
            if str(event['id']) in seen: raise ApiError('Duplicate event ID')
            seen.add(str(event['id']))
    row=c.execute('SELECT content,version FROM site_content WHERE id=1').fetchone()
    if payload.get('version')!=row['version']: raise ApiError('Content changed elsewhere. Reload before saving.',409)
    content=json.loads(row['content']);content[section]=value
    c.execute('UPDATE site_content SET content=?,version=version+1,updated_at=? WHERE id=1',(json.dumps(content,ensure_ascii=False),now()))
    activity(c,'content.save',section)
    return {'content':content,'version':row['version']+1}

def save_settings(c,payload):
    current,version=settings_from_db(c)
    if payload.get('version')!=version: raise ApiError('Settings changed elsewhere. Reload.',409)
    value=payload.get('value')
    if not isinstance(value,dict): raise ApiError('Invalid settings')
    domain=text(value.get('domain'),'domain',250,True)
    if not re.fullmatch(r'[A-Za-z0-9.-]+',domain): raise ApiError('Invalid domain')
    email=text(value.get('businessEmail'),'business email',200,True)
    if not valid_email(email): raise ApiError('Invalid email')
    links=value.get('links');shipping=value.get('shipping')
    if not isinstance(links,dict) or not isinstance(shipping,dict): raise ApiError('Invalid settings')
    clean={'domain':domain,'businessEmail':email,'links':{k:external_url(links.get(k,'')) for k in DEFAULT_SETTINGS['links']}}
    zones=shipping.get('zones',[])
    if not isinstance(zones,list) or len(zones)>50: raise ApiError('Invalid shipping zones')
    countries=set();clean_zones=[]
    for zone in zones:
        if not isinstance(zone,dict) or not isinstance(zone.get('countries'),list): raise ApiError('Invalid shipping zone')
        codes=zone['countries']
        if not codes or any(not isinstance(v,str) or not re.fullmatch('[A-Z]{2}',v) or v in countries for v in codes) or len(set(codes))!=len(codes): raise ApiError('Use distinct two-letter country codes per zone')
        countries.update(codes)
        clean_zones.append({'name':text(zone.get('name'),'zone name',100,True),'countries':codes,'priceCents':integer(zone.get('priceCents'),'Shipping price')})
    threshold=shipping.get('freeThresholdCents')
    if threshold is not None: integer(threshold,'Free shipping threshold',1)
    if type(shipping.get('pickupEnabled')) is not bool: raise ApiError('Invalid pickup switch')
    clean['shipping']={'zones':clean_zones,'freeThresholdCents':threshold,'pickupEnabled':shipping['pickupEnabled'],'pickupAddress':text(shipping.get('pickupAddress',''),'Pickup address',1000),'pickupInstructions':text(shipping.get('pickupInstructions',''),'Pickup instructions',2000)}
    c.execute('UPDATE settings SET content=?,version=version+1 WHERE id=1',(json.dumps(clean),))
    activity(c,'settings.save')
    return {'settings':clean,'version':version+1}

def save_product(c,p):
    if not isinstance(p,dict): raise ApiError('Invalid product')
    pid=p.get('id');old=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone() if pid else None
    if pid and not old: raise ApiError('Product not found',404)
    if old and p.get('version')!=old['version']: raise ApiError('Product changed elsewhere. Reload.',409)
    if type(p.get('active')) is not bool: raise ApiError('Invalid product visibility')
    values=(text(p.get('name'),'name',160,True),text(p.get('sku'),'SKU',100,True),text(p.get('meta',''),'meta',200),text(p.get('description',''),'description',5000),integer(p.get('priceCents'),'Price',1),text(p.get('image',''),'image',4000),text(p.get('alt',''),'alt',300),int(p['active']),now())
    if old:
        c.execute('UPDATE products SET name=?,sku=?,meta=?,description=?,price_cents=?,image=?,alt=?,active=?,updated_at=?,version=version+1 WHERE id=?',(*values,pid))
    else:
        pid=c.execute('INSERT INTO products(name,sku,meta,description,price_cents,image,alt,active,updated_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(*values,now())).lastrowid
    variants=p.get('variants',[])
    if not isinstance(variants,list) or len(variants)>100: raise ApiError('Invalid variants')
    if variants and old and (old['stock'] or old['reserved_stock']): raise ApiError('Set simple-product stock to zero before introducing variants')
    present=set()
    for v in variants:
        if not isinstance(v,dict) or type(v.get('active')) is not bool: raise ApiError('Invalid variant')
        vid=v.get('id')
        fields=(text(v.get('sku'),'variant SKU',100,True),text(v.get('size',''),'size',80),text(v.get('color',''),'color',80),int(v['active']),now())
        if vid:
            if vid in present or not c.execute('SELECT id FROM variants WHERE id=? AND product_id=?',(vid,pid)).fetchone(): raise ApiError('Invalid variant ID')
            c.execute('UPDATE variants SET sku=?,size=?,color=?,active=?,updated_at=? WHERE id=?',(*fields,vid))
        else: vid=c.execute('INSERT INTO variants(sku,size,color,active,updated_at,product_id) VALUES(?,?,?,?,?,?)',(*fields,pid)).lastrowid
        present.add(vid)
    for row in c.execute('SELECT id FROM variants WHERE product_id=?',(pid,)).fetchall():
        if row['id'] not in present: c.execute('UPDATE variants SET active=0 WHERE id=?',(row['id'],))
    activity(c,'product.save',pid)
    return {'id':pid}

def inventory_target(c,item,active=False):
    pid=integer(item.get('productId'),'Product ID',1)
    p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    if not p or (active and not p['active']): raise ApiError('Product unavailable',409)
    vid=item.get('variantId')
    if vid is not None:
        integer(vid,'Variant ID',1)
        row=c.execute('SELECT * FROM variants WHERE id=? AND product_id=?',(vid,pid)).fetchone()
        if not row or (active and not row['active']): raise ApiError('Variant unavailable',409)
        return 'variants',row,p
    if c.execute('SELECT 1 FROM variants WHERE product_id=? LIMIT 1',(pid,)).fetchone(): raise ApiError('Select a variant')
    return 'products',p,p

def adjust_stock(c,payload):
    table,row,p=inventory_target(c,payload)
    delta=integer(payload.get('delta'),'Stock adjustment',-1_000_000,1_000_000)
    reason=text(payload.get('reason'),'reason',500,True)
    if row['stock']+delta<row['reserved_stock']: raise ApiError('Stock cannot be below reserved quantity',409)
    c.execute(f'UPDATE {table} SET stock=stock+?,updated_at=? WHERE id=?',(delta,now(),row['id']))
    c.execute('INSERT INTO stock_history(product_id,variant_id,delta,reason,reference,created_at) VALUES(?,?,?,?,?,?)',(p['id'],payload.get('variantId'),delta,reason,'admin',now()))
    activity(c,'stock.adjust',f"{p['id']}:{payload.get('variantId')} {delta:+d}")
    return {'ok':True}

def aggregate_items(items):
    if not isinstance(items,list) or not 1<=len(items)<=50: raise ApiError('Cart must contain 1 to 50 rows')
    grouped={}
    for item in items:
        if not isinstance(item,dict): raise ApiError('Invalid cart item')
        pid=integer(item.get('productId'),'Product ID',1);vid=item.get('variantId')
        if vid is not None: integer(vid,'Variant ID',1)
        qty=integer(item.get('quantity'),'Quantity',1,99)
        key=(pid,vid)
        if key not in grouped: grouped[key]=dict(item,productId=pid,variantId=vid,quantity=0)
        grouped[key]['quantity']+=qty
        integer(grouped[key]['quantity'],'Combined quantity',1,99)
    return list(grouped.values())

def authoritative_items(c,items):
    result=[]
    for item in aggregate_items(items):
        table,row,p=inventory_target(c,item,True)
        if row['stock']-row['reserved_stock']<item['quantity']: raise ApiError(f"Insufficient stock: {p['name']}",409)
        result.append({'productId':p['id'],'variantId':item['variantId'],'name':p['name'],'sku':row['sku'],'variant':(' / '.join(filter(None,[row['size'],row['color']])) if table=='variants' else ''),'quantity':item['quantity'],'priceCents':p['price_cents'],'image':p['image'] or ''})
    return result

def reservation_expiry():
    return datetime.fromtimestamp(int(time.time())+STOCK_RESERVATION_TTL,timezone.utc).isoformat()

def reserve_order_stock(c,items):
    if not c.in_transaction: c.execute('BEGIN IMMEDIATE')
    items[:]=aggregate_items(items)
    for item in items:
        table,row,p=inventory_target(c,item,True)
        qty=item['quantity']
        if row['stock']-row['reserved_stock']<qty: raise ApiError(f"Insufficient stock: {p['name']}",409)
    for item in items:
        table,row,p=inventory_target(c,item)
        c.execute(f'UPDATE {table} SET reserved_stock=reserved_stock+?,updated_at=? WHERE id=?',(item['quantity'],now(),row['id']))
    return reservation_expiry()

def release_order_reservation(c,oid):
    row=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
    if not row or not row['stock_reserved']: return False
    for item in aggregate_items(json.loads(row['items_json'])):
        table,stock,p=inventory_target(c,item)
        c.execute(f'UPDATE {table} SET reserved_stock=MAX(0,reserved_stock-?),updated_at=? WHERE id=?',(item['quantity'],now(),stock['id']))
    c.execute('UPDATE orders SET stock_reserved=0,reservation_expires_at=NULL,updated_at=? WHERE id=?',(now(),oid))
    return True

def release_expired_reservations(c):
    # A local clock is not proof that Stripe cannot still charge. Release only after
    # signed expiration/failed events or explicit provider reconciliation.
    return 0

def queue_mail(c,key,recipient,subject,body):
    c.execute('INSERT OR IGNORE INTO mail_outbox(id,recipient,subject,body,updated_at) VALUES(?,?,?,?,?)',(key,recipient,subject,body,now()))

def apply_paid_order(c,oid,session_id=''):
    if not c.in_transaction: c.execute('BEGIN IMMEDIATE')
    row=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
    if not row: return False
    if row['stock_applied'] or row['payment_status']=='REFUNDED': return True
    items=aggregate_items(json.loads(row['items_json']))
    c.execute('SAVEPOINT payment_stock')
    try:
        for item in items:
            table,stock,p=inventory_target(c,item)
            qty=item['quantity'];owned=qty if row['stock_reserved'] else 0
            if stock['stock']<qty or stock['reserved_stock']<owned or stock['stock']-stock['reserved_stock']+owned<qty: raise ApiError('Payment received without sufficient stock')
            c.execute(f'UPDATE {table} SET stock=stock-?,reserved_stock=reserved_stock-?,updated_at=? WHERE id=?',(qty,owned,now(),stock['id']))
            c.execute('INSERT INTO stock_history(product_id,variant_id,delta,reason,reference,created_at) VALUES(?,?,?,?,?,?)',(p['id'],item.get('variantId'),-qty,'sale',oid,now()))
        c.execute("UPDATE orders SET status=CASE WHEN status IN ('SHIPPED','DELIVERED','PROCESSING') THEN status ELSE 'PAID' END,payment_status='PAID',stock_applied=1,stock_reserved=0,reservation_expires_at=NULL,issue='',updated_at=? WHERE id=?",(now(),oid))
        c.execute('RELEASE payment_stock')
    except ApiError:
        c.execute('ROLLBACK TO payment_stock');c.execute('RELEASE payment_stock')
        c.execute("UPDATE orders SET payment_status='PAID',issue='PAID_WITHOUT_STOCK',updated_at=? WHERE id=?",(now(),oid))
        settings,_=settings_from_db(c)
        queue_mail(c,oid+':exception',settings['businessEmail'],'Order requires attention: '+oid,'Payment received, inventory could not be allocated. Review before fulfillment.')
        return False
    settings,_=settings_from_db(c)
    body=f"Order {oid}\n"+'\n'.join(f"{i['quantity']} × {i['name']} ({i.get('sku','')})" for i in items)+f"\nTotal EUR {row['total_cents']/100:.2f}\nDelivery: {row['shipping_method']}"
    if row['shipping_method']=='pickup': body+='\n'+settings['shipping']['pickupAddress']+'\n'+settings['shipping']['pickupInstructions']
    queue_mail(c,oid+':customer',row['email'],'KOSMIK order confirmed: '+oid,body)
    queue_mail(c,oid+':owner',settings['businessEmail'],'New KOSMIK order: '+oid,body+'\nSee Admin for the delivery address.')
    return True

def payments_enabled():
    return bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET and urlparse(PUBLIC_BASE_URL).scheme=='https' and urlparse(PUBLIC_BASE_URL).hostname)

def stripe_request(method,endpoint,params=None,idempotency_key=None):
    if not STRIPE_SECRET_KEY: raise ApiError('Payment provider is not configured',503)
    req=Request('https://api.stripe.com/v1/'+endpoint,data=urlencode(params or {}).encode() if method=='POST' else None,method=method)
    req.add_header('Authorization','Bearer '+STRIPE_SECRET_KEY)
    req.add_header('Content-Type','application/x-www-form-urlencoded')
    if idempotency_key: req.add_header('Idempotency-Key',idempotency_key)
    try:
        with urlopen(req,timeout=20) as r: return json.loads(r.read(MAX_BODY))
    except (HTTPError,URLError,TimeoutError,ValueError): raise ApiError('Payment provider temporarily unavailable. Retry with the same cart.',503)

def create_stripe_checkout(oid,email,items):
    with closing(db()) as c: row=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
    params={'mode':'payment','customer_email':email,'payment_method_types[0]':'card','success_url':f'{PUBLIC_BASE_URL}/cart.html?payment=success&order={oid}','cancel_url':f'{PUBLIC_BASE_URL}/cart.html?payment=cancelled&order={oid}','metadata[order_id]':oid,'payment_intent_data[metadata][order_id]':oid,'expires_at':int(datetime.fromisoformat(row['reservation_expires_at']).timestamp())}
    lines=list(items)
    if row['shipping_cents']: lines.append({'quantity':1,'priceCents':row['shipping_cents'],'name':'Shipping'})
    for i,item in enumerate(lines):
        prefix=f'line_items[{i}]'
        params.update({prefix+'[quantity]':item['quantity'],prefix+'[price_data][currency]':'eur',prefix+'[price_data][unit_amount]':item['priceCents'],prefix+'[price_data][product_data][name]':item['name']+(' / '+item['variant'] if item.get('variant') else '')})
    return stripe_request('POST','checkout/sessions',params,'checkout:'+oid)

def validate_customer(payload):
    data=payload.get('customer')
    if not isinstance(data,dict): raise ApiError('Customer details are required')
    method=payload.get('shippingMethod','shipping')
    if method not in ('shipping','pickup'): raise ApiError('Invalid delivery method')
    out={k:text(data.get(k,''),k,250,k=='name' or (method=='shipping' and k in ('address','city','postcode','country'))) for k in ('name','phone','address','city','postcode','country')}
    email=text(payload.get('email'),'email',200,True)
    if not valid_email(email): raise ApiError('Invalid email')
    out['country']=out['country'].upper()
    if method=='shipping' and not re.fullmatch('[A-Z]{2}',out['country']): raise ApiError('Country must be a two-letter code, e.g. IT')
    return out,email,method

def shipping_cost(settings,customer,method,subtotal):
    s=settings['shipping']
    if method=='pickup':
        if not s['pickupEnabled'] or not s['pickupAddress'] or not s['pickupInstructions']: raise ApiError('Local pickup is not configured',409)
        return 0
    zone=next((z for z in s['zones'] if customer['country'] in z['countries']),None)
    if not zone: raise ApiError('Shipping is not configured for this country',409)
    return 0 if s['freeThresholdCents'] is not None and subtotal>=s['freeThresholdCents'] else zone['priceCents']

def checkout(payload,quote=False):
    customer,email,method=validate_customer(payload)
    if not quote and not payments_enabled(): raise ApiError('Checkout is unavailable until payment configuration is complete. Your cart is retained.',503)
    key=payload.get('requestKey','')
    if not quote and (not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{20,100}',key)): raise ApiError('Invalid checkout request key')
    digest=hashlib.sha256(json.dumps({'customer':customer,'email':email,'method':method,'items':aggregate_items(payload.get('items'))},sort_keys=True).encode()).hexdigest()
    with closing(db()) as c,c:
        c.execute('BEGIN IMMEDIATE')
        existing=c.execute('SELECT * FROM orders WHERE request_key=?',(key,)).fetchone() if not quote else None
        if existing:
            if existing['request_hash']!=digest: raise ApiError('This checkout key belongs to a different cart',409)
            if existing['payment_status']!='PENDING': raise ApiError('Checkout is already finalized. Check the order status.',409)
            row=dict(existing);items=json.loads(row['items_json'])
        else:
            items=authoritative_items(c,payload.get('items'))
            subtotal=sum(i['priceCents']*i['quantity'] for i in items)
            settings,_=settings_from_db(c);delivery=shipping_cost(settings,customer,method,subtotal)
            if quote: return {'items':items,'subtotalCents':subtotal,'shippingCents':delivery,'totalCents':subtotal+delivery}
            expiry=reserve_order_stock(c,items);oid='KC-'+secrets.token_hex(8).upper();token=new_status_token()
            cid=c.execute('INSERT INTO customers(name,email,phone,address,city,postcode,country,created_at) VALUES(?,?,?,?,?,?,?,?)',(customer['name'],email,customer['phone'],customer['address'],customer['city'],customer['postcode'],customer['country'],now())).lastrowid
            c.execute("INSERT INTO orders(id,customer_id,email,total_cents,status,payment_status,shipping_status,items_json,stock_reserved,reservation_expires_at,status_token,created_at,updated_at,request_key,request_hash,shipping_method,shipping_cents) VALUES(?,?,?,?,'NEW','PENDING','NEW',?,?,?,?,?,?,?,?,?,?)",(oid,cid,email,subtotal+delivery,json.dumps(items),sum(i['quantity'] for i in items),expiry,token,now(),now(),key,digest,method,delivery))
            row=dict(c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone())
    if row['checkout_url']: return {'orderId':row['id'],'statusToken':row['status_token'],'checkoutUrl':row['checkout_url']}
    session=create_stripe_checkout(row['id'],email,items)
    if not session.get('id') or urlparse(session.get('url','')).hostname!='checkout.stripe.com': raise ApiError('Invalid payment provider response',503)
    with closing(db()) as c,c:
        c.execute('UPDATE orders SET stripe_session_id=?,checkout_url=?,updated_at=? WHERE id=?',(session['id'],session['url'],now(),row['id']))
    return {'orderId':row['id'],'statusToken':row['status_token'],'checkoutUrl':session['url']}

def process_webhook(c,event):
    eid=text(event.get('id'),'event ID',200,True);kind=text(event.get('type'),'event type',200,True)
    if c.execute('SELECT id FROM webhook_events WHERE id=?',(eid,)).fetchone(): return
    obj=event.get('data',{}).get('object',{})
    if not isinstance(obj,dict): raise ApiError('Invalid webhook object')
    oid=obj.get('metadata',{}).get('order_id')
    row=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone() if isinstance(oid,str) else None
    if kind.startswith('checkout.session.') and row:
        if row['stripe_session_id'] and row['stripe_session_id']!=obj.get('id'): raise ApiError('Session mismatch',409)
        c.execute('UPDATE orders SET stripe_session_id=?,payment_intent=COALESCE(?,payment_intent) WHERE id=?',(obj.get('id'),obj.get('payment_intent'),oid))
        if kind in ('checkout.session.completed','checkout.session.async_payment_succeeded') and obj.get('payment_status')=='paid':
            if obj.get('amount_total')!=row['total_cents'] or obj.get('currency')!='eur':
                c.execute("UPDATE orders SET issue='PAYMENT_AMOUNT_MISMATCH' WHERE id=?",(oid,))
            else: apply_paid_order(c,oid,obj.get('id',''))
        elif kind in ('checkout.session.expired','checkout.session.async_payment_failed') and row['payment_status']=='PENDING':
            release_order_reservation(c,oid)
            c.execute("UPDATE orders SET payment_status='FAILED',status='CANCELLED',updated_at=? WHERE id=?",(now(),oid))
    elif kind=='charge.refunded':
        row=c.execute('SELECT * FROM orders WHERE payment_intent=?',(obj.get('payment_intent'),)).fetchone()
        if row:
            if obj.get('refunded') is True and obj.get('amount_refunded')==row['total_cents']:
                c.execute("UPDATE orders SET payment_status='REFUNDED',updated_at=? WHERE id=?",(now(),row['id']))
            else: c.execute("UPDATE orders SET issue='PARTIAL_REFUND_REVIEW' WHERE id=?",(row['id'],))
    c.execute('INSERT INTO webhook_events VALUES(?,?,?)',(eid,kind,now()))

def flush_mail():
    if not SMTP_HOST or not SMTP_FROM or not MAIL_LOCK.acquire(False): return
    try:
        with closing(db()) as c,c:
            c.execute('BEGIN IMMEDIATE')
            rows=c.execute("SELECT * FROM mail_outbox WHERE state='pending' LIMIT 10").fetchall()
            for row in rows: c.execute("UPDATE mail_outbox SET state='sending',attempts=attempts+1,updated_at=? WHERE id=?",(now(),row['id']))
        for row in rows:
            success=send_mail(row['subject'],row['body'],row['recipient'])
            with closing(db()) as c,c: c.execute('UPDATE mail_outbox SET state=?,updated_at=? WHERE id=?',('sent' if success else 'uncertain',now(),row['id']))
    finally: MAIL_LOCK.release()

def maintenance():
    while True:
        try:
            flush_mail()
            if STRIPE_SECRET_KEY:
                with closing(db()) as c: rows=c.execute("SELECT * FROM orders WHERE payment_status='PENDING' AND stripe_session_id IS NOT NULL AND reservation_expires_at<? LIMIT 10",(now(),)).fetchall()
                for row in rows:
                    session=stripe_request('GET','checkout/sessions/'+row['stripe_session_id'])
                    kind='checkout.session.completed' if session.get('payment_status')=='paid' else ('checkout.session.expired' if session.get('status')=='expired' else None)
                    if kind:
                        with closing(db()) as c,c:
                            c.execute('BEGIN IMMEDIATE');process_webhook(c,{'id':'reconcile:'+row['stripe_session_id']+':'+kind,'type':kind,'data':{'object':session}})
        except Exception as exc: print('Maintenance needs attention:',type(exc).__name__)
        time.sleep(30)

def rate_limited(scope,client,limit,window):
    current=time.time()
    with RATE_LOCK:
        for key in list(RATE_BUCKETS):
            if not RATE_BUCKETS[key] or current-RATE_BUCKETS[key][-1]>600: RATE_BUCKETS.pop(key,None)
        key=(scope,client);values=[v for v in RATE_BUCKETS.get(key,[]) if current-v<window]
        if len(values)>=limit: return True
        if len(RATE_BUCKETS)>20000: return True
        values.append(current);RATE_BUCKETS[key]=values
        return False

def send(handler,status,obj,headers=None):
    body=json.dumps(obj,ensure_ascii=False).encode()
    handler.send_response(status);handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Content-Length',str(len(body)));handler.send_header('Cache-Control','no-store')
    for k,v in (headers or {}).items(): handler.send_header(k,v)
    handler.end_headers()
    if handler.command!='HEAD': handler.wfile.write(body)

PUBLIC_FILES={'index.html','shop.html','cart.html','live.html','contact.html','us.html','legal.html','admin.html','404.html','site.js','admin.js','style.css','admin.css','site.webmanifest','robots.txt','security.txt','sitemap.xml'}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def setup(self):
        super().setup();self.connection.settimeout(15)
    def log_message(self,fmt,*args):
        print(self.client_address[0],self.command,urlparse(self.path).path) # never log query tokens or form data
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','SAMEORIGIN')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy',"default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self'; connect-src 'self'; form-action 'self' https://checkout.stripe.com")
        if PUBLIC_BASE_URL.startswith('https://'): self.send_header('Strict-Transport-Security','max-age=31536000')
        super().end_headers()
    def client_ip(self):
        ip=self.client_address[0]
        return self.headers.get('X-Forwarded-For',ip).split(',')[-1].strip() if ip in TRUSTED_PROXIES else ip
    def limit(self,scope,count,window=600):
        if rate_limited(scope,self.client_ip(),count,window): raise ApiError('Too many requests. Try again later.',429)
    def raw_body(self,maximum=MAX_BODY):
        if self.headers.get('Transfer-Encoding'): raise ApiError('Transfer encoding is not supported',400)
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ApiError('Invalid content length')
        if length<=0: raise ApiError('Empty request body')
        if length>maximum:
            self.close_connection=True;raise ApiError('Payload too large',413)
        return self.rfile.read(length)
    def read_json(self):
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json': raise ApiError('Content-Type must be application/json',415)
        try: value=json.loads(self.raw_body())
        except (ValueError,UnicodeError): raise ApiError('Invalid JSON')
        if not isinstance(value,dict): raise ApiError('JSON body must be an object')
        return value
    def session(self,mutation=False):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: return None
        token=cookie.get('kosmik_session')
        if not token: return None
        digest=hashlib.sha256(token.value.encode()).hexdigest()
        with closing(db()) as c: row=c.execute('SELECT * FROM sessions WHERE token=? AND expires_at>?',(digest,int(time.time()))).fetchone()
        if row and mutation and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),row['csrf'] or ''): raise ApiError('Invalid CSRF token',403)
        return row
    def guard(self,mutation=False):
        row=self.session(mutation)
        if not row: raise ApiError('Sign in required',401)
        return row
    def static_target(self):
        raw=urlparse(self.path).path
        path=unquote(raw)
        if '%' in path or '\\' in path or '\x00' in path or any(p in ('.','..') or p.startswith('.') for p in path.split('/') if p): return None
        if path=='/': path='/index.html'
        if path.startswith('/backend/uploads/'):
            name=path.removeprefix('/backend/uploads/')
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp|gif)',name,re.I): return None
            base=UPLOADS
        else:
            name=path.lstrip('/')
            if '/' in name: return None
            if name not in PUBLIC_FILES and not re.fullmatch(r'WhatsApp Image 2026-08-11 at 00\.52\.13(?: \(\d+\))?\.(?:jpeg|webp)',name): return None
            base=ROOT
        target=(base/name).resolve()
        if target.parent!=base.resolve() or not target.is_file(): return None
        return target
    def do_HEAD(self): self.do_GET()
    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_DELETE(self): send(self,405,{'error':'Method not allowed'})
    def dispatch(self,method):
        try: self.route(method)
        except ApiError as exc: send(self,exc.status,{'error':str(exc)})
        except sqlite3.IntegrityError: send(self,409,{'error':'Conflicting identifier or existing record'})
        except (ValueError,TypeError,KeyError,AttributeError): send(self,400,{'error':'Invalid request data'})
        except (BrokenPipeError,ConnectionResetError,TimeoutError): self.close_connection=True
        except Exception as exc:
            print('Request failed:',type(exc).__name__);send(self,500,{'error':'Service error. Please retry.'})
    def route(self,method):
        path=urlparse(self.path).path
        if method=='GET' and not path.startswith('/api/'):
            target=self.static_target()
            if not target: return send(self,404,{'error':'Not found'})
            self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(target.stat().st_size));self.send_header('Cache-Control','no-cache');self.end_headers()
            if self.command!='HEAD':
                with target.open('rb') as f:
                    while chunk:=f.read(65536): self.wfile.write(chunk)
            return
        if path.startswith('/api/gallery') or path.startswith('/api/admin/gallery'): raise ApiError('Not found',404)
        if method=='GET':
            if path=='/api/health':
                with closing(db()) as c: c.execute('SELECT 1').fetchone()
                return send(self,200,{'ok':True,'version':API_VERSION})
            if path=='/api/config':
                with closing(db()) as c: settings,_=settings_from_db(c)
                return send(self,200,{'paymentsEnabled':payments_enabled(),'paymentProvider':'stripe' if payments_enabled() else None,'shipping':settings['shipping'],'links':settings['links'],'businessEmail':settings['businessEmail']})
            if path=='/api/content':
                with closing(db()) as c:
                    content=content_from_db(c);content['shop']=catalog(c);content['live']=[e for e in content.get('live',[]) if e.get('visible',True)]
                    settings,_=settings_from_db(c);content['links']=settings['links']
                return send(self,200,content)
            if path=='/api/orders/status':
                query=parse_qs(urlparse(self.path).query);oid=query.get('id',[''])[0]
                token=self.headers.get('X-Order-Token','')
                if not oid or not token: raise ApiError('Missing order credentials')
                with closing(db()) as c: row=c.execute('SELECT id,payment_status,shipping_status,issue FROM orders WHERE id=? AND status_token=?',(oid,token)).fetchone()
                if not row: raise ApiError('Order not found',404)
                return send(self,200,{'orderId':row['id'],'paymentStatus':row['payment_status'],'fulfillmentStatus':row['shipping_status'],'needsReview':bool(row['issue'])})
            if path.startswith('/api/admin/'):
                session=self.guard()
                with closing(db()) as c:
                    if path=='/api/admin/session': result={'csrfToken':session['csrf']}
                    elif path=='/api/admin/content':
                        row=c.execute('SELECT * FROM site_content WHERE id=1').fetchone();result={'content':json.loads(row['content']),'version':row['version']}
                    elif path=='/api/admin/products': result={'products':catalog(c,True),'history':[dict(r) for r in c.execute('SELECT * FROM stock_history ORDER BY id DESC LIMIT 100')]}
                    elif path=='/api/admin/settings':
                        settings,version=settings_from_db(c);result={'settings':settings,'version':version}
                    elif path=='/api/admin/orders': result={'orders':[dict(r)|{'items':json.loads(r['items_json'])} for r in c.execute('SELECT o.*,c.name,c.phone,c.address,c.city,c.postcode,c.country FROM orders o LEFT JOIN customers c ON c.id=o.customer_id ORDER BY o.created_at DESC LIMIT 500')]}
                    elif path=='/api/admin/messages': result={'messages':[dict(r) for r in c.execute('SELECT * FROM messages ORDER BY created_at DESC LIMIT 100')]}
                    elif path=='/api/admin/stats': result=dashboard(c)
                    else: raise ApiError('Not found',404)
                return send(self,200,result)
            raise ApiError('Not found',404)
        if path=='/api/stripe/webhook':
            raw=self.raw_body()
            if not verify_stripe_signature(raw,self.headers.get('Stripe-Signature','')): raise ApiError('Invalid signature',400)
            try: event=json.loads(raw)
            except ValueError: raise ApiError('Invalid event')
            if not isinstance(event,dict): raise ApiError('Invalid event')
            with closing(db()) as c,c:
                c.execute('BEGIN IMMEDIATE');process_webhook(c,event)
            return send(self,200,{'received':True})
        if path=='/api/admin/upload':
            self.guard(True);raw=self.raw_body(MAX_UPLOAD)
            mime=self.headers.get('Content-Type','').split(';')[0]
            formats={'image/png':('png',raw.startswith(b'\x89PNG\r\n\x1a\n')),'image/jpeg':('jpg',raw.startswith(b'\xff\xd8\xff')),'image/webp':('webp',raw[:4]==b'RIFF' and raw[8:12]==b'WEBP'),'image/gif':('gif',raw[:6] in (b'GIF87a',b'GIF89a'))}
            if mime not in formats or not formats[mime][1]: raise ApiError('Supported image required',415)
            name='image-'+secrets.token_hex(12)+'.'+formats[mime][0];(UPLOADS/name).write_bytes(raw)
            return send(self,201,{'url':'/backend/uploads/'+name})
        data=self.read_json()
        if path=='/api/admin/login':
            self.limit('login',8,300)
            password=data.get('password')
            if not ADMIN_PASSWORD: raise ApiError('Admin password is not configured',503)
            if not isinstance(password,str) or not hmac.compare_digest(password,ADMIN_PASSWORD): raise ApiError('Invalid credentials',401)
            token=new_status_token();csrf=new_status_token()
            with closing(db()) as c,c:
                c.execute('DELETE FROM sessions WHERE expires_at<?',(int(time.time()),))
                c.execute('INSERT INTO sessions(token,expires_at,csrf) VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),int(time.time())+SESSION_TTL,csrf))
                activity(c,'admin.login')
            cookie=f'kosmik_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}'+('; Secure' if PUBLIC_BASE_URL.startswith('https://') else '')
            return send(self,200,{'csrfToken':csrf},{'Set-Cookie':cookie})
        if path in ('/api/checkout','/api/checkout/quote'):
            self.limit('checkout',30)
            return send(self,200 if path.endswith('/quote') else 201,checkout(data,path.endswith('/quote')))
        if path=='/api/messages':
            self.limit('contact',5)
            if data.get('website'): return send(self,200,{'ok':True})
            name=text(data.get('name'),'name',120,True);email=text(data.get('email'),'email',200,True);message=text(data.get('message'),'message',4000,True)
            if not valid_email(email): raise ApiError('Invalid email')
            mid='MSG-'+secrets.token_hex(8)
            with closing(db()) as c,c:
                c.execute('INSERT INTO messages(id,name,email,message,created_at) VALUES(?,?,?,?,?)',(mid,name,email,message,now()))
                settings,_=settings_from_db(c);queue_mail(c,mid,settings['businessEmail'],'KOSMIK contact message',name+'\n'+email+'\n'+message)
            return send(self,201,{'ok':True})
        if path.startswith('/api/admin/'):
            session=self.guard(True)
            if path=='/api/admin/backup':
                from backup import create_backup
                name=create_backup(DB,UPLOADS,DATA/'backups')
                with closing(db()) as c,c: activity(c,'backup.create',name.name)
                return send(self,200,{'ok':True,'createdAt':now()})
            with closing(db()) as c,c:
                c.execute('BEGIN IMMEDIATE')
                if path=='/api/admin/logout':
                    c.execute('DELETE FROM sessions WHERE token=?',(session['token'],));return send(self,200,{'ok':True},{'Set-Cookie':'kosmik_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
                if path=='/api/admin/content': result=save_content(c,data)
                elif path=='/api/admin/settings': result=save_settings(c,data)
                elif path=='/api/admin/products': result=save_product(c,data)
                elif path=='/api/admin/stock': result=adjust_stock(c,data)
                elif path=='/api/admin/orders/status':
                    oid=text(data.get('orderId'),'order ID',80,True);status=data.get('fulfillmentStatus')
                    if status not in ('NEW','PREPARING','SHIPPED','DELIVERED'): raise ApiError('Invalid fulfillment status')
                    row=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
                    if not row: raise ApiError('Order not found',404)
                    if row['payment_status']!='PAID' or row['issue']: raise ApiError('Only paid orders without issues can be fulfilled',409)
                    c.execute('UPDATE orders SET shipping_status=?,tracking=?,notes=?,updated_at=? WHERE id=?',(status,text(data.get('tracking',''),'tracking',500),text(data.get('notes',''),'notes',4000),now(),oid));activity(c,'order.fulfillment',oid);result={'ok':True}
                elif path=='/api/admin/mail/retry':
                    if data.get('confirm') is not True: raise ApiError('Confirm retry: an uncertain message may already have been delivered')
                    mid=text(data.get('id'),'message ID',150,True)
                    c.execute("UPDATE mail_outbox SET state='pending' WHERE id=? AND state='uncertain'",(mid,));activity(c,'mail.retry',mid);result={'ok':True}
                else: raise ApiError('Not found',404)
            return send(self,200,result)
        raise ApiError('Not found',404)

def dashboard(c):
    def count(sql): return c.execute(sql).fetchone()[0]
    backups=sorted((DATA/'backups').glob('*.zip'),key=lambda p:p.stat().st_mtime) if (DATA/'backups').exists() else []
    return {'orders':count('SELECT COUNT(*) FROM orders'),'unpaid':count("SELECT COUNT(*) FROM orders WHERE payment_status='PENDING'"),'issues':count("SELECT COUNT(*) FROM orders WHERE issue!='' OR (payment_status='PENDING' AND reservation_expires_at<'"+now()+"')"),'toProcess':count("SELECT COUNT(*) FROM orders WHERE payment_status='PAID' AND shipping_status='NEW'"),'toShip':count("SELECT COUNT(*) FROM orders WHERE payment_status='PAID' AND shipping_status='PREPARING'"),'lowStock':count('SELECT COUNT(*) FROM products WHERE active=1 AND stock-reserved_stock BETWEEN 1 AND 3 AND NOT EXISTS(SELECT 1 FROM variants WHERE product_id=products.id)')+count('SELECT COUNT(*) FROM variants WHERE active=1 AND stock-reserved_stock BETWEEN 1 AND 3'),'soldOut':count('SELECT COUNT(*) FROM products WHERE active=1 AND stock-reserved_stock<=0 AND NOT EXISTS(SELECT 1 FROM variants WHERE product_id=products.id)')+count('SELECT COUNT(*) FROM variants WHERE active=1 AND stock-reserved_stock<=0'),'services':{'website':'responding','stripe':'configured; provider test required' if payments_enabled() else 'not configured','email':'configured; delivery test required' if SMTP_HOST and SMTP_FROM else 'not configured','database':'SQLite / responding','version':API_VERSION,'lastBackup':datetime.fromtimestamp(backups[-1].stat().st_mtime,timezone.utc).isoformat() if backups else None},'activity':[dict(r) for r in c.execute('SELECT * FROM activity_log ORDER BY id DESC LIMIT 30')],'mail':[dict(r) for r in c.execute("SELECT id,recipient,state,attempts,updated_at FROM mail_outbox WHERE state!='sent' ORDER BY updated_at DESC LIMIT 50")],'recentOrders':[dict(r) for r in c.execute('SELECT id,payment_status,shipping_status,total_cents,issue FROM orders ORDER BY created_at DESC LIMIT 10')]}

if __name__=='__main__':
    init_db()
    threading.Thread(target=maintenance,daemon=True).start()
    print(f'KOSMIK {API_VERSION}: http://{HOST}:{PORT}')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

