# Kosmik Circles — Kosmik-Base

Sorgente ufficiale del sito del collettivo.

## Stato

**Pronto per configurazione e staging.** Il catalogo, CMS, Admin, inventario, checkout Stripe, webhook, backup e protezione dei file privati sono implementati. La produzione richiede ancora credenziali, contenuti reali e test con i servizi esterni.

- [Elenco verificato dei problemi e priorità](docs/PHASE_2_SECURITY_AUDIT.md)
- [Checklist unica per il lancio](docs/PRODUCTION_READINESS.md)
- [Avvio backend e API](backend/README.md)
- [Asset fotografici e ottimizzazione](docs/IMAGE_OPTIMIZATION.md)

## Struttura

- HTML, CSS e JavaScript nella radice: sito pubblico e Admin.
- `backend/server.py`: backend canonico Python standard library + SQLite.
- `backend/tests/`: test di inventario, HTTP, checkout e browser.
- `.env.example`: unico riferimento per le variabili di ambiente; non contiene credenziali.
- `docs/`: documentazione corrente.
- `.github/workflows/ci.yml`: controlli automatici.

I JPEG originali e i WebP derivati non sono copie binarie identiche: conservare gli originali finché la selezione dei media definitivi non è conclusa. I report storici rimossi restano nella cronologia Git.

## Sviluppo

`main` è la baseline pubblicata nella repository; `development` contiene la fase 1. Il lavoro più avanzato è su `phase-2-security-deployment-v2`, nella [PR #15](https://github.com/Rico14080/Kosmik-Base/pull/15). Non ricreare correzioni già presenti nelle PR precedenti.

1. Sviluppare su development o sul branch di lavoro dedicato; aggiornare main solo dopo test e revisione.
2. Mantenere l'identità grafica salvo modifiche richieste.
3. Il checkout pubblico e l'Admin usano un solo controller ciascuno: evitare script di correzione sovrapposti.
4. Non committare .env, credenziali, database, upload privati, cache o log.
5. Mantenere una sola checklist e un solo elenco dei problemi aggiornato.

## Avvio locale

Da questa cartella, PowerShell:

```powershell
$env:KOSMIK_ADMIN_PASSWORD = "SCEGLI_UNA_PASSWORD_LUNGA_E_CASUALE"
python backend/server.py
```

Aprire [sito locale](http://127.0.0.1:8080/) o [Admin](http://127.0.0.1:8080/admin.html). L'Admin è organizzato in Dashboard, Orders, Products, Content e Settings.

Il server legge le variabili dell'ambiente del processo: copiare `.env.example` in `.env` non le carica automaticamente. Per il lancio usare l'ambiente/secret manager dell'hosting.

## Verifiche locali

```text
python backend/tests/phase1_checkout_test.py
python backend/tests/production_inventory_guard_test.py
python backend/tests/checkout_api_integration_test.py
python backend/tests/security_http_regression_test.py
```

Con server avviato: `python backend/tests/smoke_test.py`. Il test browser richiede Playwright e Chromium; la CI li installa. Nessuno di questi controlli sostituisce pagamento, email, backup e verifica HTTPS in staging.

