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

    departure_id = os.environ.get("DEPARTURE_ID", DEFAULT_DEPARTURES)
    outbound_date = os.environ.get("OUTBOUND_DATE", "2027-01-09")
    return_date = os.environ.get("RETURN_DATE", "2027-01-10")

    params = {
        "engine": "google_travel_explore",
        "departure_id": departure_id,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "type": "1",  # andata e ritorno
        "currency": "EUR",
        "hl": "it",
        "gl": "it",
        "api_key": api_key,
    }

    print(f"Test SerpApi: {departure_id}, {outbound_date} -> {return_date}")
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

    if response.status_code != 200 or data.get("error"):
        print(f"ERRORE API: {data.get('error', 'Errore API senza descrizione')}")
        return 1

    destinations = data.get("destinations") or []
    print(f"Destinazioni restituite: {len(destinations)}")

    direct_under_100 = []
    for item in destinations:
        price = item.get("flight_price")
        stops = item.get("number_of_stops")
        if isinstance(price, (int, float)) and price <= 100 and stops == 0:
            direct_under_100.append(item)

    print(f"Risultati con prezzo <= 100 EUR e 0 scali: {len(direct_under_100)}")
    print("Prime 15 destinazioni restituite:")
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

    if direct_under_100:
        print("Esempi sotto soglia:")
        for item in direct_under_100[:10]:
            name = item.get("name", "Destinazione non specificata")
            airport = (item.get("destination_airport") or {}).get("code", "N/D")
            print(f"- {name} ({airport}): {item.get('flight_price')} EUR, {item.get('number_of_stops')} scali")

    if not destinations:
        print("La richiesta è stata accettata, ma non sono state restituite destinazioni.")
        print("Campi principali della risposta:", ", ".join(sorted(data.keys())))

    return 0


if __name__ == "__main__":
    sys.exit(main())
