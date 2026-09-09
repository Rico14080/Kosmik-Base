# Kosmik Circles — Kosmik-Base

Sorgente ufficiale del sito Kosmik Circles.

## Stato progetto

- `main`: baseline stabile
- `development`: sviluppo e test applicativo
- `phase-2-security-deployment-v2`: hardening sicurezza e preparazione al deployment
- `backup/pre-production-audit-20260909`: restore point pre-produzione
- Backend canonico: `backend/server.py`
- Documentazione tecnica e di produzione: `docs/`

## Struttura principale

- pagine HTML del sito: homepage, shop, cart/bag, gallery, live, contact, us e admin
- `backend/`: API Python standard-library + SQLite
- `docs/`: roadmap e controlli di produzione
- `.github/workflows/`: CI e controlli automatici

## Regole di sviluppo

1. Le modifiche applicative vengono sviluppate su `development` o su un branch dedicato.
2. `main` viene aggiornato solo dopo verifica, test e revisione.
3. Non committare segreti, `.env`, database locali, upload privati, virtual environment, cache o log.
4. La grafica e l'identità Kosmik Circles devono rimanere invariati salvo richieste esplicite o miglioramenti UX concordati.

## Controlli automatici

GitHub Actions verifica pagine e asset principali, sintassi JavaScript, compilazione Python, test di inventario/checkout e guardrail contro segreti Stripe live e file `.env`/database tracciati.

## Avanzamento

### Fase 0 — completata

Repository organizzata con branch di sviluppo, `.gitignore`, documentazione iniziale, CI e backend canonico.

### Fase 1 — completata

Hardening checkout/inventario completato. Sono coperti i casi di stock esaurito, quantità non valide, quantità oltre disponibilità e confini delle riserve. Il gate CI della Fase 1 è verde.

### Fase 2 — in corso

La checklist comprende CSP, sessioni Admin/CSRF, security headers, API hardening, deployment HTTPS/staging, Stripe test-mode, E2E e passaggio finale performance/accessibilità/SEO.

Le verifiche già presenti nel backend sono documentate in `docs/PHASE_2_SECURITY_AUDIT.md`. Restano obbligatori i test reali in staging prima di dichiarare il sito pronto per la produzione.

### Nota produzione

Stripe, SMTP, dominio, HTTPS, hosting, persistenza/backup e monitoraggio devono essere configurati con gli account esterni reali. Le credenziali devono restare fuori da Git e devono essere fornite tramite environment/secret manager del provider.
