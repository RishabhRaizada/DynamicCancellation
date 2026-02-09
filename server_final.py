import json
import logging
import requests
from fastmcp import FastMCP

from tools.validator import validate_request
from tools.profile import find_users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flight-disruption-mcp")

mcp = FastMCP("flight_disruption_mcp")


with open("data/cancell_trigger.json", "r", encoding="utf-8") as f:
    CANCELLATIONS = json.load(f)

with open("data/available_seats.json", "r", encoding="utf-8") as f:
    AVAILABLE_SEATS = json.load(f)



def find_cancellation(pnr: str):
    for c in CANCELLATIONS:
        if c.get("pnr") == pnr:
            return c
    return None



def call_indigo_flight_search(origin, destination, date):
    url = "https://api-uat-mobile-skyplus6e.goindigo.in/flightsearch/v1/flight/search"

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "user_key": "2945e931b5e99bceed811fd202713432",
        "x-acf-sensor-data": "6,a,CTFQy+MyHDwvPKjyPz1dyxkZGg/tadL9bLYzWkTttUqVRo/RpmSgaiCSlaMHplO6r72BdakC56KbIXX2CqxuSfruob759H352r7aRzZYx9mULpNG+msxUNcQLa0robNX5wDXFYGruYkZFpI9aRF8e4aY68eVzEhq1CnIPAAyaIU=...",
        "source": "android",
        "version": "7.3.3",
        "user-agent": "IndiGoUAT/7.3.3.1 (Android 15; Build/AE3A.240806.036)",
        "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpYmUiLCJqdGkiOiJlMmI5ZDM0Zi04ODFlLTczYWItNDNiMy00YTNhNzg4ZDZiZjkiLCJpc3MiOiJkb3RSRVogQVBJIn0.cIac2owjkUTdlJaDVZ4sz125KPqcurqA8vy-ArTq6S8"
    }

    body = {
        "codes": {"currency": "INR", "vaxDoseNo": ""},
        "criteria": [{
            "dates": {"beginDate": date},
            "flightFilters": {"type": "All"},
            "stations": {
                "originStationCodes": [origin],
                "destinationStationCodes": [destination]
            }
        }],
        "passengers": {
            "residentCountry": "IN",
            "types": [{"count": 1, "discountCode": "", "type": "ADT"}]
        },
        "infantCount": 0,
        "taxesAndFees": "TaxesAndFees",
        "totalPassengerCount": 1,
        "searchType": "OneWay",
        "isRedeemTransaction": False
    }

    response = requests.post(url, json=body, headers=headers, timeout=30)
    
    logger.info("Indigo Status Code: %s", response.status_code)
    logger.info("Indigo Raw Response: %s", response.text[:500])
    
    if response.status_code != 200:
        logger.error("❌ Indigo Flight Search Failed: %s", response.text[:300])
        return {}

    return response.json()



def extract_available_flights(flights_json: dict):
    flights = {}
    trips = flights_json.get("data", {}).get("trips", [])

    for trip in trips:
        for journey in trip.get("journeysAvailable", []):
            segments = journey.get("segments", [])
            if not segments:
                continue

            segment = segments[0]
            identifier = segment.get("identifier", {})
            designator = segment.get("designator", {})

            carrier = identifier.get("carrierCode")
            flight_no = identifier.get("identifier")
            utc_departure = designator.get("utcDeparture")

            if not all([carrier, flight_no, utc_departure]):
                continue

            flight_uid = journey.get("journeyKey")
            if flight_uid in flights:
                continue

            flights[flight_uid] = {
                "flight_uid": flight_uid,
                "flight_number": f"{carrier}{flight_no}",
                "origin": designator.get("origin"),
                "destination": designator.get("destination"),
                "utcDeparture": utc_departure,
                "utcArrival": designator.get("utcArrival"),
                "stops": journey.get("stops"),
                "flightType": journey.get("flightType"),
                "isStretch": segment.get("isStretch", False),
                "fillingFast": journey.get("fillingFast", False)
            }

    return list(flights.values())



