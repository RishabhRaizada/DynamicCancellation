from fastapi import FastAPI
from pydantic import BaseModel
import json
import requests
from time import sleep
from azure.ai.agents.models import RunStatus
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ENDPOINT = "https://testapiagent-resource.services.ai.azure.com/api/projects/testapiagent"
AGENT_ID = "asst_N9B4EZEPs17A4NxhjD5fVgeX"
MCP_URL = "http://127.0.0.1:8003/mcp"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class DashboardQuery(BaseModel):
    question: str


# @app.post("/dashboard/query")
# def dashboard_query(payload: DashboardQuery):
#     # 1️⃣ Call Agent
#     client = AIProjectClient(
#         endpoint=PROJECT_ENDPOINT,
#         credential=DefaultAzureCredential()
#     )

#     with client:
#         thread = client.agents.threads.create()

#         client.agents.messages.create(
#             thread_id=thread.id,
#             role="user",
#             content=payload.question
#         )

#         client.agents.runs.create_and_process(
#             thread_id=thread.id,
#             agent_id=AGENT_ID
#         )

#         messages = client.agents.messages.list(
#             thread_id=thread.id,
#             order=ListSortOrder.ASCENDING
#         )

#         params = None
#         for m in reversed(list(messages)):
#             if m.role == "assistant" and m.text_messages:
#                 params = json.loads(m.text_messages[0].text.value)
#                 break

#     if not params:
#         return {"error": "No agent response"}

#     # 2️⃣ Call MCP
#     mcp_payload = {
#         "jsonrpc": "2.0",
#         "method": "tools/call",
#         "params": {
#             "name": "employee_kpi",
#             "arguments": params
#         },
#         "id": 1
#     }

#     response = requests.post(
#         MCP_URL,
#         json=mcp_payload,
#         headers={
#             "Accept": "application/json, text/event-stream",
#             "Content-Type": "application/json"
#         },
#         timeout=30
#     )

#     for line in response.text.splitlines():
#         if line.startswith("data:"):
#             data = json.loads(line.replace("data:", "").strip())
#             result = data.get("result", {})
#             structured = result.get("structuredContent", {})
#             content = structured.get("content", [])
#             if content and content[0]["type"] == "json":
#                 return content[0]["json"]

#     return {"error": "No MCP response"}
@app.post("/dashboard/query")
def dashboard_query(payload: DashboardQuery):

    client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential()
    )

    with client:
        # Create thread
        thread = client.agents.threads.create()

        # Add user message
        client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=payload.question
        )

        # Create run (non-blocking)
        run = client.agents.runs.create(
            thread_id=thread.id,
            agent_id=AGENT_ID
        )

        # Poll until run completes
        while run.status in ["queued", "in_progress"]:
            sleep(1)
            run = client.agents.runs.get(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status != RunStatus.COMPLETED:
            return {"error": f"Agent failed with status {run.status}"}

        # Fetch messages
        messages = client.agents.messages.list(
            thread_id=thread.id,
            order=ListSortOrder.ASCENDING
        )

        params = None

        for m in reversed(list(messages)):
            if m.role != "assistant":
                continue

            for tm in m.text_messages or []:
                raw = tm.text.value.strip()
                if not raw:
                    continue

                try:
                    parsed = json.loads(raw)
                    params = parsed
                    break
                except json.JSONDecodeError:
                    continue

            if params:
                break

    if not params or "tool" not in params or "arguments" not in params:
        return {"error": "Agent did not return valid tool JSON"}

    if not params:
        return {"error": "No agent response"}
    tool_name = params.get("tool")
    arguments = params.get("arguments")

    mcp_payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }

    response = requests.post(
        MCP_URL,
        json=mcp_payload,
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        },
        timeout=60
    )

    for line in response.text.splitlines():
        if line.startswith("data:"):
            data = json.loads(line.replace("data:", "").strip())
            result = data.get("result", {})
            structured = result.get("structuredContent", {})
            content = structured.get("content", [])
            if content and content[0]["type"] == "json":
                return content[0]["json"]

    return {"error": "No MCP response"}