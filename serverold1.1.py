import json
import logging
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
with open(
    "data/flights-dataa-extended.json",
    "r",
    encoding="utf-8"
) as f:
    FLIGHTS_DATA = json.load(f)


def find_cancellation(pnr: str):
    for c in CANCELLATIONS:
        if c.get("pnr") == pnr:
            return c
    return None

def extract_available_seats_from_seatmap(seatmap_json: dict):
    """
    Extracts UNIQUE, assignable, available seats
    with explicit seat types.
    """

    seats = {}
    seat_maps = seatmap_json.get("data", {}).get("seatMaps", [])

    for sm in seat_maps:
        seat_map = sm.get("seatMap", {})
        decks = seat_map.get("decks", {})

        for deck in decks.values():
            compartments = deck.get("compartments", {})

            for cabin in compartments.values():
                units = cabin.get("units", [])

                for seat in units:
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

                    seat_types = []
                    for prop in seat.get("properties", []):
                        code = prop.get("code")
                        if code in {
                            "WINDOW",
                            "AISLE",
                            "LEGROOM",
                            "XL",
                            "STRETCH"
                        }:
                            seat_types.append(code)

                    seats[key] = {
                        "seat_number": seat_number,
                        "travel_class": travel_class,
                        "availability": seat.get("availability"),
                        "seat_type": seat_types
                    }

    return list(seats.values())

def extract_available_flights(flights_json: dict):
    """
    Extract minimal, decision-ready flight data for agent ranking.
    """

    flights = {}

    trips = flights_json.get("data", {}).get("trips", [])

    for trip in trips:
        journeys = trip.get("journeysAvailable", [])

        for journey in journeys:
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

            economy_prices = []
            business_prices = []

            for f in journey.get("passengerFares") or []:
                if f.get("FareClass") == "Economy":
                    economy_prices.append(f.get("totalFareAmount"))
                elif f.get("FareClass") == "Business":
                    business_prices.append(f.get("totalFareAmount"))

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
                "fillingFast": journey.get("fillingFast", False),
                "min_economy_fare": min(economy_prices) if economy_prices else None,
                "min_business_fare": min(business_prices) if business_prices else None
            }

    return list(flights.values())


# SINGLE MCP TOOL 

@mcp.tool()
def recover_passenger(pnr: str, last_name: str):
    """
    FULL recovery in one call.
    This tool ALWAYS returns a FINAL response.
    """

    logger.info("🚑 recover_passenger called")
    logger.info(f"PNR={pnr}, LAST_NAME={last_name}")


    if not pnr or not last_name:
        return {
            "content": [{
                "type": "json",
                "json": {
                    "final": True,
                    "status": "error",
                    "reason": "PNR_AND_LAST_NAME_REQUIRED"
                }
            }]
        }


    cancellation = find_cancellation(pnr)

    if not cancellation:
        return {
            "content": [{
                "type": "json",
                "json": {
                    "final": True,
                    "status": "error",
                    "reason": "PNR_NOT_FOUND"
                }
            }]
        }

    user_info = cancellation.get("user_info", {})
    email = user_info.get("USR_EMAIL")
    phone = str(user_info.get("USR_MOBILE", ""))


    eligibility = validate_request(
        last_name=last_name,
        email_or_phone=email or phone
    )

    if not eligibility or eligibility.get("eligible") is False:
        return {
            "content": [{
                "type": "json",
                "json": {
                    "final": True,
                    "status": "ineligible",
                    "reason": "NOT_HIGHSPENDER_OR_STUDENT"
                }
            }]
        }


    profile = find_users(
        last_name=last_name,
        email_or_phone=email or phone
    )


    available_seats = extract_available_seats_from_seatmap(AVAILABLE_SEATS)


    available_flights = extract_available_flights(FLIGHTS_DATA)



    return {
        "content": [{
            "type": "json",
            "json": {
                "final": True,
                "status": "success",
                "pnr": pnr,
                "passenger": {
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "Past Data": profile
                },
                "original_flight": {
                    "flight_number": cancellation.get("flight_number"),
                    "origin": cancellation.get("origin"),
                    "destination": cancellation.get("destination"),
                    "cabin_class": cancellation.get("cabin_class")
                },
                "recovery": {
                    "available_flights": available_flights,
                    "available_seats": available_seats

                                    }
                                }
                
                            }]
    }
    logger.info("📦 FINAL MCP PAYLOAD (keys only)")
    logger.info({
        "status": final_payload["status"],
        "has_profile": bool(profile),
        "flights_count": len(available_flights),
        "seats_count": len(available_seats)
    })

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8003,
        path="/mcp",
        stateless_http=True
    )
