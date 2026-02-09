import requests
 
url = "https://api-uat-mobile-skyplus6e.goindigo.in/flightsearch/v1/flight/search"
 
headers = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "user_key": "2945e931b5e99bceed811fd202713432",
    "x-acf-sensor-data": "6,a,CTFQy+MyHDwvPKjyPz1dyxkZGg/tadL9bLYzWkTttUqVRo/RpmSgaiCSlaMHplO6r72BdakC56KbIXX2CqxuSfruob759H352r7aRzZYx9mULpNG+msxUNcQLa0robNX5wDXFYGruYkZFpI9aRF8e4aY68eVzEhq1CnIPAAyaIU=,...$$$",
    "source": "android",
    "version": "7.3.3",
    "user-agent": "IndiGoUAT/7.3.3.1 (Android 15)",
    "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpYmUiLCJqdGkiOiJkZDhmZTg0OC02MDVlLWYxOTAtNjBhOC1hMWMyODBiZDFlN2MiLCJpc3MiOiJkb3RSRVogQVBJIn0.3Mum11wMQmWbbrmgTVXCvnCzKJufCPVhLJI5ZHPjA98"
}
 
body = {
    "codes": {"currency": "INR"},
    "criteria": [{
        "dates": {"beginDate": "2026-02-05"},
        "stations": {
            "originStationCodes": ["DEL"],
            "destinationStationCodes": ["GOI"]
        }
    }],
    "passengers": {
        "residentCountry": "IN",
        "types": [{"count": 1, "type": "ADT"}]
    },
    "searchType": "OneWay"
}
 
r = requests.post(url, json=body, headers=headers, allow_redirects=False)
 
print("Status:", r.status_code)
print("Final URL:", r.url)
print("History:", r.history)
print(r.text)

# import requests
# import logging

# logger = logging.getLogger(__name__)


# def flight_search_api():
#     url = "https://api-uat-mobile-skyplus6e.goindigo.in/flightsearch/v1/flight/search"

#     headers = {
#         "accept": "application/json, text/plain, */*",
#         "content-type": "application/json",
#         "user_key": "2945e931b5e99bceed811fd202713432",

#         # Must be EXACT one-line sensor string
#         "x-acf-sensor-data": "6,a,CTFQy+MyHDwvPKjyPz1dyxkZGg/tadL9bLYzWkTttUqVRo/RpmSgaiCSlaMHplO6r72BdakC56KbIXX2CqxuSfruob759H352r7aRzZYx9mULpNG+msxUNcQLa0robNX5wDXFYGruYkZFpI9aRF8e4aY68eVzEhq1CnIPAAyaIU=,...$$$",

#         "source": "android",
#         "version": "7.3.3",
#         "user-agent": "IndiGoUAT/7.3.3.1 (Android 15)",

#         "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpYmUiLCJqdGkiOiI5NjJmNGIyYy1lMzRiLTgxNGYtMWEzNy1iMjE1OTRlMmE5YWQiLCJpc3MiOiJkb3RSRVogQVBJIn0.s52SiSYB8kougO190kR22NL75aHtFiPRWSy_3oNV3f8"
#     }

#     body = {
#         "codes": {"currency": "INR"},
#         "criteria": [{
#             "dates": {"beginDate": "2026-01-08"},
#             "stations": {
#                 "originStationCodes": ["DEL"],
#                 "destinationStationCodes": ["GOI"]
#             }
#         }],
#         "passengers": {
#             "residentCountry": "IN",
#             "types": [{"count": 1, "type": "ADT"}]
#         },
#         "searchType": "OneWay"
#     }

#     try:
#         response = requests.post(
#             url,
#             json=body,
#             headers=headers,
#             allow_redirects=False,
#             timeout=30
#         )

#         print("Status:", response.status_code)
#         print("Final URL:", response.url)
#         print("History:", response.history)
#         print("Raw Response:", response.text[:500], "...")

#         if response.status_code == 200:
#             return response.json()

#         logger.error("Flight search failed with status %s", response.status_code)
#         return {}

#     except Exception:
#         logger.exception("Flight search API call crashed")
#         return {}


# def extract_flight_data(api_response):
#     flights = []

#     data = (api_response or {}).get("data") or {}
#     trips = data.get("trips", [])

#     for trip in trips:
#         for journey in trip.get("journeysAvailable", []):
#             segments = journey.get("segments", [])
#             if not segments:
#                 continue

#             segment = segments[0]
#             identifier = segment.get("identifier", {})
#             designator = segment.get("designator", {})

#             flights.append({
#                 "flightNumber": f"{identifier.get('carrierCode')}{identifier.get('identifier')}",
#                 "origin": designator.get("origin"),
#                 "destination": designator.get("destination"),
#                 "departureTime": designator.get("utcDeparture"),
#                 "arrivalTime": designator.get("utcArrival"),
#                 "stops": journey.get("stops", 0),
#                 "flightType": journey.get("flightType", "Direct")
#             })

#     return flights


# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)

#     api_response = flight_search_api()

#     if not api_response:
#         print("❌ Flight Search API returned no data")
#         exit(1)

#     flights = extract_flight_data(api_response)

#     if not flights:
#         print("⚠️ No flights found for given search criteria")
#     else:
#         print(f"✅ Found {len(flights)} flights:\n")
#         for idx, flight in enumerate(flights, start=1):
#             print(f"{idx}. Flight Number : {flight['flightNumber']}")
#             print(f"   Route         : {flight['origin']} → {flight['destination']}")
#             print(f"   Departure     : {flight['departureTime']}")
#             print(f"   Arrival       : {flight['arrivalTime']}")
#             print(f"   Stops         : {flight['stops']}")
#             print(f"   Type          : {flight['flightType']}")
#             print("-" * 50)