# KD-Flight-Scanner

Scanner automatico di offerte voli weekend con notifiche Telegram.

## Configurazione

- Passeggeri: 1
- Aeroporti: Venezia Marco Polo (VCE), Treviso (TSF), Milano Malpensa (MXP), Bergamo Orio al Serio (BGY)
- Periodo: weekend sabato-domenica da gennaio a giugno 2027
- Solo voli diretti
- Prezzo massimo: 60 EUR A/R, tasse incluse
- Bagaglio richiesto: solo zaino personale piccolo
- Destinazioni già visitate escluse
- Preferenza per paesi senza visto per passaporto albanese biometrico
- Telegram: massimo 3 offerte complessive per destinazione, selezionate tra le più economiche; raggruppate in un solo messaggio per destinazione
- Frequenza: primo e terzo martedì del mese

## Secrets GitHub Actions richiesti

Configurare in **Settings → Secrets and variables → Actions**:

- `SERPAPI_KEY` (già configurato)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Se i due secret Telegram mancano, lo scanner si ferma prima di effettuare chiamate SerpApi.

## Consumo API

- 26 weekend × 4 aeroporti = massimo 104 richieste per scansione completa.
- Due scansioni mensili = circa 208 richieste.
- Il codice impone un tetto di sicurezza di 240 richieste/mese, sotto il limite gratuito dichiarato di 250.
- Ogni chiamata viene registrata in `data/scanner_state.json` prima di essere eseguita.
- Nessun retry automatico: errori API o di rete interrompono la scansione per non consumare ulteriori chiamate.
- Gli aeroporti senza risultati vengono saltati; non sono trattati come errori di autenticazione.

## Filtri e limiti dei dati

Lo scanner seleziona risultati con prezzo non superiore a 60 EUR A/R, zero scali, date esatte sabato-domenica e paese presente nella lista prudenziale dei paesi senza visto. Esclude le destinazioni già visitate. Per ogni destinazione ordina le offerte di tutti i weekend analizzati per prezzo e invia al massimo 3 offerte complessive, raggruppate in un unico messaggio; il contatore viene salvato nello stato per evitare notifiche ripetute nelle scansioni successive.

Google Travel Explore non espone in modo affidabile la regola tariffaria sul bagaglio personale: ogni messaggio richiede quindi di verificare sul sito della compagnia che lo zaino piccolo sia incluso. Il prezzo mostrato dall'API va ricontrollato prima dell'acquisto.

La copertura non è esaustiva: Google Travel può restituire zero risultati per un aeroporto o una data anche quando esistono voli venduti altrove. Un risultato vuoto viene registrato come assenza di dati, non come prova che non esistano voli.

La lista dei paesi visa-free è intenzionalmente prudente e va mantenuta aggiornata prima di considerarla una verifica legale definitiva.

## Avvio

Dopo aver configurato tutti e tre i secrets, aprire **Actions → Weekend Flight Scanner → Run workflow** per un primo avvio manuale. Il primo avvio effettua la scansione completa dei weekend ancora futuri nel periodo gennaio-giugno 2027.

Il workflow automatico si attiva ogni martedì alle 05:00 UTC, ma lo script esegue chiamate soltanto il primo e il terzo martedì del mese. L'orario corrisponde alle 06:00 in inverno e alle 07:00 durante l'ora legale italiana.

Non inserire mai chiavi API o token nei file del repository.
