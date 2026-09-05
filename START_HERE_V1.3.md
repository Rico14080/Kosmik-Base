# Kosmik Circles V1.3 — Backend integrated

The visual design is intentionally unchanged. V1.3 adds a local backend, SQLite database, server-side content, contact storage, order storage and protected admin API.

## What is now real

- `/api/health`
- `/api/content`
- contact messages stored server-side
- orders stored server-side
- customer details stored server-side
- admin login/session
- admin content save/reload
- admin order status
- admin message deletion
- uploaded admin images are persisted as files instead of remaining only in browser storage

## Start on Windows

Open PowerShell in the `KosmikCircles` folder:

```powershell
$env:KOSMIK_ADMIN_PASSWORD = "CHOOSE-A-LONG-RANDOM-PASSWORD"
python backend\server.py
```

Then open:

`http://127.0.0.1:8080/`

Admin:

`http://127.0.0.1:8080/admin.html`

## Important

The order endpoint creates an `UNPAID` order. **No payment is claimed to have happened.** A real payment provider must be configured before accepting paid orders publicly.

Email delivery also needs a transactional SMTP/API provider and credentials. These are intentionally not invented or embedded in the project.
