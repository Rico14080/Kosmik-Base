# Kosmik Circles backend

Backend V2 per CMS, catalogo, ordini, contatti, upload immagine, Stripe Checkout, backup e SQLite. Il core usa solo la standard library Python.

## Avvio locale (Windows PowerShell)

```powershell
$env:KOSMIK_ADMIN_PASSWORD = "CHANGE-ME-LONG-RANDOM-PASSWORD"
python backend/server.py
```

Aprire `http://127.0.0.1:8080/`.

## API principali

- `GET /api/health`
- `GET /api/content`
- `POST /api/messages`
- `POST /api/checkout`
- `POST /api/checkout/quote`
- `GET /api/orders/status?id=...` con header `X-Order-Token`
- `POST /api/admin/login`
- `GET /api/admin/stats`
- `GET /api/admin/orders`, `/products`, `/content`, `/settings`, `/messages`
- `POST /api/admin/content`, `/products`, `/stock`, `/settings`, `/orders/status`, `/backup`
- Admin: sessione HttpOnly SameSite + token CSRF, non token Bearer
- `POST /api/stripe/webhook`

## Produzione

I segreti devono essere configurati nell'ambiente del server e mai committati. Il database locale, backup e upload sono esclusi da Git. Per accettare pagamenti reali servono dominio HTTPS, Stripe configurato e webhook verificato. Per le email serve SMTP. Il backup si crea dall'Admin oppure con `python backend/backup.py`; il ripristino deve sempre avvenire in una cartella vuota con `python backend/backup.py --restore FILE.zip --destination CARTELLA_VUOTA`.

