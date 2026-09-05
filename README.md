# Kosmik Circles — Kosmik-Base

Sorgente ufficiale del sito Kosmik Circles.

## Stato progetto

- Versione di partenza: V1.14
- `main`: versione stabile
- `development`: branch di lavoro e test
- Roadmap: `Kosmik_Circles_Roadmap_Operativa.pdf` (gestita fuori dalla repo) e documentazione in `docs/`

## Regole di sviluppo

1. Le modifiche applicative vengono sviluppate su `development`.
2. `main` viene aggiornato solo dopo verifica e test.
3. Non committare segreti, `.env`, database locali, upload privati, virtual environment, cache o log.
4. La grafica e l'identita Kosmik Circles devono rimanere invariati salvo richieste esplicite o miglioramenti UX concordati.

## Fase 0

L'audit iniziale e documentato in `docs/PHASE_0_AUDIT.md`.

### Bloccante attuale

La cartella `backend/` e `backend/server.py` non risultano presenti nella repository. Il frontend fa riferimento alle API `/api`, quindi il backend completo della V1.14 deve essere recuperato prima di poter validare e rendere operative tutte le funzioni server-side.
