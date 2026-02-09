import sys
import json
import requests
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder


PROJECT_ENDPOINT = "https://testapiagent-resource.services.ai.azure.com/api/projects/testapiagent"
AGENT_ID = "asst_fVKKUVovJ6FGONPYJOV3pe21"

MCP_URL = "http://127.0.0.1:8003/mcp"


def execute_mcp_tool(tool_name: str, arguments: dict):
    print(f"🔮 Executing {tool_name} via MCP")
    print(f"📝 Arguments: {arguments}")

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }

    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }

    response = requests.post(MCP_URL, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"MCP call failed: {response.status_code} {response.text}")


    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue

        raw = line.replace("data:", "", 1).strip()
        mcp_payload = json.loads(raw)

        result = mcp_payload.get("result", {})

        structured = result.get("structuredContent", {})
        content = structured.get("content", [])

        if content and content[0].get("type") == "json":
            print("✅ MCP JSON received (structuredContent)")
            return content[0]["json"]

        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    embedded = json.loads(item["text"])
                    for c in embedded.get("content", []):
                        if c.get("type") == "json":
                            print("✅ MCP JSON received (embedded text)")
                            return c["json"]
                except Exception:
                    pass

    raise RuntimeError("No MCP JSON response found in SSE stream")



def run_agent(pnr: str, last_name: str):
    print("\n🚀 Running manual MCP + Agent reasoning")
    print(f"PNR: {pnr}, LAST NAME: {last_name}")

    # ==============================
    # 1️⃣ CALL MCP
    # ==============================
    mcp_data = execute_mcp_tool(
        "recover_passenger",
        {"pnr": pnr, "last_name": last_name}
    )

    print("\n📦 MCP RESPONSE:")
    print(json.dumps(mcp_data, indent=2))

    # ==============================
    # 2️⃣ HARD STOP IF NOT ELIGIBLE
    # ==============================
    status = mcp_data.get("status")

    if status != "success":
        print("\n⛔ RECOVERY FLOW STOPPED")
        print(json.dumps({
            "status": status,
            "reason": mcp_data.get("reason"),
            "message": "Passenger not eligible for auto-recovery. Agent NOT invoked."
        }, indent=2))
        return  # 🚨 ABSOLUTE STOP — AGENT WILL NEVER RUN

    # ==============================
    # 3️⃣ SAFETY CHECK (DEFENSIVE)
    # ==============================
    recovery = mcp_data.get("recovery", {})
    if not recovery.get("available_flights") or not recovery.get("available_seats"):
        print("\n⛔ INCOMPLETE RECOVERY CONTEXT")
        print("Flights or seats missing — agent invocation blocked.")
        return

    # ==============================
    # 4️⃣ AGENT INVOCATION (SUCCESS ONLY)
    # ==============================
    client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential()
    )

    with client:
        thread = client.agents.threads.create()

        client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""
You are a STRICT Flight & Seat Recovery Decision Engine.
Passenger Profile:
--------------------------------
INPUT DATA (ACTUAL MCP RESPONSE - THIS IS YOUR UNIVERSE)
--------------------------------

Passenger Profile:
{json.dumps(mcp_data.get('passenger', {}), indent=2)}

Original Flight:
{json.dumps(mcp_data.get('original_flight', {}), indent=2)}

Available Flights (YOU MUST SELECT FROM THIS LIST):
{json.dumps(recovery.get('available_flights', []), indent=2)}

Available Seats (YOU MUST SELECT FROM THIS LIST):
{json.dumps(recovery.get('available_seats', []), indent=2)}
You are a STRICT Flight & Seat Optimization Engine.

ABSOLUTE RULES (FAIL IF VIOLATED):
1. You MUST ONLY use flights and seats provided in the input JSON.
2. You MUST NOT invent flight_uid, flight_number, seat_number, or prices.
3. If any identifier is not found in the input → FAIL.
--------------------------------
ORIGINAL BOOKING CONSTRAINTS (MANDATORY)
--------------------------------

The original_flight represents the passenger's contractual booking intent.

MANDATORY RULES:

1. Route Preservation:
- selected_flight.origin MUST equal original_flight.origin
- selected_flight.destination MUST equal original_flight.destination
- If no such flight exists → FAIL

2. Time Proximity:
- Prefer flights whose utcDeparture is closest to original_flight.utc_scheduled_departure
- Prefer earlier arrival over later arrival when possible

