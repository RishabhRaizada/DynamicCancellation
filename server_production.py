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

# with open("data/available_seats.json", "r", encoding="utf-8") as f:
#     AVAILABLE_SEATS = json.load(f)



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
        "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpYmUiLCJqdGkiOiIzYjRiZjY3Yy0xZDRiLWM1MzYtNzFhZS0yZjQ0OWI3ZjJmNzgiLCJpc3MiOiJkb3RSRVogQVBJIn0.MUVZcWZ4Va8St-nqoCq7NvyEowGjB4RhS-YMmqaPh-M"
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


def call_indigo_seat_map():
    url = "https://api-uat-mobile-skyplus6e.goindigo.in/seatselection/v1/seat/getentireseats"

    headers = {
        'accept': "application/json, text/plain, */*",
        'user_key': "2945e931b5e99bceed811fd202713432",
        'x-acf-sensor-data': "6,a,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,14,15",
        'source': "android",
        'version': "7.3.3",
        'user-agent': "IndiGoUAT/7.3.3.1 (Android 15; Build/AE3A.240806.036)",
        'authorization': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpYmUiLCJqdGkiOiI1NWJiYjVhYy04ZDQxLTFkMTItYzNmNC00ZjgwMzM0ZmEwZDUiLCJpc3MiOiJkb3RSRVogQVBJIn0._F44rs8GDrSGuOzckIBBasHsNTJkX7NksPnYjJ0mcPA"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        logger.info("🪑 Indigo Seat API Status: %s", response.status_code)

        if not response.content:
            logger.warning("⚠️ Seat API returned EMPTY body")
            return None

        try:
            seat_json = response.json()
        except Exception as e:
            logger.error("❌ Seat API response is NOT JSON: %s", e)
            logger.error("🪑 Raw seat API response (first 500): %s", response.text[:500])
            return None

        if isinstance(seat_json, dict):
            logger.info("🪑 Seat API top-level keys: %s", list(seat_json.keys()))

            data = seat_json.get("data")
            logger.info("🪑 Seat API 'data' type: %s", type(data))

            if isinstance(data, dict):
                logger.info("🪑 Seat API 'data' keys: %s", list(data.keys()))

                seat_maps = data.get("seatMaps")
                logger.info(
                    "🪑 seatMaps type: %s | count: %s",
                    type(seat_maps),
                    len(seat_maps) if isinstance(seat_maps, list) else "N/A"
                )
        else:
            logger.warning("⚠️ Seat API returned non-dict JSON")

        # ---------------- PREVIEW ----------------
        logger.info(
            "🪑 Seat API JSON preview (first 300): %s",
            str(seat_json)[:300]
        )

        return seat_json

    except Exception as e:
        logger.error("❌ Seat API call failed: %s", e)
        return None

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


# def extract_available_seats_from_seatmap(seatmap_json: dict):
#     logger.info("🪑 Starting live seat extraction")

#     if not seatmap_json or not isinstance(seatmap_json, dict):
#         logger.warning("⚠️ Seat map response invalid or None")
#         return []

#     data = seatmap_json.get("data")
#     if not isinstance(data, dict):
#         logger.warning("⚠️ Seat map 'data' missing or null")
#         return []

#     seat_maps = data.get("seatMaps", [])
#     if not seat_maps:
#         logger.warning("⚠️ No seatMaps found in seat API response")
#         return []

#     seats = {}

#     for sm in seat_maps:
#         seat_map = sm.get("seatMap", {})
#         decks = seat_map.get("decks", {})

#         for deck in decks.values():
#             compartments = deck.get("compartments", {})

#             for cabin in compartments.values():
#                 for seat in cabin.get("units", []):
#                     if not (
#                         seat.get("assignable") is True
#                         and seat.get("availability", 0) > 0
#                     ):
#                         continue

#                     seat_number = seat.get("designator")
#                     travel_class = seat.get("travelClassCode")

#                     if not seat_number or not travel_class:
#                         continue

#                     key = f"{seat_number}-{travel_class}"
#                     if key in seats:
#                         continue

#                     seats[key] = {
#                         "seat_number": seat_number,
#                         "travel_class": travel_class,
#                         "availability": seat.get("availability"),
#                         "seat_type": [
#                             p.get("code") for p in seat.get("properties", [])
#                             if p.get("code") in {
#                                 "WINDOW", "AISLE", "LEGROOM", "XL", "STRETCH"
#                             }
#                         ]
#                     }

#     logger.info("🪑 Live seats extracted: %d", len(seats))
#     return list(seats.values())

# def extract_available_seats_from_seatmap(seatmap_json: dict):

#     """
#     Extract seats and attach pricing ONLY from API fee groups.
#     No defaults, no assumptions.
#     """

#     if not seatmap_json or "data" not in seatmap_json:
#         return []

#     data = seatmap_json["data"]

#     seat_maps = data.get("seatMaps", [])
#     fees_root = data.get("fees", {})

#     # Build group → price lookup
#     group_price_map = {}

#     for passenger in fees_root.values():
#         groups = passenger.get("groups", {})
#         for group_id, group_obj in groups.items():
#             fee_list = group_obj.get("fees", [])
#             if not fee_list:
#                 continue

#             fee = fee_list[0]
#             service_charges = fee.get("serviceCharges", [])

#             currency = None
#             amount = fee.get("finalPrice")

#             if service_charges:
#                 currency = service_charges[0].get("currencyCode")

#             group_price_map[int(group_id)] = {
#                 "amount": amount,
#                 "currency": currency,
#                 "code": fee.get("code")
#             }

#     seats = []

#     for sm in seat_maps:
#         decks = sm.get("seatMap", {}).get("decks", {})

#         for deck in decks.values():
#             compartments = deck.get("compartments", {})

#             for cabin in compartments.values():
#                 for seat in cabin.get("units", []):
#                     if not seat.get("assignable") or seat.get("availability", 0) <= 0:
#                         continue

#                     group_id = seat.get("group")
#                     pricing = group_price_map.get(group_id)

#                     seat_obj = {
#                         "seat_number": seat.get("designator"),
#                         "travel_class": seat.get("travelClassCode"),
#                         "seat_type": [
#                             p.get("code") for p in seat.get("properties", [])
#                         ],
#                         "availability": seat.get("availability")
#                     }

#                     # Attach pricing ONLY if API provided it
#                     if pricing:
#                         seat_obj["pricing"] = pricing

#                     seats.append(seat_obj)

#     return seats

def build_seat_price_map(seatmap_json: dict):
    logger.info("💰 Building seat price map")

    price_map = {}

    if not seatmap_json or "data" not in seatmap_json:
        return price_map

    category_raw = seatmap_json["data"].get("category")

    # 🔑 NORMALIZE category → list
    if isinstance(category_raw, dict):
        categories = category_raw.values()
    elif isinstance(category_raw, list):
        categories = category_raw
    else:
        logger.warning("⚠️ Unknown category format: %s", type(category_raw))
        return price_map

    for category in categories:
        if not isinstance(category, dict):
            continue

        groups = category.get("groups", [])
        for group in groups:
            if not isinstance(group, dict):
                continue

            group_key = group.get("groupKey")
            fees = group.get("fees", [])

            if not group_key or not fees:
                continue

            fee = fees[0]
            price_map[group_key] = {
                "amount": fee.get("amount"),
                "currency": fee.get("currency")
            }

    logger.info("💰 Price groups found: %d", len(price_map))
    return price_map

def debug_seatmap_structure(seatmap_json: dict):
    """Debug the actual structure of the seatmap response"""
    logger.info("🔍 DEBUG: Analyzing seatmap response structure")
    
    if not seatmap_json:
        logger.warning("⚠️ No seatmap JSON received")
        return
    
    data = seatmap_json.get("data", {})
    
    # Check top-level keys
    logger.info("📋 Top-level data keys: %s", list(data.keys()))
    
    # Check if fees exists
    fees = data.get("fees", {})
    logger.info("💰 Fees type: %s, keys: %s", type(fees), list(fees.keys()))
    
    # Check category (old location)
    category = data.get("category", {})
    logger.info("📊 Category type: %s", type(category))
    
    # Check seatMaps
    seat_maps = data.get("seatMaps", [])
    logger.info("🪑 Seat maps count: %d", len(seat_maps))
    
    # If there are seats, show first seat's structure
    if seat_maps:
        first_map = seat_maps[0]
        seat_map = first_map.get("seatMap", {})
        if seat_map:
            decks = seat_map.get("decks", {})
            logger.info("📦 Decks count: %d", len(decks))
            
            # Check first seat for group info
            for deck_key, deck in decks.items():
                compartments = deck.get("compartments", {})
                for comp_key, compartment in compartments.items():
                    units = compartment.get("units", [])
                    if units:
                        first_seat = units[0]
                        logger.info("💺 First seat in %s/%s: %s", deck_key, comp_key, {
                            "designator": first_seat.get("designator"),
                            "group": first_seat.get("group"),
                            "assignable": first_seat.get("assignable"),
                            "availability": first_seat.get("availability")
                        })
                        break
                break

# def extract_available_seats_from_seatmap(seatmap_json: dict):
#     """
#     Extract available seats and attach pricing using:
#     seat.priceGroupKey → data.category.groups.fees
#     """

#     logger.info("🪑 Starting live seat extraction WITH pricing")

#     if not seatmap_json or "data" not in seatmap_json:
#         logger.warning("⚠️ Seat map JSON missing or invalid")
#         return []

#     data = seatmap_json["data"]
#     seat_maps = data.get("seatMaps", [])

#     if not seat_maps:
#         logger.warning("⚠️ No seatMaps found")
#         return []

#     # ✅ Build price lookup ONCE
#     price_map = build_seat_price_map(seatmap_json)

#     seats = []
#     priced_count = 0
#     unpriced_count = 0

#     for sm in seat_maps:
#         seat_map = sm.get("seatMap", {})
#         decks = seat_map.get("decks", {})

#         for deck in decks.values():
#             compartments = deck.get("compartments", {})

#             for cabin in compartments.values():
#                 for seat in cabin.get("units", []):
#                     if not seat.get("assignable") or seat.get("availability", 0) <= 0:
#                         continue

#                     seat_number = seat.get("designator")
#                     group_key = seat.get("priceGroupKey")
#                     pricing = price_map.get(group_key)

#                     seat_obj = {
#                         "seat_number": seat_number,
#                         "travel_class": seat.get("travelClassCode"),
#                         "availability": seat.get("availability"),
#                         "seat_type": [
#                             p.get("code") for p in seat.get("properties", [])
#                         ],
#                         "price_group": group_key
#                     }

#                     if pricing:
#                         seat_obj["pricing"] = pricing
#                         priced_count += 1
#                     else:
#                         unpriced_count += 1

#                     seats.append(seat_obj)

#     logger.info("🪑 Seats with pricing: %d", priced_count)
#     logger.info("🪑 Seats without pricing: %d", unpriced_count)
#     logger.info("🪑 Total available seats: %d", len(seats))

#     return seats


def extract_available_seats_from_seatmap(seatmap_json: dict):
    """
    Extract available seats using ONLY real API values.
    No estimations - if API returns 0.0 or no pricing, we return that.
    """

    logger.info("🪑 Extracting seats with REAL API values only")

    if not seatmap_json or "data" not in seatmap_json:
        logger.warning("⚠️ Seat map JSON missing or invalid")
        return []

    data = seatmap_json["data"]
    seat_maps = data.get("seatMaps", [])
    
    seats = []
    seats_with_pricing = 0
    seats_without_pricing = 0

    for sm in seat_maps:
        seat_map = sm.get("seatMap", {})
        decks = seat_map.get("decks", {})

        for deck in decks.values():
            compartments = deck.get("compartments", {})

            for cabin in compartments.values():
                for seat in cabin.get("units", []):
                    # Skip non-assignable or unavailable seats
                    if not seat.get("assignable") or seat.get("availability", 0) <= 0:
                        continue

                    seat_number = seat.get("designator")
                    
                    # Create seat object with ONLY API data
                    seat_obj = {
                        "seat_number": seat_number,
                        "travel_class": seat.get("travelClassCode", "Y"),
                        "availability": seat.get("availability"),
                        "seat_type": [
                            p.get("code") for p in seat.get("properties", [])
                        ],
                        "group": seat.get("group"),
                        "compartment": seat.get("compartmentDesignator"),
                        "zone": seat.get("zone"),
                        "deck": deck.get("number", 1)
                    }

                    # Check if ANY pricing exists in the API response
                    # Look for pricing in category data
                    category_data = data.get("category", {})
                    found_pricing = None
                    
                    for category_name, category_items in category_data.items():
                        if isinstance(category_items, list):
                            for item in category_items:
                                if isinstance(item, dict):
                                    # Check if this seat matches any seat list
                                    seats_list = item.get("seats", "")
                                    if seat_number in seats_list:
                                        min_price = item.get("minPrice")
                                        if min_price is not None:
                                            found_pricing = {
                                                "amount": min_price,
                                                "currency": "INR",
                                                "source": category_name,
                                                "is_real_api_price": True
                                            }
                                            break
                    
                    # If found real pricing, add it
                    if found_pricing:
                        seat_obj["pricing"] = found_pricing
                        seats_with_pricing += 1
                    else:
                        # No pricing found in API for this seat
                        seats_without_pricing += 1
                        # DO NOT add any estimated pricing

                    seats.append(seat_obj)

    # Log summary
    logger.info("📊 Results (REAL API DATA ONLY):")
    logger.info("  Total available seats: %d", len(seats))
    logger.info("  Seats with API pricing data: %d", seats_with_pricing)
    logger.info("  Seats without API pricing data: %d", seats_without_pricing)
    
    # Show what we actually got from API
    if seats:
        # Show seat counts by class
        class_counts = {}
        for seat in seats:
            travel_class = seat.get("travel_class", "UNKNOWN")
            class_counts[travel_class] = class_counts.get(travel_class, 0) + 1
        
        logger.info("  Seat classes: %s", class_counts)
        
        # Show a few examples
        logger.info("  Sample seats (first 3):")
        for i, seat in enumerate(seats[:3]):
            pricing_info = seat.get("pricing", {})
            price_amount = pricing_info.get("amount", "NO PRICE") if pricing_info else "NO PRICE"
            logger.info("    %d. %s (%s): ₹%s", 
                      i+1, 
                      seat["seat_number"], 
                      seat["travel_class"],
                      price_amount)

    return seats

# def extract_available_seats_from_seatmap(seatmap_json: dict):
#     """
#     Extract available seats with REAL API pricing.
#     The API returns 0.0 prices with empty seat lists, so we use those prices.
#     """
    
#     logger.info("🪑 Extracting seats with REAL API pricing")
    
#     if not seatmap_json or "data" not in seatmap_json:
#         return []
    
#     data = seatmap_json["data"]
#     seat_maps = data.get("seatMaps", [])
#     category_data = data.get("category", {})
    
#     # Get pricing from category (even if it's 0.0)
#     category_prices = {}
    
#     for category_name, category_items in category_data.items():
#         if isinstance(category_items, list):
#             for item in category_items:
#                 if isinstance(item, dict):
#                     # Get the flight-specific pricing
#                     for flight_key, price_info in item.items():
#                         if isinstance(price_info, dict):
#                             min_price = price_info.get("minPrice")
#                             if min_price is not None:
#                                 # Store the category price
#                                 category_prices[category_name] = {
#                                     "amount": min_price,
#                                     "currency": "INR",
#                                     "source": f"category_{category_name}",
#                                     "note": f"From API category: {category_name}"
#                                 }
#                                 logger.info("💰 Category '%s' price: ₹%s", 
#                                           category_name, min_price)
    
#     logger.info("📊 Found %d price categories in API", len(category_prices))
    
#     seats = []
    
#     for sm in seat_maps:
#         seat_map = sm.get("seatMap", {})
#         decks = seat_map.get("decks", {})
        
#         for deck in decks.values():
#             compartments = deck.get("compartments", {})
            
#             for cabin in compartments.values():
#                 for seat in cabin.get("units", []):
#                     if not seat.get("assignable") or seat.get("availability", 0) <= 0:
#                         continue
                    
#                     seat_number = seat.get("designator")
#                     travel_class = seat.get("travelClassCode", "Y")
                    
#                     # Create seat object
#                     seat_obj = {
#                         "seat_number": seat_number,
#                         "travel_class": travel_class,
#                         "availability": seat.get("availability"),
#                         "seat_type": [p.get("code") for p in seat.get("properties", [])],
#                         "group": seat.get("group"),
#                         "compartment": seat.get("compartmentDesignator")
#                     }
                    
#                     # Determine which category this seat belongs to
#                     # Based on seat properties and class
#                     assigned_category = None
#                     seat_props = seat_obj["seat_type"]
                    
#                     if travel_class == "C":  # Business Class
#                         assigned_category = "xlSeat"  # or whatever category for business
#                     elif "EXITROW" in seat_props or "LEGROOM" in seat_props:
#                         assigned_category = "xlSeat"
#                     elif "WINDOW" in seat_props or "AISLE" in seat_props:
#                         assigned_category = "standardSeat"
#                     else:
#                         assigned_category = "allSeats"
                    
#                     if assigned_category in category_prices:
#                         seat_obj["pricing"] = category_prices[assigned_category]
#                         seat_obj["price_category"] = assigned_category
#                     else:
#                         if category_prices:
#                             first_category = list(category_prices.keys())[0]
#                             seat_obj["pricing"] = category_prices[first_category]
#                             seat_obj["price_category"] = first_category
                    
#                     seats.append(seat_obj)
    
#     logger.info("✅ Extracted %d seats with API pricing", len(seats))
    
#     # Show pricing summary
#     if seats:
#         price_summary = {}
#         for seat in seats:
#             price = seat.get("pricing", {}).get("amount", "NO_PRICE")
#             category = seat.get("price_category", "UNKNOWN")
#             key = f"{category}_₹{price}"
#             price_summary[key] = price_summary.get(key, 0) + 1
        
#         logger.info("💰 Pricing summary:")
#         for price_key, count in price_summary.items():
#             logger.info("  %s: %d seats", price_key, count)
    
#     return seats


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

    seat_map_response = call_indigo_seat_map()
    # debug_seatmap_structure(seat_map_response)
    # if seat_map_response and "data" in seat_map_response:
    #     # Print a small sample of the data
    #     import json
    #     sample = json.dumps(seat_map_response["data"], indent=2)[:500]
    #     logger.info("📄 Sample data structure: %s", sample)
    
    available_seats = extract_available_seats_from_seatmap(seat_map_response)
    origin = cancellation["origin"]
    destination = cancellation["destination"]
    date = cancellation["scheduled_departure_time"][:10]

    flight_search_response = call_indigo_flight_search(origin, destination, date)

    available_flights = extract_available_flights(flight_search_response)
    # available_seats = extract_available_seats_from_seatmap(AVAILABLE_SEATS)
    seat_map_response = call_indigo_seat_map()

    logger.info("🪑 Seat map response type: %s", type(seat_map_response))
    logger.info("🪑 Seat map response preview: %s", str(seat_map_response)[:300])
    available_seats = extract_available_seats_from_seatmap(seat_map_response)

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