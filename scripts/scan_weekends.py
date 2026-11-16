import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://serpapi.com/search.json"
STATE_PATH = Path("data/scanner_state.json")
AIRPORTS = {
    "VCE": "Venezia Marco Polo",
    "TSF": "Treviso",
    "MXP": "Milano Malpensa",
    "BGY": "Bergamo Orio al Serio",
}
MAX_PRICE_EUR = 60
MAX_OFFERS_PER_DESTINATION = 3
GREAT_PRICE_EUR = 45
PRICE_DROP_MIN_PERCENT = 15
PRICE_DROP_MIN_EUR = 5
SCAN_HISTORY_LIMIT = 24
MONTHLY_CALL_CAP = 240  # lascia margine rispetto alle 250 ricerche del piano gratuito
SCAN_START = date(2027, 1, 1)
SCAN_END = date(2027, 6, 30)

# Destinazioni già visitate: confronto normalizzato su nome e alias.
VISITED = {
    "sirmione", "castelmola", "taormina", "malta", "rimini", "barcelona",
    "barcellona", "vienna", "brussels", "bruxelles", "athens", "atene",
    "menton", "monte carlo", "nice", "nizza", "lyon", "lione", "malmo",
    "malmö", "copenhagen", "copenaghen", "venice", "venezia", "warsaw",
    "varsavia", "madrid", "berlin", "berlino", "mallorca", "maiorca",
    "florence", "firenze", "pisa", "bologna", "rome", "roma", "verona",
    "livorno", "sardinia", "sardegna", "milan", "milano", "zagreb",
    "zagabria", "seville", "siviglia", "uppsala", "stockholm", "stoccolma",
    "prague", "praga", "sofia", "valencia", "tirana", "strasbourg",
    "strasburgo", "obernai", "dambach-la-ville", "colmar", "basel", "basilea",
    "paris", "parigi", "budapest", "hamburg", "amburgo", "lisbon", "lisbona",
    "porto", "utrecht", "amsterdam", "rotterdam", "krakow", "cracovia",
    "bordeaux", "bucharest", "bucarest", "luxembourg", "lussemburgo",
    "echternach", "vianden", "istanbul", "costantinopoli", "toulouse",
    "carcassonne", "carcassona", "gdansk", "danzica", "malbork", "sopot",
    "ibiza", "alicante", "elche", "murcia", "benidorm", "lecco", "bellagio",
    "como", "st. moritz", "saint moritz", "bratislava", "helsinki", "porvoo",
    "tallinn", "santorini", "turin", "torino", "genoa", "genova", "villach",
    "salzburg", "salisburgo", "munich", "monaco di baviera", "innsbruck",
    "padova", "bruges", "brugge", "ghent", "gand", "antwerp", "anversa",
    "bilbao", "san sebastian", "san sebastián", "malaga", "malaga",
    "granada", "palma de mallorca", "la spezia", "cannes",
}

# Paesi con accesso senza visto per soggiorni brevi per titolari di passaporto
# albanese biometrico; lista volutamente prudente e limitata all'Europa.
VISA_FREE_COUNTRIES = {
    "albania", "andorra", "austria", "belgium", "belgio", "bosnia and herzegovina",
    "bosnia ed erzegovina", "bulgaria", "croatia", "croazia", "cyprus", "cipro",
    "czechia", "czech republic", "repubblica ceca", "denmark", "danimarca",
    "estonia", "finland", "finlandia", "france", "francia", "georgia",
    "germany", "germania", "greece", "grecia", "hungary", "ungheria",
    "iceland", "islanda", "italy", "italia", "kosovo", "latvia", "lettonia",
    "liechtenstein", "lithuania", "lituania", "luxembourg", "lussemburgo",
    "malta", "moldova", "monaco", "montenegro", "netherlands", "paesi bassi",
    "north macedonia", "macedonia del nord", "norway", "norvegia", "poland",
    "polonia", "portugal", "portogallo", "romania", "san marino", "serbia",
    "slovakia", "slovacchia", "slovenia", "spain", "spagna", "sweden",
    "svezia", "switzerland", "svizzera", "turkey", "turchia", "ukraine",
    "ucraina", "vatican city", "città del vaticano",
}

