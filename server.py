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

with open("data/flights-dataa-extended.json", "r", encoding="utf-8") as f:
    FLIGHTS_DATA = json.load(f)


def find_cancellation(pnr: str):
    for c in CANCELLATIONS:
        if c.get("pnr") == pnr:
            return c
    return None


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

            economy = []
            business = []

            for f in journey.get("passengerFares") or []:
                if f.get("FareClass") == "Economy":
                    economy.append(f.get("totalFareAmount"))
                elif f.get("FareClass") == "Business":
                    business.append(f.get("totalFareAmount"))

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
                "min_economy_fare": min(economy) if economy else None,
                "min_business_fare": min(business) if business else None
            }

    return list(flights.values())


@mcp.tool()
def recover_passenger(pnr: str, last_name: str):
    logger.info("🚑 recover_passenger called")
    logger.info("PNR=%s LAST_NAME=%s", pnr, last_name)

    # 1️⃣ Validate input
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

    # 2️⃣ Find cancellation
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

    # 3️⃣ Disruption gate (CRITICAL)
    event_type = cancellation.get("event_type")
    logger.info("📡 Event type: %s", event_type)

    if event_type != "flight_cancelled":
        logger.warning("🚫 No disruption — recovery not applicable")

        return {
            "content": [{
                "type": "json",
                "json": {
                    "final": True,
                    "status": "not_applicable",
                    "reason": "NO_FLIGHT_DISRUPTION",
                    "pnr": pnr
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
        logger.warning("🚫 Passenger not eligible for recovery")

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

    logger.info("✈️ Flights extracted: %d", len(available_flights))
    logger.info("💺 Seats extracted: %d", len(available_seats))
    logger.info("📊 Profile records: %d", len(profile) if profile else 0)

    final_payload = {
        "final": True,
        "status": "success",
        "pnr": pnr,
        "passenger": {
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "Past Data": profile
        },
        "original_flight": cancellation,
        "recovery": {
            "available_flights": available_flights,
            "available_seats": available_seats
        }
    }

    logger.info("📦 FINAL MCP PAYLOAD SUMMARY")
    logger.info({
        "status": final_payload["status"],
        "has_profile": bool(profile),
        "flights_count": len(available_flights),
        "seats_count": len(available_seats)
    })
    logger.info("✈️ Available Flights (FULL):")
    for idx, f in enumerate(available_flights):
        logger.info(f"[FLIGHT {idx}] {json.dumps(f, indent=2)}")
    return {
        "content": [{
            "type": "json",
            "json": final_payload
        }]
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8003,
        path="/mcp",
        stateless_http=True
    )
