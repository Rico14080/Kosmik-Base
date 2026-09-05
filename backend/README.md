# Kosmik Circles backend

Backend V1.14 per CMS, ordini, contatti, upload e archivio Gallery. Il core usa Python standard library + SQLite.

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
- `GET /api/orders/status?id=...`
- `POST /api/admin/login`
- `GET /api/admin/stats` (Bearer token)
- `GET /api/admin/orders` (Bearer token)
- `GET /api/admin/messages` (Bearer token)
- `POST /api/admin/content` (Bearer token)
- `POST /api/admin/orders/status` (Bearer token)
- `DELETE /api/admin/messages?id=...` (Bearer token)
- API pubbliche/admin per Gallery album e media
- `POST /api/stripe/webhook`

## Produzione

I segreti devono essere configurati nell'ambiente del server e mai committati. Il database locale e gli upload sono esclusi da Git. Per accettare pagamenti reali servono dominio HTTPS, Stripe configurato e webhook verificato. Per le email serve un servizio SMTP/transazionale.
