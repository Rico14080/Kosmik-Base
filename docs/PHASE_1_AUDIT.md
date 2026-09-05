# Kosmik Circles — Fase 1 Audit Tecnico

Data: 2026-09-05
Branch di lavoro: `development`
Base stabile: `main`

## Stato della V1.14

Il backend V1.14 e' ora presente in `backend/server.py` usando lo stesso contenuto del backend caricato nella V1.14 originale. La compilazione Python locale ha avuto esito positivo e la CI GitHub sul commit di ripristino ha restituito `success`.

## Smoke test locali eseguiti

Verificati con backend avviato localmente:

- `/api/health`
- `/api/content`
- protezione Admin senza sessione
- login Admin
- statistiche Admin
- upload immagine
- creazione cartella Gallery
- upload media Gallery
- elenco pubblico Gallery
- dettaglio album pubblico
- creazione ordine non pagato con Stripe disattivato
- stato ordine
- cancellazione media Gallery
- cancellazione album Gallery
- logout

Tutti i test sopra hanno restituito `PASS`.

## Prime criticita' tecniche

### Alta priorita' — Inventario / checkout
Il checkout considera `stock=0` come non limitante, perche' la verifica server-side viene applicata solo quando `stock > 0`. Questa semantica non e' sicura finche' non viene definito esplicitamente cosa significhi `0`.

Inoltre, con Stripe, lo stock non viene riservato alla creazione della Checkout Session ma applicato al pagamento tramite webhook. Cio' puo' generare overselling o un pagamento acquisito senza disponibilita' nel caso di ordini concorrenti.

Issue: #5.

### Media / upload
La gestione dei file usa allow-list di MIME, verifica firme dei file, nomi sanificati e limiti di dimensione. Va completata con test di abuso e limiti coerenti a livello reverse proxy/hosting.

### Admin / CSP
`admin.html` contiene ancora uno script inline e stili inline/dinamici; la CSP del backend mantiene `unsafe-inline`. E' possibile migliorare la politica spostando lo script Admin in un file esterno e riducendo progressivamente le eccezioni CSP.

Issue: #6.

### Sessioni Admin
Le sessioni sono server-side con token casuale e scadenza. Nel browser il token viene mantenuto in `sessionStorage`; per produzione va valutata una sessione cookie-based con attributi Secure/HttpOnly/SameSite e una strategia CSRF coerente.

### HTTPS / HSTS
HSTS viene inviato solo quando il backend riceve `X-Forwarded-Proto: https`. La corretta configurazione del reverse proxy dovra' essere verificata in fase produzione.

### Performance
Il Matrix effect usa un `requestAnimationFrame` continuo sulle pagine desktop. E' gia' presente una riduzione su schermi stretti e rispetto a `prefers-reduced-motion`, ma in produzione conviene fermare il loop quando la pagina non e' visibile e valutare un budget CPU piu' conservativo.

## Frontend

Entry point confermati:

`index.html`, `shop.html`, `cart.html`, `gallery.html`, `live.html`, `contact.html`, `us.html`, `admin.html`, `404.html`.

Il design system resta coerente con l'identita' Kosmik Circles; non sono state introdotte modifiche grafiche nella Fase 1.

## Prossimo ordine di intervento

1. Hardening inventario/checkout e test concorrenti.
2. Hardening Admin/CSP senza variazioni visive.
3. Test frontend funzionali per pagina.
4. Performance e mobile.
5. SEO e produzione.
