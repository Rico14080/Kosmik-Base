# Kosmik Circles — production setup

The V1.14 backend is designed to run behind an HTTPS reverse proxy. Do not put secrets in Git or the frontend.

## Required environment

- `KOSMIK_ADMIN_PASSWORD`: long random admin password.
- `PUBLIC_BASE_URL`: final HTTPS site origin.

## Optional until launch

- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `SITE_OWNER_EMAIL`.

## Stripe webhook

Configure `/api/stripe/webhook` for `checkout.session.completed`. The V1.14 backend verifies the Stripe signature before applying the paid state.

## Backups

Run `python backend/backup.py` before upgrades or deployments. Keep backups outside the public web root and preferably on separate storage.
