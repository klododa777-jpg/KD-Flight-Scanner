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

## API

Il test usa SerpApi Google Travel Explore. La documentazione supporta più aeroporti di partenza nella stessa richiesta, separati da virgola. La modalità round trip è il valore predefinito; il test la imposta esplicitamente.

## Stato del progetto

- [x] Secret GitHub Actions `SERPAPI_KEY` configurato
- [x] Prima chiamata API riuscita con VCE
- [x] Test aggiornato per VCE, TSF, MXP e BGY in un'unica richiesta
- [ ] Verificare il risultato reale della richiesta multi-aeroporto
- [ ] Verificare prezzo A/R, date, scali e dati di destinazione
- [ ] Implementare filtri, esclusioni e deduplicazione
- [ ] Configurare Telegram
- [ ] Attivare scansione programmata dopo i test

## Test manuale

GitHub → Actions → Test SerpApi → Run workflow. I valori predefiniti verificano VCE,TSF,MXP,BGY per il weekend 9–10 gennaio 2027.

Non inserire mai API key o token nei file del repository: usare GitHub Actions Secrets.
