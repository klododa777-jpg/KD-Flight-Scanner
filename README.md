# KD-Flight-Scanner

Scanner automatico di offerte voli weekend con notifiche Telegram.

## Configurazione

- Passeggeri: 1
- Aeroporti: Venezia Marco Polo (VCE), Treviso (TSF), Milano Malpensa (MXP), Bergamo Orio al Serio (BGY)
- Periodo: finestra mobile di circa tre mesi, che avanza a ogni scansione
- Solo voli diretti
- Prezzo massimo: 60 EUR A/R, tasse incluse
- Bagaglio: non usato come filtro; i prezzi servono come riferimento e il bagaglio si verifica separatamente
- Destinazioni già visitate escluse
- Destinazioni: tutta l'area Schengen, i paesi UE accessibili senza visto e gli altri paesi europei visa-free per passaporto albanese biometrico (Irlanda esclusa perché richiede un visto)
- Telegram: massimo 3 notifiche per destinazione; prima notifica con fino a 3 date più economiche, successive solo per ribassi significativi
- Frequenza: automatica il primo e il terzo martedì del mese alle 05:00 UTC; avvio manuale disponibile anche su richiesta

## Secrets GitHub Actions richiesti

Configurare in **Settings → Secrets and variables → Actions**:

- `SERPAPI_KEY` (già configurato)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Se i due secret Telegram mancano, lo scanner si ferma prima di effettuare chiamate SerpApi.

## Consumo API

- Circa 14 weekend × 4 aeroporti = circa 56 richieste per scansione.
- Il workflow parte automaticamente ogni martedì alle 05:00 UTC; lo script effettua chiamate soltanto il primo e il terzo martedì del mese. È disponibile anche l'avvio manuale.
- Il codice impone un tetto di sicurezza di 240 richieste/mese, sotto il limite gratuito dichiarato di 250.
- Ogni chiamata viene registrata in `data/scanner_state.json` prima di essere eseguita.
- Nessun retry automatico: errori API o di rete interrompono la scansione per non consumare ulteriori chiamate.
- Gli aeroporti senza risultati vengono saltati; non sono trattati come errori di autenticazione.

## Filtri e limiti dei dati

Lo scanner seleziona risultati con prezzo non superiore a 60 EUR A/R, zero scali, date esatte sabato-domenica e paese presente nella lista europea ammessa: UE/Schengen e altri paesi europei visa-free per passaporto albanese biometrico. L'Irlanda è esclusa perché richiede un visto ai cittadini albanesi. Esclude le destinazioni già visitate confrontando nome della destinazione, nome/città/codice dell'aeroporto di arrivo e varianti normalizzate. Charleroi (CRL) è esclusa perché è usata come aeroporto alternativo per Bruxelles, già visitata. Per ogni destinazione ordina le offerte raccolte nei weekend analizzati: la prima notifica può contenere fino a 3 date tra le più economiche. Nelle scansioni successive invia un nuovo avviso solo se il prezzo minimo scende almeno del 15% e di almeno 5 EUR rispetto al miglior prezzo già notificato. Massimo 3 notifiche complessive per destinazione. I prezzi fino a 45 EUR sono evidenziati come ottime occasioni. Lo storico conserva le ultime 24 scansioni e il riepilogo è visibile nel Summary del run GitHub Actions.

Google Travel Explore non espone in modo affidabile la regola tariffaria sul bagaglio personale. Il bagaglio non viene quindi usato come filtro: i prezzi servono come riferimento e il costo finale va ricontrollato prima dell'acquisto.

La copertura non è esaustiva: Google Travel può restituire zero risultati per un aeroporto o una data anche quando esistono voli venduti altrove. Un risultato vuoto viene registrato come assenza di dati, non come prova che non esistano voli. Il prezzo minimo è quindi il migliore tra i risultati restituiti, non una garanzia del prezzo più basso disponibile sul mercato.

La lista include i paesi europei Schengen/UE accessibili senza visto e gli altri paesi europei visa-free per i titolari di passaporto albanese biometrico. Non include paesi europei per cui è richiesto un visto, come l'Irlanda. Le condizioni d'ingresso possono cambiare: prima dell'acquisto va sempre verificata la regola ufficiale del paese di destinazione.

## Avvio

Dopo aver configurato tutti e tre i secrets, aprire **Actions → Weekend Flight Scanner → Run workflow** per un primo avvio manuale. Il primo avvio cerca i weekend nella finestra mobile: dal primo sabato a partire da un mese dopo la scansione fino al primo sabato a partire da quattro mesi dopo.

La scansione è automatica il primo e il terzo martedì del mese alle 05:00 UTC. A ogni esecuzione la finestra avanza: parte dal primo weekend a partire da un mese dopo la data di scansione e arriva al primo weekend a partire da quattro mesi dopo. L'avvio manuale resta disponibile. L'orario corrisponde alle 06:00 in inverno e alle 07:00 durante l'ora legale italiana.

Non inserire mai chiavi API o token nei file del repository.
