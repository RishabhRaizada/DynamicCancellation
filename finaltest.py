import sys
import json
import requests
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import time

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

        # 🔄 Fallback: content[].text contains JSON string
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

    # ❌ If we reach here, parsing failed
    raise RuntimeError("No MCP JSON response found in SSE stream")

# ==============================
# AGENT RUNNER
# ==============================
# ==============================
# 4️⃣ AGENT INVOCATION (SUCCESS ONLY)
# ==============================
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
        return

    # ==============================
    # 3️⃣ SAFETY CHECK (DEFENSIVE)
    # ==============================
    recovery = mcp_data.get("recovery", {})
    if not recovery.get("available_flights") or not recovery.get("available_seats"):
        print("\n⛔ INCOMPLETE RECOVERY CONTEXT")
        print("Flights or seats missing — agent invocation blocked.")
        return

    # ==============================
    # 4️⃣ AGENT INVOCATION WITH EMBEDDED DATA
    # ==============================
    client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential()
    )

    with client:
        thread = client.agents.threads.create()

        # ✅ CRITICAL: Embed the actual MCP data into the prompt
        agent_prompt = f"""
You are a CLOSED-WORLD Flight & Seat Decision Engine.

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

--------------------------------
ABSOLUTE CONSTRAINTS (NON-NEGOTIABLE)
--------------------------------

1. You are operating in a CLOSED DATA WORLD - ONLY use data from above.
2. You MUST ONLY select flights from the "Available Flights" list above.
3. You MUST ONLY select seats from the "Available Seats" list above.
4. The above data is the COMPLETE universe - DO NOT invent or assume anything else.
5. If a value is not in the lists above, it DOES NOT EXIST.

--------------------------------
SEAT SELECTION SCOPE
--------------------------------

Seats are GLOBAL across all flights. Choose any seat from available_seats list.

--------------------------------
PRIORITY RULES (APPLY TO booking_details[0] ONLY)
--------------------------------

PRIORITY 1 — STUDENT (OVERRIDES ALL)
- If STUDENT > 0:
  - Choose flight with LOWEST `min_economy_fare`
  - NEVER choose business class
  - Seat: economy only

PRIORITY 2 — HIGH SPENDER
- If HIGHSPENDERHIGHFREQ or HIGHSPENDERLOWFREQ is true:
  - Prefer comfort over price
  - Prefer stretch / business seats
  - Prefer earlier arrival

PRIORITY 3 — GENERAL
- NonStop preferred
- Earlier arrival preferred
- Lower fare preferred
- fillingFast is negative

--------------------------------
SINGLE FLIGHT RULE
--------------------------------

If only 1 flight available (as shown above):
- You MUST select that exact flight
- DO NOT compare or invent alternatives

--------------------------------
SEAT FALLBACK RULE
--------------------------------

If seat price is NOT provided:
- Treat ALL economy seats as equal cost
- Select the FIRST economy seat in available_seats

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------

Return ONLY valid JSON.

If selection succeeds:

{{
  "selected_flight": {{ EXACT COPY FROM AVAILABLE_FLIGHTS LIST }},
  "selected_seat": {{ EXACT COPY FROM AVAILABLE_SEATS LIST }},
  "reasoning": {{
    "flight_reason": "Reason based ONLY on provided CDP + rules",
    "seat_reason": "Reason based ONLY on provided CDP + rules"
  }}
}}

If ANY rule violated or data missing:
Return EXACTLY:
{{}}
"""

        client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=agent_prompt
        )

        run = client.agents.runs.create(
            thread_id=thread.id,
            agent_id=AGENT_ID
        )

        while True:
            run = client.agents.runs.get(thread.id, run.id)
            if run.status == "completed":
                break
            time.sleep(0.5)  # Add small delay to avoid busy waiting

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