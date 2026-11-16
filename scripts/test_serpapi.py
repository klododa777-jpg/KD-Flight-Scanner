import os
import sys
import requests

API_URL = "https://serpapi.com/search.json"
DEFAULT_DEPARTURES = "VCE,TSF,MXP,BGY"


def main():
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("ERRORE: secret SERPAPI_KEY non configurato.")
        return 2

    departure_ids = [
        code.strip().upper()
        for code in os.environ.get("DEPARTURE_ID", DEFAULT_DEPARTURES).split(",")
        if code.strip()
    ]
    outbound_date = os.environ.get("OUTBOUND_DATE", "2027-01-09")
    return_date = os.environ.get("RETURN_DATE", "2027-01-10")

    if not departure_ids:
        print("ERRORE: nessun aeroporto di partenza configurato.")
        return 2

    total_destinations = 0
    total_direct_under_100 = 0
    failures = []

    for departure_id in departure_ids:
        params = {
            "engine": "google_travel_explore",
            "departure_id": departure_id,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "type": "1",
            "currency": "EUR",
            "hl": "it",
            "gl": "it",
            "api_key": api_key,
        }

        print(f"\\nTest SerpApi: {departure_id}, {outbound_date} -> {return_date}")
        try:
            response = requests.get(API_URL, params=params, timeout=45)
        except requests.RequestException as exc:
            print(f"ERRORE DI CONNESSIONE: {exc}")
            failures.append(departure_id)
            continue

        print(f"HTTP status: {response.status_code}")
        try:
            data = response.json()
        except ValueError:
            print("La risposta non è JSON valido.")
            print(response.text[:1000])
            failures.append(departure_id)
            continue

        if response.status_code != 200 or data.get("error"):
            print(f"ERRORE API: {data.get('error', 'Errore API senza descrizione')}")
            failures.append(departure_id)
            continue

        destinations = data.get("destinations") or []
        total_destinations += len(destinations)
        direct_under_100 = [
            item for item in destinations
            if isinstance(item.get("flight_price"), (int, float))
            and item.get("flight_price") <= 100
            and item.get("number_of_stops") == 0
        ]
        total_direct_under_100 += len(direct_under_100)

        print(f"Destinazioni restituite: {len(destinations)}")
        print(f"Risultati prezzo <= 100 EUR e 0 scali: {len(direct_under_100)}")
        for item in destinations[:8]:
            name = item.get("name") or item.get("destination") or "Destinazione non specificata"
            price = item.get("flight_price", "N/D")
            stops = item.get("number_of_stops", "N/D")
            airline = item.get("airline", "N/D")
            start = item.get("start_date", "N/D")
            end = item.get("end_date", "N/D")
            link_present = bool(item.get("link") or item.get("serpapi_link"))
            print(
                f"- {name} | {price} EUR | scali: {stops} | {airline} "
                f"| {start} -> {end} | link: {'sì' if link_present else 'no'}"
            )

    print("\\nRIEPILOGO")
    print(f"Aeroporti richiesti: {', '.join(departure_ids)}")
    print(f"Chiamate riuscite: {len(departure_ids) - len(failures)}/{len(departure_ids)}")
    print(f"Destinazioni totali restituite: {total_destinations}")
    print(f"Occorrenze dirette sotto 100 EUR: {total_direct_under_100}")
    if failures:
        print(f"Aeroporti con errore: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
