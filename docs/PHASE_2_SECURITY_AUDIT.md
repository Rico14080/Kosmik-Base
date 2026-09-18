# KOSMIK CIRCLES — revisione tecnica e funzionale
Data: 18 settembre 2026. Stato: **NON PRONTO PER IL LANCIO**.

## Versioni e metodo

Revisione di `main` (2144eb0), `development` (c4a0043) e della versione più avanzata, `phase-2-security-deployment-v2` (f9b461a, PR #15). Le due precedenti PR #10 e #14 sono ancora aperte: le loro correzioni non vanno ricreate. I risultati sotto si riferiscono alla PR #15 salvo diversa indicazione.

Esaminati backend Python/SQLite, CMS, script pubblici, checkout, configurazione, CI e documentazione. Eseguiti test locali isolati con dati sintetici, senza pagamenti né email reali. Browser: percorso Shop → Cart, errore esaurito, caricamento/login Admin; visita delle otto pagine pubbliche a larghezza 390 px. L'Admin e gli script pubblici interessati hanno lo stesso contenuto in development e nella PR #15.

**R** = riprodotto localmente; **C** = difetto riscontrato nel codice, non collaudato con provider reale; **D** = requisito o configurazione da completare. P0 = blocco sicurezza; P1 = blocco funzionale/commerciale; P2 = miglioramento necessario o rischio condizionale.

## P0 — sicurezza

### 01. File privati raggiungibili senza autenticazione — R
`backend/server.py`, `blocked_static` e gestione statica.
Il controllo usa il percorso non normalizzato, mentre il server statico decodifica e normalizza successivamente. Nel test locale un percorso alternativo ha restituito HTTP 200 e il database SQLite, invece del 404 atteso. Anche sorgenti e HEAD non sono protetti uniformemente. La directory dei backup non è inclusa nella protezione.
Impatto: esposizione potenziale di clienti, messaggi, ordini, token delle sessioni e configurazione. Il rischio è nel backend; non è stata verificata un'esposizione su un dominio pubblico.
Intervento: separare la cartella pubblica dai dati, usare una allow-list di asset e validare il percorso risolto per tutti i metodi HTTP. Testare anche backup e file nascosti.

## P1 — prima di inserire i contenuti definitivi o vendere

### 02. Admin non completa il caricamento — R
`admin.js:24,39`, `admin.html`.
`renderAll()` chiama `renderGallery()`, che cerca `gallery-list`, assente nell'HTML. Riprodotto l'errore «Cannot set properties of null (setting 'innerHTML')», sia prima sia dopo il login. Il pannello segnala erroneamente server non disponibile e ripropone il login; le sezioni successive non vengono inizializzate.
Intervento: eliminare il vecchio editor Gallery e collegare correttamente l'archivio album esistente.

### 03. Salvataggio Admin può svuotare le intestazioni delle pagine — C
`admin.js:23,32,33`.
I campi sono input con `data-page-field`; la raccolta li tratta come contenitori e cerca discendenti `data-key`, ottenendo stringhe vuote. Un salvataggio può cancellare titoli, eyebrow e note di tutte le pagine interne. Il crash precedente può inoltre lasciare altri campi vuoti.
Intervento: mappare gli input effettivi e testare un salvataggio senza modifiche e uno con un solo campo modificato.

### 04. Date e link biglietti si perdono dopo il salvataggio — R
`backend/server.py`, `save_content` e `GET /api/content`; `site.js:46`.
L'API restituisce `iso_date/ticket_url`; frontend e CMS usano `isoDate/ticketUrl`. Riprodotto: evento salvato con data e URL corretti, riletto e risalvato con entrambi i valori vuoti. I link risultano disabilitati e il calcolo degli eventi passati non riceve la data.
Intervento: un contratto JSON coerente e test completo salva → ricarica → salva.

### 05. Le righe duplicate aggirano la disponibilità — R
`backend/server.py`, `reserve_order_stock` e checkout.
Con stock 1 e due righe dello stesso prodotto da quantità 1, l'ordine viene accettato. Riprodotta anche la riserva di 2 unità con una sola disponibile. Ogni riga viene verificata prima che inizi l'aggiornamento delle riserve.
Intervento: aggregare per identificativo prodotto prima di verificare e riservare.

### 06. Prenotazione delle scorte e sessione Stripe non scadono insieme — R/C
`STOCK_RESERVATION_TTL`, `create_stripe_checkout`, `release_expired_reservations`.
La riserva locale dura 30 minuti; la richiesta Stripe non imposta `expires_at` e la cancellazione amministrativa non scade la sessione remota. Stripe documenta una durata predefinita di 24 ore: il cliente potrebbe pagare dopo che il pezzo è stato liberato e rivenduto.
Intervento: allineare le scadenze e gestire cancellazione, pagamento tardivo ed eventuale rimborso. [Stripe: creazione Checkout Session](https://docs.stripe.com/api/checkout/sessions/create).

### 07. Pagamento confermato anche con stock arrivato a zero — R
`backend/server.py`, `apply_paid_order`.
Il controllo/scarico viene saltato quando il prodotto ha stock 0. Riprodotto un ordine non ancora finalizzato: stock 0, funzione restituisce True e ordine marcato PAID/stock_applied=1. Può verificarsi dopo scadenza della prenotazione o modifica Admin.
Intervento: validare disponibilità e prenotazione anche a zero, con gestione esplicita degli ordini già pagati ma non evadibili.

### 08. Salvataggio contenuti può ripristinare scorte già vendute — R
`backend/server.py`, `save_content`.
L'Admin invia tutto il catalogo, incluso lo stock letto all'apertura. Test: stock 5, vendita porta a 4, salvataggio della vecchia schermata riporta lo stock a 5. Anche la modifica di un testo può quindi alterare il magazzino.
Intervento: separare stock e contenuti, oppure introdurre aggiornamenti per campo e controllo di versione.

### 09. Replay del webhook fa regredire lo stato dell'ordine — R
`backend/server.py`, `apply_paid_order` e webhook.
Un ordine già finalizzato e poi SHIPPED torna PAID al secondo evento di pagamento. L'invio email può ripetersi. Il controllo attuale evita parte dei doppi scarichi, ma non rende idempotente l'intero flusso.
Intervento: memorizzare gli eventi elaborati e mantenere distinti pagamento ed evasione.

### 10. Conferma pagamento frontend incompatibile con il token nuovo — C
`site.js:103`, `checkout-fix.js`, API stato ordine.
Lo script principale interroga lo stato senza token, mentre la PR #15 lo richiede. Lo script aggiuntivo usa il token ma si limita a svuotare il carrello: non aggiorna il messaggio principale. La conferma può quindi fallire visivamente anche quando il pagamento è riuscito. Manca inoltre un tentativo successivo se il webhook arriva dopo il ritorno del cliente.
Intervento: un solo controller di checkout/conferma, autenticazione coerente, attesa limitata e aggiornamento del carrello visualizzato.

### 11. La protezione da doppio invio si disattiva dopo il primo tentativo — R/C
`checkout-fix.js:9-26`, `site.js:102`.
Dopo un errore rimane `checkoutFixBound=1`: il secondo invio salta l'intercettore e raggiunge il vecchio handler, privo delle stesse protezioni e del salvataggio del token. Riprodotto con errore di rete simulato.
Intervento: rimuovere la doppia gestione e utilizzare un unico stato di invio/riprova.

### 12. Ordini spedibili accettati senza indirizzo — R/C
`site.js:102`, endpoint checkout, creazione sessione Stripe.
Solo l'email è obbligatoria. Riprodotto HTTP 201 con nome e indirizzo assenti; Stripe non è configurato per raccogliere un indirizzo di spedizione. Non ci sono regole di costo/paese di spedizione nel totale.
Intervento: validare i dati necessari per il merch fisico e definire spedizione, ritiro e prezzi finali prima dei pagamenti reali.

### 13. Admin ordini non mostra i dati necessari per spedire — C
`admin-ops.js:28-44`.
L'API restituisce indirizzo, città, CAP, paese e telefono, ma la scheda visualizza solo nome/email/articoli/stato.
Intervento: dettaglio ordine completo, totale e informazioni di evasione.

### 14. Rimborsi e spedizioni sono solo etichette — R/C
`backend/server.py`, `POST /api/admin/orders/status`.
Cambiare in REFUNDED non chiama Stripe e non modifica `payment_status`; SHIPPED non aggiorna `shipping_status`. Verificato nel codice e nel database locale. Lo stato di pagamento e i conteggi dei ricavi rimangono incoerenti.
Intervento: distinguere annotazioni e operazioni reali; aggiornare lo stato solo sulla base del risultato effettivo.

### 15. Salvataggi/operazioni Admin perdono modifiche non salvate — C
`admin.js`, aggiunta e cancellazione prodotti/eventi.
I campi modificati restano nel DOM; i pulsanti ricostruiscono le righe da `content` senza raccoglierli. Esempio: modificare il nome di un prodotto e aggiungerne un altro può far sparire la prima modifica.
Intervento: mantenere un unico modello di modifica, oppure raccogliere prima di ridisegnare.

## P2 — funzionalità, robustezza e manutenzione

### 16. Stock incoerente tra backend, Admin e shop — R/C
L'Admin mostra ancora «0 = unlimited», ma il backend rifiuta stock 0. Lo shop mostra «Add to cart» anche a stock zero; riprodotto acquisto bloccato solo all'invio. L'API rappresenta ancora `availableStock` zero come null.
Intervento: significato unico di zero, badge esaurito e limite quantità coerente.

### 17. Prezzi e identità prodotto nel carrello non vengono aggiornati — C
`site.js:25-32,102`; checkout identifica per nome.
Il carrello conserva prezzo/nome originali. Una modifica del prezzo lascia un totale vecchio prima del checkout; rinominare un prodotto già nel carrello lo rende indisponibile.
Intervento: usare ID/SKU stabili e ricalcolare il riepilogo dal catalogo prima della conferma.

### 18. Etichetta Bag/Cart sostituita dal numero — R
`site.js:30`, `site-fixes.js`, `checkout-fix.js`.
Il selettore `.bag-link span` comprende anche il testo del link. Nel browser è apparso «1 1» su tutte le pagine dopo la navigazione; la correzione aggiuntiva può arrivare prima del render asincrono.
Intervento: aggiornare esclusivamente `data-cart-count` nel codice principale.

### 19. Validazione API incompleta e limiti corpo non uniformi — R/C
`read_json`, checkout e webhook.
Un array JSON al checkout chiude la connessione con eccezione invece di rispondere 400 (riprodotto). Le quantità numeriche frazionarie sono convertite con int. Il ramo JSON troppo grande legge comunque tutta la lunghezza dichiarata; il webhook non applica un tetto analogo.
Intervento: validare tipo/struttura prima dell'accesso ai campi, rifiutare frazioni e limitare lettura/timeout senza caricare corpi arbitrari.

### 20. Pagamenti asincroni e notifiche email incompleti — C
Webhook gestisce completamento pagato e scadenza, non la conferma asincrona. Errori email restituiscono False ma non attivano una coda/riprova. Valutare i metodi effettivamente abilitati su Stripe; non dichiarare supportati quelli non collaudati.
Intervento: gestire gli eventi necessari e monitorare/riprovare le notifiche.

### 21. Login tardivo non aggiorna Orders/Messages — C
`admin-ops.js:68-75`.
L'attesa del token termina dopo 120 × 250 ms. Un login oltre 30 secondi non rilancia il caricamento operativo; il controller Admin non comunica l'avvenuta autenticazione.
Intervento: evento esplicito di login/logout e caricamento collegato alla sessione.

### 22. Copertine Gallery e anteprime immagini fragili — C
La pulizia degli upload rimossi dai contenuti generali può cancellare un'immagine ancora usata come copertina album: una routine controlla solo i contenuti, la successiva controlla anche gli album, troppo tardi. Nell'Admin le anteprime dinamiche hanno `data-preview-slot`, mentre `preview()` cerca un ID.
Intervento: unica raccolta dei riferimenti prima di cancellare file; selettori anteprima coerenti.

### 23. Video/download Gallery non adatti a file grandi — C
Il download usa `read_bytes()` su media ammessi fino a 1 GB; più download possono esaurire la RAM. Il percorso video non gestisce Range, limitando il seek. AVI/MOV accettati non garantiscono riproduzione su tutti i browser.
Intervento: streaming, Range, limiti di hosting e formati web concordati.

### 24. Backup parziale e non verificato durante le scritture — C
`backend/backup.py`.
Copia direttamente il file DB e non include uploads/media. Non usa l'API backup SQLite e non c'è prova di ripristino. La destinazione è sotto la radice servita (vedi #01).
Intervento: snapshot consistente, media, destinazione privata e prova di restore.

### 25. Modalità backend indisponibile confonde i contenuti — C
`site.js:18`.
Un errore API ripiega silenziosamente su contenuti locali/demo, che possono essere diversi da quelli pubblicati. Senza Stripe viene creato un ordine UNPAID e lo script aggiuntivo svuota il carrello.
Intervento: stato offline chiaro, vendita disabilitata quando non operativa, conservazione del carrello.

### 26. Sessioni/CSP e rate limit da completare — C/D
Bearer in sessionStorage, CSP con `unsafe-inline`, rate limit in memoria basato sull'IP del socket. Dietro un reverse proxy più visitatori potrebbero condividere il limite.
Intervento: decisione esplicita su sessioni e difese XSS, CSP compatibile con gli script, gestione dei proxy fidati e verifica HTTPS. Non è stata dimostrata un'ulteriore vulnerabilità XSS.

### 27. Performance, accessibilità e SEO incompleti — C/D
Canvas Matrix con rendering continuo; il fix ne cambia la visibilità ma non il loop. Mancano meta description, Open Graph, canonical e sitemap. Molti messaggi sono ancora inglesi e non passano per il CMS. Le immagini esterne dipendono da servizi terzi; nella sessione locale la hero non si è caricata, senza prova che il problema si ripeta in produzione.
Intervento: test prestazioni/accessibilità reali, riduzione animazioni, media definitivi e metadati dopo la scelta del dominio.
Le otto pagine pubbliche non hanno mostrato overflow orizzontale nel controllo DOM a 390 px; questo non sostituisce il collaudo su dispositivi reali.

### 28. Test verdi non coprono i flussi critici emersi — R/C
Passano localmente le suite esistenti phase1_checkout, production_inventory_guard, checkout_api_integration e security_http_regression. Sintassi dei principali script valida. Il browser smoke della repo non include Admin né i casi duplicati, pagamento tardivo, round-trip eventi, salvataggio titoli e retry.
Intervento: estendere i test esistenti con questi scenari, senza creare suite parallele che verifichino le stesse cose.

## Dati e funzionalità ancora da completare — D

- Identità e testi reali del collettivo: storia, membri, servizi, contatti, social, lingua, foto approvate e crediti.
- Catalogo reale: SKU, prezzi, taglie/colori (non modellati oggi), disponibilità per variante, foto, descrizioni e regole di esaurimento/preordine.
- Eventi reali, date, location e link biglietti; album Gallery e relativi file.
- Paesi/costi/tempi di spedizione, eventuale ritiro, resi e gestione assistenza.
- Informazioni dell'organizzazione e pagine Privacy/condizioni/vendita/spedizioni/resi: assenti nel sorgente; contenuti da definire in base all'attività effettiva.
- Hosting Python con storage persistente, dominio/DNS, HTTPS, Stripe test e poi live, SMTP, backup, monitoraggio e ripristino. La configurazione degli account reali non è stata ispezionata.

## Ordine di lavoro

1. Chiudere #01 e ripristinare Admin/salvataggi (#02–04, #15).
2. Unificare i controller esistenti di checkout e correggere magazzino/pagamenti (#05–14). Niente nuovi file «fix» sovrapposti.
3. Inserire dati reali e merch dopo che un salvataggio non può perdere contenuti o alterare le scorte.
4. Completare Gallery, gestione operativa, backup, sicurezza, SEO e accessibilità.
5. Staging HTTPS: pagamento test completo, webhook ripetuto/ritardato, ultimo pezzo, spedizione, messaggi, email e ripristino.
6. Revisione finale e solo allora promozione della versione verificata e lancio.

## Pulizia della repository in questa revisione

Rimossi report di versioni superate, istruzioni duplicate, una copia binaria di prova identica a un asset conservato e lo script di verifica immagini che stampava OK senza assert. Consolidate checklist di lancio e configurazione; mantenuti test reali e sorgenti fotografici originali. La storia rimane recuperabile da Git.
Le modifiche di pulizia non correggono i bug elencati: questo documento è il punto di partenza per le correzioni.