3. Cabin Preservation:
- If original_flight.cabin_class == "Business":
  - Must preserve Business cabin in recovery
  - Only downgrade if no business seats exist
- If original_flight.cabin_class == "Economy":
  - Economy acceptable, upgrade optional for highspender

These rules apply BEFORE CDP logic.
CDP rules apply only after these booking constraints are satisfied.

--------------------------------
PRIORITY 0 (ORIGINAL BOOKING OVERRIDE)
--------------------------------

If original_flight.cabin_class == "Business":
- ALWAYS select a flight that has min_business_fare available
- ALWAYS select a seat with travel_class == "C"
- This rule OVERRIDES STUDENT logic
- Only downgrade to Economy if NO business seats exist


If student > 0 AND original_flight.cabin_class == "Economy":
- MUST NOT select travel_class == "C"
- MUST select economy class only
- FAIL if only business seats are selected

If original_flight.cabin_class == "Economy":
- Proceed with CDP rules as defined



--------------------------------
CDP PRIORITY ORDER (MANDATORY)
--------------------------------

Evaluate booking_details[0] first.

PRIORITY 1 (OVERRIDES EVERYTHING):
- If STUDENT > 0:
  - ALWAYS choose the CHEAPEST min_economy_fare flight
  - NEVER choose business class
  - Seat priority: cheapest economy seat, ignore comfort
  - Comfort signals (LEGROOM, XL, AISLE) are SECONDARY

- If HIGHSPENDERHIGHFREQ == true OR HIGHSPENDERLOWFREQ == true:
  - Price is IRRELEVANT
  - Prefer comfort, stretch, business class
  - Prefer earlier arrival and non-stop

--------------------------------
PRIORITY 2 (ONLY IF NOT STUDENT / HIGHSPENDER)
--------------------------------

Journey Intent:
- BUSINESS > LEISURE → time + comfort
- LEISURE >= BUSINESS → cost + flexibility

--------------------------------
FLIGHT SCORING (STRICT)
--------------------------------

For EACH available flight:

Start score = 0

Base:
+40 if NonStop
+25 if utcArrival earlier than original flight
+20 if utcDeparture closest to original flight
-15 if fillingFast == true

STUDENT OVERRIDE:
- score = -min_economy_fare
- IGNORE all comfort bonuses

HIGHSPENDER OVERRIDE:
+40 if isStretch == true
+30 if min_business_fare exists

--------------------------------
SEAT SCORING (STRICT)
--------------------------------

For EACH seat on SELECTED flight:

Start score = 0

STUDENT OVERRIDE:
- Prefer travel_class == "Y"
- Ignore LEGROOM, XL, WINDOW, AISLE
- Pick seat with highest availability or lowest cost proxy

HIGHSPENDER OVERRIDE:
+40 if travel_class == "C"
+25 if LEGROOM
+20 if XL
+15 if AISLE or WINDOW

--------------------------------
OUTPUT (STRICT JSON ONLY)
--------------------------------

{{
  "cdp_summary": {{
    "student": number,
    "highspender": boolean,
    "business": number,
    "leisure": number
  }},
  "selected_flight": {{ ... }},
  "selected_seat": {{ ... }},
  "reasoning": {{
    "flight_reason": "Explicitly reference STUDENT or HIGHSPENDER rule",
    "seat_reason": "Explicitly reference STUDENT or HIGHSPENDER rule"
  }}
}}

FAIL IF:
- Cheapest flight is NOT selected for STUDENT
- Business class is selected for STUDENT
- Any invented ID appears

"""
        )

        run = client.agents.runs.create(
            thread_id=thread.id,
            agent_id=AGENT_ID
        )

        while True:
            run = client.agents.runs.get(thread.id, run.id)
            if run.status == "completed":
                break

        messages = client.agents.messages.list(
            thread_id=thread.id,
            order=ListSortOrder.ASCENDING
        )

        print("\n🎯 FINAL AGENT OUTPUT:")
        for msg in reversed(list(messages)):
            if msg.role == "assistant":
                print(msg.text_messages[0].text.value)
                break

# ==============================
# ENTRY
# ==============================

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python testing.py <PNR> <LAST_NAME>")
        sys.exit(1)

    run_agent(sys.argv[1], sys.argv[2])
