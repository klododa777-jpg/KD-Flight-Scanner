# KD-Flight-Scanner

Scanner automatico di offerte voli weekend con notifiche Telegram.

## Configurazione confermata

- Passeggeri: 1
- Aeroporti di partenza: Venezia Marco Polo (VCE), Treviso (TSF), Milano Malpensa (MXP), Bergamo Orio al Serio (BGY)
- Periodo da monitorare: weekend sabato-domenica da gennaio a giugno 2027
- Solo voli diretti
- Prezzo massimo: 100 EUR andata e ritorno, tasse incluse
- Bagaglio: solo piccolo zaino personale
- Orari: liberi, purché andata sabato e ritorno domenica
- Destinazioni: escludere quelle già visitate e quelle per cui il passaporto albanese richiede un visto non posseduto
- Notifiche Telegram: soltanto nuove offerte, con deduplicazione
- Frequenza scansione prevista: due martedì al mese, primo e terzo martedì

## Budget SerpApi

Il test ha dimostrato che gli aeroporti devono essere interrogati separatamente: una richiesta con più codici aeroporto restituisce risultati vuoti.

- 26 weekend da controllare
- 4 aeroporti per weekend
- 104 richieste per scansione completa
- 2 scansioni al mese: circa 208 richieste mensili
- Limite piano gratuito: 250 richieste mensili
- Margine previsto: circa 42 richieste al mese

La stima presuppone una richiesta per ogni combinazione aeroporto/weekend e nessun retry. Il codice dovrà evitare chiamate aggiuntive non necessarie e interrompersi in caso di errori ripetuti, così da proteggere il budget mensile.

## API

Il test usa SerpApi Google Travel Explore. Ogni aeroporto viene interrogato con una richiesta separata. La modalità round trip viene impostata esplicitamente.

## Stato del progetto

- [x] Secret GitHub Actions `SERPAPI_KEY` configurato
- [x] Prima chiamata API riuscita con VCE
- [x] Test aggiornato per interrogare separatamente VCE, TSF, MXP e BGY
- [ ] Verificare il nuovo test con i quattro aeroporti
- [ ] Verificare prezzo A/R, date, scali e dati di destinazione
- [ ] Implementare scansione dei 26 weekend con controllo del budget API
- [ ] Implementare filtri, esclusioni e deduplicazione
- [ ] Configurare Telegram
- [ ] Attivare scansione il primo e terzo martedì del mese, dopo i test

## Test manuale

GitHub → Actions → Test SerpApi → Run workflow. I valori predefiniti verificano separatamente VCE, TSF, MXP e BGY per il weekend 9–10 gennaio 2027.

Non inserire mai API key o token nei file del repository: usare GitHub Actions Secrets.
