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



@mcp.tool()
def prepare_recovery_context(pnr: str, last_name: str) -> str:
    """
    FINAL recovery tool for Azure Agent.
    Takes PNR and last name, returns recovery details as JSON string.
    """
    logger.info("=" * 60)
    logger.info("🚀 Azure Agent calling prepare_recovery_context")
    logger.info(f"📋 PNR: {pnr}, Last Name: {last_name}")

    if not pnr or not last_name:
        return json.dumps({
            "error": "PNR_AND_LAST_NAME_REQUIRED",
            "message": "Both PNR and Last Name are required"
        })

    event = next((c for c in CANCELLATIONS if c.get("pnr") == pnr), None)
    
    if not event:
        return json.dumps({
            "error": "PNR_NOT_FOUND",
            "message": f"PNR {pnr} not found in cancellation records"
        })

    user_info = event.get("user_info", {})
    email = user_info.get("USR_EMAIL")
    phone = str(user_info.get("USR_MOBILE", ""))

    # 3. Eligibility check
    eligibility = validate_request(
        last_name=last_name,
        email_or_phone=email or phone
    )
    
    logger.info(f"📊 Eligibility result: {eligibility}")

    if not eligibility or eligibility.get("eligible") is False:
        return json.dumps({
            "error": "NOT_ELIGIBLE",
            "message": "Passenger not eligible for recovery",
            "details": eligibility
        })

    # 4. Fetch CDP profile
    profile = find_users(last_name=last_name, email_or_phone=email or phone)
    
    # 5. Find best available seat
    best_seat = None
    for flight in AVAILABLE_SEATS:
        for seat in flight.get("seats", []):
            if seat.get("available") is True:
                best_seat = seat
                break
        if best_seat:
            break

    # 6. Prepare final response
    response = {
        "status": "SUCCESS",
        "recovery_id": f"REC-{pnr}-{int(time.time())}",
        "passenger": {
            "pnr": pnr,
            "last_name": last_name,
            "first_name": user_info.get("USR_FIRSTNAME", ""),
            "email": email,
            "phone": phone,
            "eligibility": eligibility
        },
        "cancelled_flight": {
            "flight_number": event.get("flight_number"),
            "origin": event.get("origin"),
            "destination": event.get("destination"),
            "scheduled_departure": event.get("scheduled_departure"),
            "cabin_class": event.get("cabin_class")
        },
        "recovery_flight": AVAILABLE_SEATS[0] if AVAILABLE_SEATS else None,
        "assigned_seat": best_seat,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "instructions": "Passenger has been rebooked on the next available flight"
    }
    
    logger.info("✅ Recovery context prepared successfully")
    logger.info(f"📦 Response: {json.dumps(response, indent=2)}")
    
    return json.dumps(response, indent=2)

# -------------------------------------------------
# Add missing import
# -------------------------------------------------
import time

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------

if __name__ == "__main__":
    logger.info("🚀 MCP Server starting on http://127.0.0.1:8003/mcp")
    logger.info("🛠️ Available tool: prepare_recovery_context")
    logger.info("📡 Waiting for Azure Agent connections...")
    
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8003,
        path="/mcp"
    )