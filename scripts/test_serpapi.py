import os
import sys
import requests

API_URL = "https://serpapi.com/search.json"
DEFAULT_DEPARTURE = "VCE"


def main():
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("ERRORE: secret SERPAPI_KEY non configurato.")
        return 2

    departure_id = os.environ.get("DEPARTURE_ID", DEFAULT_DEPARTURE).strip().upper()
    outbound_date = os.environ.get("OUTBOUND_DATE", "2027-01-09")
    return_date = os.environ.get("RETURN_DATE", "2027-01-10")

    if not departure_id or "," in departure_id:
        print("ERRORE: indicare un solo aeroporto per test.")
        return 2

    params = {
        "engine": "google_travel_explore",
        "departure_id": departure_id,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "EUR",
        "hl": "it",
        "gl": "it",
        "api_key": api_key,
    }

    print(f"Test SerpApi: {departure_id}, {outbound_date} -> {return_date}")
    print("Nota: parametro type omesso (round trip è il default documentato).")
    try:
        response = requests.get(API_URL, params=params, timeout=45)
    except requests.RequestException as exc:
        print(f"ERRORE DI CONNESSIONE: {exc}")
        return 1

    print(f"HTTP status: {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        print("La risposta non è JSON valido.")
        print(response.text[:1000])
        return 1

    metadata = data.get("search_metadata") or {}
    print(f"Stato SerpApi: {metadata.get('status', 'N/D')}")
    if metadata.get("id"):
        print(f"Search ID: {metadata['id']}")

    if response.status_code != 200:
        print(f"ERRORE HTTP: {data.get('error', 'Errore API senza descrizione')}")
        return 1

    api_error = data.get("error")
    if api_error:
        if "Empty results for departure_id" in api_error:
            print(f"NESSUN DATO RESTITUITO DA GOOGLE TRAVEL PER {departure_id}.")
            print("Non è un errore di autenticazione o di esecuzione dello script; la fonte non ha fornito destinazioni per questa ricerca.")
            return 0
        print(f"ERRORE API: {api_error}")
        print("Chiavi risposta:", ", ".join(sorted(data.keys())))
        return 1

    destinations = data.get("destinations") or []
    direct_under_100 = [
        item for item in destinations
        if isinstance(item.get("flight_price"), (int, float))
        and item.get("flight_price") <= 100
        and item.get("number_of_stops") == 0
    ]

    print(f"Destinazioni restituite: {len(destinations)}")
    print(f"Risultati prezzo <= 100 EUR e 0 scali: {len(direct_under_100)}")
    for item in destinations[:15]:
        name = item.get("name") or item.get("destination") or "Destinazione non specificata"
        airport = (item.get("destination_airport") or {}).get("code", "N/D")
        price = item.get("flight_price", "N/D")
        stops = item.get("number_of_stops", "N/D")
        airline = item.get("airline", "N/D")
        start = item.get("start_date", "N/D")
        end = item.get("end_date", "N/D")
        link_present = bool(item.get("link") or item.get("serpapi_link"))
        print(
            f"- {name} ({airport}) | {price} EUR | scali: {stops} "
            f"| {airline} | {start} -> {end} | link: {'sì' if link_present else 'no'}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