def normalized(value):
    return " ".join(str(value or "").strip().casefold().replace("’", "'").split())

def load_state():
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        return {"api_usage": {}, "seen_offer_keys": [], "destination_alerts": {}, "destination_price_history": {}, "scan_history": []}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("Formato stato non valido")
        state.setdefault("api_usage", {})
        state.setdefault("seen_offer_keys", [])
        state.setdefault("destination_alerts", {})
        state.setdefault("destination_price_history", {})
        state.setdefault("scan_history", [])
        return state
    except (OSError, ValueError, json.JSONDecodeError):
        print("ERRORE: file data/scanner_state.json illeggibile; interruzione per sicurezza.")
        raise

def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_PATH)

def first_and_third_tuesday(day):
    if day.weekday() != 1:
        return False
    return 1 <= day.day <= 7 or 15 <= day.day <= 21

def weekend_pairs(today):
    pairs = []
    current = SCAN_START
    while current <= SCAN_END:
        if current.weekday() == 5:
            sunday = current + timedelta(days=1)
            if current >= today:
                pairs.append((current, sunday))
        current += timedelta(days=1)
    return pairs

def is_visited(destination):
    name = normalized(destination.get("name"))
    aliases = {name}
    aliases.add(normalized(destination.get("destination")))
    return bool(aliases & VISITED)

def is_visa_free(destination):
    country = normalized(destination.get("country"))
    return country in VISA_FREE_COUNTRIES

def offer_key(airport, destination, outbound, returning):
    identity = "|".join([
        airport,
        normalized(destination.get("name")),
        normalized((destination.get("destination_airport") or {}).get("code")),
        outbound.isoformat(),
        returning.isoformat(),
        normalized(destination.get("airline")),
    ])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()

