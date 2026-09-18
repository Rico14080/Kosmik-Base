# Checklist unica per il lancio

Aggiornata il 18 settembre 2026. Stato: **NON PRONTO PER LA PRODUZIONE**.

L'[audit corrente](PHASE_2_SECURITY_AUDIT.md) contiene problemi, prove e priorità. Questa pagina raccoglie solo le condizioni per passare al lancio; i vecchi report di fase restano recuperabili dalla cronologia Git.

## 1. Base tecnica

- [ ] Chiudere l'accesso ai file privati e verificare percorsi alternativi, HEAD, backup e file nascosti.
- [ ] Ripristinare Admin, salvataggio delle intestazioni e dati eventi senza perdite.
- [ ] Correggere disponibilità, prenotazioni, pagamento tardivo, webhook ripetuti e modifiche stock.
- [ ] Unificare i flussi frontend di checkout, retry e conferma con token.
- [ ] Completare ordini, indirizzi, spedizioni, rimborsi e messaggi.
- [ ] Verificare sessioni, CSP, rate limit e proxy fidati.
- [ ] Estendere i test esistenti con i casi emersi nell'audit.

## 2. Contenuti e attività del collettivo

- [ ] Testi, membri, servizi, contatti, social e lingua definitivi.
- [ ] Foto autorizzate, crediti, album e media.
- [ ] Eventi con data, luogo e link biglietti veri.
- [ ] Merch con SKU, varianti/taglie, prezzi, foto e disponibilità reali.
- [ ] Paesi, costi e tempi di spedizione; eventuale ritiro; resi e assistenza.
- [ ] Informazioni dell'organizzazione e pagine informative/condizioni pertinenti all'attività.
- [ ] Metadati, anteprime social, canonical e sitemap sul dominio definitivo.

## 3. Infrastruttura e servizi

- [ ] Hosting che esegua Python, con storage persistente e accesso al backend solo tramite reverse proxy HTTPS.
- [ ] Dominio registrato, DNS, certificato e PUBLIC_BASE_URL verificati.
- [ ] KOSMIK_ADMIN_PASSWORD impostata tramite secret manager, fuori da Git.
- [ ] Stripe test configurato con STRIPE_SECRET_KEY e STRIPE_WEBHOOK_SECRET.
- [ ] Endpoint /api/stripe/webhook verificato, con eventi coerenti con l'implementazione e i metodi di pagamento abilitati.
- [ ] SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS e SITE_OWNER_EMAIL configurati e collaudati.
- [ ] Backup consistente di database, uploads e media in una posizione privata esterna alla radice pubblica.
- [ ] Ripristino di un backup provato e monitoraggio degli errori/email attivo.
- [ ] Limiti upload/download e spazio disco definiti per i video.
- [ ] Piano di rollback con versione e dati compatibili.

Unico elenco delle variabili: [../.env.example](../.env.example). Il backend legge l'ambiente del processo, non carica automaticamente un file .env.

Durante aggiornamenti preservare backend/data/kosmik.db, backend/uploads/ e backend/media/. Lo script backup.py corrente non copre da solo tutti questi requisiti: vedere l'audit.

## 4. Staging e decisione finale

- [ ] CI verde sulla revisione esatta da distribuire.
- [ ] Browser desktop/mobile, tastiera e riduzione delle animazioni verificati.
- [ ] Login/logout/scadenza sessione Admin, modifica/salvataggio/ricarica contenuti.
- [ ] Shop → carrello → pagamento test → webhook → conferma → evasione.
- [ ] Ultimo pezzo concorrente, righe duplicate, quantità errata, prezzo cambiato, retry e pagamento tardivo.
- [ ] Contatti, ricezione email, Gallery e download.
- [ ] HTTPS, backup/restore e rollback verificati sullo staging.
- [ ] Passaggio a Stripe live e controllo della configurazione finale.
- [ ] Revisione finale con il collettivo e decisione di apertura.

Non promuovere main né pubblicare pagamenti reali finché rimangono blocchi P0/P1. Nessuna credenziale deve essere inviata in chat o inserita nel repository.
