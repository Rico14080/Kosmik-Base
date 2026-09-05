# Kosmik Circles — Kosmik-Base

Sorgente ufficiale del sito Kosmik Circles.

## Stato progetto

- Versione di partenza: V1.14
- `main`: versione stabile
- `development`: branch di lavoro e test
- Roadmap: `Kosmik_Circles_Roadmap_Operativa.pdf` (gestita fuori dalla repo) e documentazione in `docs/`
- Backend canonico: `backend/server.py`

## Regole di sviluppo

1. Le modifiche applicative vengono sviluppate su `development`.
2. `main` viene aggiornato solo dopo verifica e test.
3. Non committare segreti, `.env`, database locali, upload privati, virtual environment, cache o log.
4. La grafica e l'identita Kosmik Circles devono rimanere invariati salvo richieste esplicite o miglioramenti UX concordati.

## Controlli automatici

GitHub Actions verifica la presenza delle pagine principali, la sintassi JavaScript, la compilazione delle sorgenti Python e l'assenza di segreti Stripe live e file `.env`/database tracciati.

## Fase 0 completata

La repository e' stata organizzata con branch di sviluppo separata, `.gitignore` specifico, documentazione iniziale, CI e backend V1.14 ripristinato nella posizione canonica.

## Fase 1 in corso

L'audit tecnico ha gia' individuato aree prioritarie su checkout/inventario, CSP/Admin, performance Matrix e alcuni dettagli frontend. I problemi sono tracciati nelle Issue GitHub e verranno risolti progressivamente su `development` prima del merge in `main`.

### Nota produzione

Stripe, SMTP, dominio, HTTPS e configurazione hosting restano attivita' di produzione da completare con le credenziali e gli account esterni reali.