def telegram_send(session, token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = session.post(
        url,
        json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
        timeout=30,
    )
    data = response.json()
    if response.status_code != 200 or not data.get("ok"):
        raise RuntimeError(f"Telegram non ha accettato il messaggio (HTTP {response.status_code}).")

def main():
    api_key = os.environ.get("SERPAPI_KEY")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not api_key:
        print("ERRORE: secret SERPAPI_KEY non configurato.")
        return 2
    if not telegram_token or not telegram_chat:
        print("BLOCCATO: configurare TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID nei GitHub Actions Secrets.")
        print("Nessuna chiamata SerpApi è stata effettuata.")
        return 2

    today = datetime.now(ZoneInfo("Europe/Rome")).date()
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not first_and_third_tuesday(today):
        print("Oggi non è il primo o il terzo martedì del mese: nessuna scansione, zero chiamate API.")
        return 0

    pairs = weekend_pairs(today)
    if not pairs:
        print("Nessun weekend residuo nel periodo gennaio-giugno 2027.")
        return 0

    state = load_state()
    month_key = today.strftime("%Y-%m")
    used = int(state["api_usage"].get(month_key, 0))
    seen = set(state["seen_offer_keys"])
    session = requests.Session()
    offers_found = []
    calls_this_run = 0

    print(f"Weekend da controllare: {len(pairs)} | aeroporti: {', '.join(AIRPORTS)}")
    print(f"Chiamate SerpApi già conteggiate nel mese: {used}/{MONTHLY_CALL_CAP}")

    for outbound, returning in pairs:
        for airport, airport_name in AIRPORTS.items():
            if used >= MONTHLY_CALL_CAP:
                print("LIMITE DI SICUREZZA API raggiunto: scansione interrotta.")
                break

            params = {
                "engine": "google_travel_explore",
                "departure_id": airport,
                "outbound_date": outbound.isoformat(),
                "return_date": returning.isoformat(),
                "currency": "EUR",
                "hl": "it",
                "gl": "it",
                "api_key": api_key,
            }

            # Conteggia e salva prima della chiamata: evita di perdere il consumo
            # se il job viene interrotto durante la richiesta.
            used += 1
            calls_this_run += 1
            state["api_usage"][month_key] = used
            save_state(state)

            try:
                response = session.get(API_URL, params=params, timeout=45)
                data = response.json()
            except (requests.RequestException, ValueError) as exc:
                print(f"ERRORE di rete/risposta per {airport} {outbound}: {type(exc).__name__}. Stop per proteggere il budget.")
                save_state(state)
                return 1

            if response.status_code != 200:
                print(f"ERRORE HTTP {response.status_code} per {airport} {outbound}. Stop.")
                save_state(state)
                return 1

            api_error = data.get("error")
            if api_error:
                if "Empty results for departure_id" in api_error:
                    print(f"Nessun dato: {airport} {outbound} -> {returning}")
                    continue
                print(f"ERRORE API per {airport} {outbound}: {api_error}. Stop.")
                save_state(state)
                return 1

            destinations = data.get("destinations") or []
            for item in destinations:
                if not isinstance(item, dict):
                    continue
                price = item.get("flight_price")
                stops = item.get("number_of_stops")
                if not isinstance(price, (int, float)) or price > MAX_PRICE_EUR:
                    continue
                if stops != 0:
                    continue
                if item.get("start_date") != outbound.isoformat() or item.get("end_date") != returning.isoformat():
                    continue
                if is_visited(item) or not is_visa_free(item):
                    continue

                key = offer_key(airport, item, outbound, returning)
                destination_name = item.get("name") or "Destinazione non specificata"
                country = item.get("country") or "Paese non specificato"
                destination_airport = (item.get("destination_airport") or {}).get("code", "")
                airline = item.get("airline") or "Compagnia non indicata"
                link = item.get("link") or item.get("serpapi_link") or data.get("google_flights_link") or ""
                offers_found.append({
                    "key": key,
                    "airport": airport,
                    "airport_name": airport_name,
                    "destination": destination_name,
                    "country": country,
                    "destination_airport": destination_airport,
                    "outbound": outbound.isoformat(),
                    "return": returning.isoformat(),
                    "price": price,
                    "airline": airline,
                    "link": link,
                })

            # Pausa minima per non martellare il provider.
            time.sleep(0.2)
        if used >= MONTHLY_CALL_CAP:
            break

    # Raggruppa tutte le offerte raccolte per destinazione. Le offerte già viste
    # restano disponibili per il confronto prezzi, ma non vengono rinotificate.
    grouped = {}
    unique_offers = {}
    for offer in offers_found:
        unique_offers[offer["key"]] = offer
    offers_found = list(unique_offers.values())
    for offer in offers_found:
        destination_key = normalized(offer["destination"])
        grouped.setdefault(destination_key, []).append(offer)

    alerts = state.setdefault("destination_alerts", {})
    price_history = state.setdefault("destination_price_history", {})
    scan_date = today.isoformat()
    for destination_key, offers in grouped.items():
        cheapest = offers[0]
        records = price_history.setdefault(destination_key, [])
        records.append({
            "scan_date": scan_date,
            "price": cheapest["price"],
            "airport": cheapest["airport"],
            "outbound": cheapest["outbound"],
            "return": cheapest["return"],
        })
        price_history[destination_key] = records[-SCAN_HISTORY_LIMIT:]

    sent_destinations = 0
    sent_offers = 0
    messages_sent = 0

    for destination_key, offers in grouped.items():
        offers.sort(key=lambda item: (item["price"], item["outbound"], item["airport"]))
        alert_state = alerts.get(destination_key)
        unseen = [offer for offer in offers if offer["key"] not in seen]

        if alert_state is None:
            # Migrazione sicura: le offerte viste dal vecchio scanner non vengono
            # inviate di nuovo. Si memorizza il prezzo corrente come riferimento.
            if unseen:
                selected = unseen[:MAX_OFFERS_PER_DESTINATION]
                alert_state = {
                    "alerts_sent": 1,
                    "best_alerted_price": offers[0]["price"],
                }
            else:
                alert_state = {
                    "alerts_sent": 0,
                    "best_alerted_price": offers[0]["price"],
                }
                alerts[destination_key] = alert_state
                continue
        else:
            alerts_sent = int(alert_state.get("alerts_sent", 0))
            best_alerted_price = float(alert_state.get("best_alerted_price", offers[0]["price"]))
            cheapest = offers[0]
            required_drop = max(PRICE_DROP_MIN_EUR, best_alerted_price * PRICE_DROP_MIN_PERCENT / 100)
            if alerts_sent >= MAX_OFFERS_PER_DESTINATION or cheapest["price"] > best_alerted_price - required_drop:
                # Mantiene il riferimento al prezzo migliore già notificato:
                # piccoli movimenti non generano notifiche ripetitive.
                alerts[destination_key] = alert_state
                continue
            selected = [cheapest]
            alert_state = {
                "alerts_sent": alerts_sent + 1,
                "best_alerted_price": cheapest["price"],
            }

        if not selected:
            continue

        title = "🔥 OTTIMO PREZZO" if min(item["price"] for item in selected) <= GREAT_PRICE_EUR else "✈️ MIGLIORI OFFERTE WEEKEND"
        parts = [
            title,
            f"{selected[0]['destination']}, {selected[0]['country']}",
            f"Massimo {MAX_OFFERS_PER_DESTINATION} notifiche per destinazione; soglia {MAX_PRICE_EUR} EUR A/R.",
        ]
        for index, offer in enumerate(selected, start=1):
            price_label = " · OTTIMO PREZZO" if offer["price"] <= GREAT_PRICE_EUR else ""
            parts.extend([
                "",
                f"{index}) {offer['price']} EUR A/R{price_label} — {offer['outbound']} → {offer['return']}",
                f"Partenza da {offer['airport']} ({offer['airport_name']}) · {offer['airline']}",
            ])
            if offer["destination_airport"]:
                parts.append(f"Aeroporto arrivo: {offer['destination_airport']}")
            if offer["link"]:
                parts.append(offer["link"])
        parts.extend([
            "",
            "Volo diretto. Verificare che la tariffa includa lo zaino personale piccolo.",
        ])

        telegram_send(session, telegram_token, telegram_chat, "\n".join(parts))
        for offer in selected:
            seen.add(offer["key"])
        alerts[destination_key] = alert_state
        sent_destinations += 1
        sent_offers += len(selected)
        messages_sent += 1
        state["seen_offer_keys"] = sorted(seen)
        state["destination_alerts"] = alerts
        save_state(state)

    state["seen_offer_keys"] = sorted(seen)
    state["destination_alerts"] = alerts
    state["destination_price_history"] = price_history
    history = state.setdefault("scan_history", [])
    history.append({
        "timestamp_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "weekends_checked": len(pairs),
        "airports": list(AIRPORTS.keys()),
        "api_calls": calls_this_run,
        "eligible_offers": len(offers_found),
        "destinations_found": len(grouped),
        "telegram_messages": messages_sent,
        "offers_notified": sent_offers,
        "api_usage_month": used,
        "api_monthly_cap": MONTHLY_CALL_CAP,
    })
    state["scan_history"] = history[-SCAN_HISTORY_LIMIT:]
    save_state(state)

    summary = [
        "## Weekend Flight Scanner",
        "",
        f"- Data (Europe/Rome): **{today.isoformat()}**",
        f"- Weekend analizzati: **{len(pairs)}**",
        f"- Aeroporti: **{', '.join(AIRPORTS.keys())}**",
        f"- Chiamate SerpApi in questo run: **{calls_this_run}**",
        f"- Offerte idonee raccolte: **{len(offers_found)}**",
        f"- Destinazioni trovate: **{len(grouped)}**",
        f"- Messaggi Telegram inviati: **{messages_sent}**",
        f"- Offerte notificate: **{sent_offers}**",
        f"- Consumo mensile: **{used}/{MONTHLY_CALL_CAP}**",
        f"- Regole: massimo **{MAX_PRICE_EUR} EUR A/R**, voli diretti, massimo **{MAX_OFFERS_PER_DESTINATION} avvisi per destinazione**.",
        "",
        "### Prezzi minimi rilevati in questa scansione",
    ]
    for offer in sorted(offers_found, key=lambda item: item["price"])[:10]:
        summary.append(f"- **{offer['destination']}** — {offer['price']} EUR A/R · {offer['airport']} · {offer['outbound']} → {offer['return']}")
    summary.append("")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as summary_file:
                summary_file.write("\n".join(summary) + "\n")
        except OSError:
            print("AVVISO: impossibile scrivere il riepilogo GitHub Actions.")
    print("\n".join(summary))
    print(f"Prezzo 'ottimo' evidenziato fino a: {GREAT_PRICE_EUR} EUR A/R")
    return 0

if __name__ == "__main__":
    sys.exit(main())