def extract_available_seats_from_seatmap(seatmap_json: dict):
    seats = {}
    seat_maps = seatmap_json.get("data", {}).get("seatMaps", [])

    for sm in seat_maps:
        seat_map = sm.get("seatMap", {})
        decks = seat_map.get("decks", {})

        for deck in decks.values():
            compartments = deck.get("compartments", {})

            for cabin in compartments.values():
                for seat in cabin.get("units", []):
                    if not (
                        seat.get("assignable") is True
                        and seat.get("availability", 0) > 0
                    ):
                        continue

                    seat_number = seat.get("designator")
                    travel_class = seat.get("travelClassCode")
                    key = f"{seat_number}-{travel_class}"

                    if key in seats:
                        continue

                    seat_types = [
                        p.get("code")
                        for p in seat.get("properties", [])
                        if p.get("code") in {
                            "WINDOW", "AISLE", "LEGROOM", "XL", "STRETCH"
                        }
                    ]

                    seats[key] = {
                        "seat_number": seat_number,
                        "travel_class": travel_class,
                        "availability": seat.get("availability"),
                        "seat_type": seat_types
                    }

    return list(seats.values())



@mcp.tool()
def recover_passenger(pnr: str, last_name: str):
    logger.info("🚑 recover_passenger called")

    # 1️⃣ Validate input
    if not pnr or not last_name:
        return {"content": [{"type": "json", "json": {
            "final": True, "status": "error", "reason": "PNR_AND_LAST_NAME_REQUIRED"
        }}]}

    # 2️⃣ Find cancellation
    cancellation = find_cancellation(pnr)
    if not cancellation:
        return {"content": [{"type": "json", "json": {
            "final": True, "status": "error", "reason": "PNR_NOT_FOUND"
        }}]}

    # 3️⃣ Disruption check
    if cancellation.get("event_type") != "flight_cancelled":
        return {"content": [{"type": "json", "json": {
            "final": True, "status": "not_applicable", "reason": "NO_FLIGHT_DISRUPTION"
        }}]}

    # 4️⃣ Eligibility
    user_info = cancellation.get("user_info", {})
    email = user_info.get("USR_EMAIL")
    phone = str(user_info.get("USR_MOBILE", ""))

    eligibility = validate_request(last_name=last_name, email_or_phone=email or phone)
    if not eligibility or eligibility.get("eligible") is False:
        return {"content": [{"type": "json", "json": {
            "final": True, "status": "ineligible", "reason": "NOT_ELIGIBLE"
        }}]}

    profile = find_users(last_name=last_name, email_or_phone=email or phone)


    origin = cancellation["origin"]
    destination = cancellation["destination"]
    date = cancellation["scheduled_departure_time"][:10]

    flight_search_response = call_indigo_flight_search(origin, destination, date)

    available_flights = extract_available_flights(flight_search_response)
    available_seats = extract_available_seats_from_seatmap(AVAILABLE_SEATS)
    logger.info("🗓️ Indigo search date being used: %s", date)
    logger.info("📍 Route: %s → %s", origin, destination)
    logger.info("✈️ Extracted flights count: %d", len(available_flights))
    logger.info("🧾 SAMPLE REAL FLIGHTS FROM INDIGO API:")
    for i, f in enumerate(available_flights[:5]):  # print first 5 only
        logger.info("FLIGHT %d → %s", i+1, json.dumps(f, indent=2))
    # 8️⃣ Final Payload
    final_payload = {
        "final": True,
        "status": "success",
        "pnr": pnr,
        "passenger": {
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "past_data": profile
        },
        "original_flight": cancellation,
        "recovery": {
            "available_flights": available_flights,
            "available_seats": available_seats
        }
    }

    return {"content": [{"type": "json", "json": final_payload}]}



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8003,
        path="/mcp",
        stateless_http=True
    )