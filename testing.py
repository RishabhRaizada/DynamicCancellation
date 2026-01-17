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

def run_agent(pnr: str, last_name: str):
    print("\n🚀 Running manual MCP + Agent reasoning")
    print(f"PNR: {pnr}, LAST NAME: {last_name}")

    mcp_data = execute_mcp_tool(
        "recover_passenger",
        {"pnr": pnr, "last_name": last_name}
    )

    print("\n📦 MCP RESPONSE:")
    print(json.dumps(mcp_data, indent=2))

    if mcp_data.get("status") != "success":
        print("❌ MCP returned non-success")
        return

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
Here is the passenger recovery context (JSON):

{json.dumps(mcp_data, indent=2)}

Select the best seat and return final JSON only.
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

# import sys
# import time
# import json
# from azure.ai.projects import AIProjectClient
# from azure.identity import DefaultAzureCredential
# from azure.ai.agents.models import ListSortOrder, RunStatus

# # ==============================
# # CONFIG
# # ==============================

# PROJECT_ENDPOINT = "https://testapiagent-resource.services.ai.azure.com/api/projects/testapiagent"
# AGENT_ID = "asst_fVKKUVovJ6FGONPYJOV3pe21"

# # ==============================
# # AGENT RUNNER
# # ==============================

# def run_agent(pnr: str, last_name: str):
#     print("\n" + "=" * 70)
#     print("🚀 FLIGHT RECOVERY AGENT TEST")
#     print("=" * 70)
#     print(f"PNR       : {pnr}")
#     print(f"LAST NAME : {last_name}")
#     print("=" * 70)

#     client = AIProjectClient(
#         endpoint=PROJECT_ENDPOINT,
#         credential=DefaultAzureCredential()
#     )

#     with client:
#         # 1️⃣ Create thread
#         thread = client.agents.threads.create()
#         print("✅ Thread created")

#         # 2️⃣ Send user message
#         client.agents.messages.create(
#             thread_id=thread.id,
#             role="user",
#             content=f"Recover passenger with PNR {pnr} and last name {last_name}."
#         )
#         print("📨 User message sent")

#         # 3️⃣ Start run
#         run = client.agents.runs.create(
#             thread_id=thread.id,
#             agent_id=AGENT_ID
#         )
#         print(f"⚡ Run started: {run.id}")

#         # 4️⃣ Poll until completion
#         while True:
#             time.sleep(1)
#             run = client.agents.runs.get(thread.id, run.id)

#             if run.status == RunStatus.REQUIRES_ACTION:
#                 # MCP tool calls are handled automatically by Foundry
#                 print("🛠️ Agent calling MCP (auto-handled)")
#                 continue

#             if run.status == RunStatus.COMPLETED:
#                 print("🎉 Agent completed")
#                 break

#             if run.status in (
#                 RunStatus.FAILED,
#                 RunStatus.CANCELLED,
#                 RunStatus.EXPIRED
#             ):
#                 print(f"❌ Run failed: {run.status}")
#                 return

#         # 5️⃣ Fetch final agent response
#         messages = client.agents.messages.list(
#             thread_id=thread.id,
#             order=ListSortOrder.ASCENDING
#         )

#         print("\n" + "=" * 70)
#         print("🎯 FINAL AGENT RESPONSE")
#         print("=" * 70)

#         for msg in reversed(list(messages)):
#             if msg.role == "assistant" and msg.text_messages:
#                 content = msg.text_messages[0].text.value
#                 print(content)
#                 try:
#                     print("\n✅ Parsed JSON:")
#                     print(json.dumps(json.loads(content), indent=2))
#                 except Exception:
#                     pass
#                 return

#         print("❌ No assistant response found")

# # ==============================
# # ENTRY POINT
# # ==============================

# if __name__ == "__main__":
#     if len(sys.argv) != 3:
#         print("Usage: python testing.py <PNR> <LAST_NAME>")
#         sys.exit(1)

#     run_agent(sys.argv[1], sys.argv[2])
