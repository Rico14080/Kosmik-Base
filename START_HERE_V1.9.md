# KOSMIK CIRCLES V1.9 — Start here

## Local launch

PowerShell from the project root:

```powershell
$env:KOSMIK_ADMIN_PASSWORD="CHOOSE_A_LONG_RANDOM_PASSWORD"
python backend\server.py
```

Open:

- Site: `http://127.0.0.1:8080/`
- Admin: `http://127.0.0.1:8080/admin.html`

## Upgrading an existing installation

Keep these two locations from your current working site:

- `backend/data/kosmik.db`
- `backend/uploads/`

Copy the new V1.9 code over the existing project without deleting the database or uploaded images.

## Current content workflow

Admin → edit text/image → Save changes → public pages reload the server content.

## Remaining external tasks

Domain, production hosting, live Stripe credentials, production email credentials, and final legal business details are intentionally outside this local release.
