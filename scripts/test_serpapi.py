import os
import sys
import requests

API_URL = "https://serpapi.com/search.json"

def main():
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("ERRORE: secret SERPAPI_KEY non configurato.")
        return 2

    departure_id = os.environ.get("DEPARTURE_ID", "VCE")
    outbound_date = os.environ.get("OUTBOUND_DATE", "2027-01-09")
    return_date = os.environ.get("RETURN_DATE", "2027-01-10")

    params = {
        "engine": "google_travel_explore",
        "departure_id": departure_id,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "EUR",
        "hl": "it",
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

    if response.status_code != 200:
        error = data.get("error", "Errore API senza descrizione")
        print(f"ERRORE API: {error}")
        return 1

    if data.get("error"):
        print(f"ERRORE API: {data['error']}")
        return 1

    destinations = data.get("destinations") or []
    print(f"Destinazioni restituite: {len(destinations)}")
    for item in destinations[:10]:
        name = item.get("name") or item.get("destination") or "Destinazione non specificata"
        price = item.get("flight_price", item.get("price", "prezzo non indicato"))
        stops = item.get("number_of_stops", "scali non indicati")
        print(f"- {name} | prezzo: {price} | scali: {stops}")

    if not destinations:
        print("La richiesta è stata accettata, ma non sono state restituite destinazioni.")
        print("Campi principali della risposta:", ", ".join(sorted(data.keys())))
    return 0

if __name__ == "__main__":
    sys.exit(main())
