import hashlib
import html
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
MAX_PRICE_EUR = 100
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
        return {"api_usage": {}, "seen_offer_keys": []}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("Formato stato non valido")
        state.setdefault("api_usage", {})
        state.setdefault("seen_offer_keys", [])
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
    new_offers = []
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
                if key in seen:
                    continue

                destination_name = item.get("name") or "Destinazione non specificata"
                country = item.get("country") or "Paese non specificato"
                destination_airport = (item.get("destination_airport") or {}).get("code", "")
                airline = item.get("airline") or "Compagnia non indicata"
                link = item.get("link") or item.get("serpapi_link") or data.get("google_flights_link") or ""
                new_offers.append({
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

    if new_offers:
        for offer in new_offers:
            parts = [
                "✈️ NUOVA OFFERTA WEEKEND",
                f"{offer['destination']}, {offer['country']}",
                f"Partenza: {offer['outbound']} da {offer['airport']} ({offer['airport_name']})",
                f"Ritorno: {offer['return']}",
                f"Prezzo indicato A/R: {offer['price']} EUR",
                f"Volo diretto · {offer['airline']}",
                "Bagaglio: verificare che la tariffa includa lo zaino personale piccolo.",
            ]
            if offer["destination_airport"]:
                parts.insert(2, f"Aeroporto arrivo: {html.escape(offer['destination_airport'])}")
            if offer["link"]:
                parts.append(offer["link"])
            telegram_send(session, telegram_token, telegram_chat, "\n".join(parts))
            seen.add(offer["key"])
            state["seen_offer_keys"] = sorted(seen)
            save_state(state)
    else:
        state["seen_offer_keys"] = sorted(seen)
        save_state(state)

    print(f"Chiamate effettuate: {calls_this_run}")
    print(f"Nuove offerte inviate su Telegram: {len(new_offers)}")
    print(f"Consumo mensile registrato: {used}/{MONTHLY_CALL_CAP}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
