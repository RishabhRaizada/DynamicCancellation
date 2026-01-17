
import sys
import time
import json
import traceback
from typing import Dict, Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder, RunStatus

PROJECT_ENDPOINT = "https://testapiagent-resource.services.ai.azure.com/api/projects/testapiagent"
AGENT_ID = "asst_fVKKUVovJ6FGONPYJOV3pe21"

def execute_real_mcp_tool(pnr: str, last_name: str) -> str:
    """
    Execute the actual MCP tool logic (based on your server.py)
    Now compatible with the actual JSON structure
    """
    try:
        # Load data (same as your server.py)
        with open("data/cancell_trigger.json", "r", encoding="utf-8") as f:
            CANCELLATIONS = json.load(f)
        
        with open("data/available_seats.json", "r", encoding="utf-8") as f:
            AVAILABLE_SEATS_DATA = json.load(f)
        
        # Find cancellation
        event = next((c for c in CANCELLATIONS if c.get("pnr") == pnr), None)
        
        if not event:
            return json.dumps({"error": "PNR_NOT_FOUND"})
        
        # Get user info
        user_info = event.get("user_info", {})
        
        # Extract flight info from available_seats.json
        # Your JSON structure is different than expected
        flight_info = None
        seat_map = None
        
        try:
            # Navigate through your actual JSON structure
            seat_maps = AVAILABLE_SEATS_DATA.get('data', {}).get('seatMaps', [])
            if seat_maps:
                seat_map = seat_maps[0].get('seatMap', {})
                
                # Extract flight information
                flight_info = {
                    "aircraft_type": seat_map.get('name'),
                    "origin": seat_map.get('departureStation'),
                    "destination": seat_map.get('arrivalStation'),
                    "equipment": f"{seat_map.get('equipmentType', '')}/{seat_map.get('equipmentTypeSuffix', '')}",
                    "available_seats": seat_map.get('availableUnits', 0)
                }
                
                # Extract seat information
                seats = []
                decks = seat_map.get('decks', {})
                
                for deck_key, deck_data in decks.items():
                    compartments = deck_data.get('compartments', {})
                    
                    for comp_key, comp_data in compartments.items():
                        units = comp_data.get('units', [])
                        
                        for seat in units:
                            seat_info = {
                                "seat_number": seat.get('designator'),
                                "available": seat.get('availability', 0) > 0,
                                "availability_count": seat.get('availability', 0),
                                "class": seat.get('travelClassCode'),
                                "properties": [prop.get('code') for prop in seat.get('properties', [])]
                            }
                            seats.append(seat_info)
        except Exception as e:
            print(f"Warning: Could not parse available seats data: {e}")
        
        # Create response
        response = {
            "status": "SUCCESS",
            "recovery_id": f"REC-{pnr}-{int(time.time())}",
            "passenger": {
                "pnr": pnr,
                "last_name": last_name,
                "first_name": user_info.get("USR_FIRSTNAME", ""),
                "email": user_info.get("USR_EMAIL", ""),
                "phone": str(user_info.get("USR_MOBILE", ""))
            },
            "cancelled_flight": {
                "flight_number": event.get("flight_number"),
                "origin": event.get("origin"),
                "destination": event.get("destination"),
                "scheduled_departure": event.get("scheduled_departure"),
                "cabin_class": event.get("cabin_class")
            },
            "recovery_flight": flight_info,
            "available_seats": seat_map,  # Include full seat map if needed
            "assigned_seat": None,
            "seat_suggestions": [],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # Find available seats (simplified logic)
        available_seats = []
        if seats:
            for seat in seats:
                if seat.get('available') and seat.get('availability_count', 0) > 0:
                    available_seats.append(seat)
            
            if available_seats:
                response["assigned_seat"] = available_seats[0]
                response["seat_suggestions"] = available_seats[:5]  # Top 5 suggestions
        
        return json.dumps(response, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "ERROR",
            "message": f"Tool execution failed: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        return json.dumps(error_response, indent=2)
    
def submit_proper_tool_outputs(pnr: str, last_name: str):
    """
    PROPER solution: Submit tool outputs exactly as Azure expects
    """
    print("\n" + "=" * 70)
    print("🎯 PROPER TOOL OUTPUT SUBMISSION")
    print("=" * 70)
    
    try:
        client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential()
        )
        
        with client:
            # 1. Create thread
            thread = client.agents.threads.create()
            thread_id = thread.id
            print(f"✅ Thread: {thread_id}")
            
            # 2. Send user message (matches agent instructions)
            client.agents.messages.create(
                thread_id=thread_id,
                role="user",
                content=f"Call prepare_recovery_context with pnr={pnr}, last_name={last_name}"
            )
            print("📨 User message sent")
            
            # 3. Start run
            run = client.agents.runs.create(
                thread_id=thread_id,
                agent_id=AGENT_ID
            )
            run_id = run.id
            print(f"⚡ Run: {run_id}")
            
            # 4. Wait for requires_action
            for i in range(10):
                time.sleep(2)
                run = client.agents.runs.get(thread_id, run_id)
                
                if run.status == RunStatus.REQUIRES_ACTION:
                    print("\n🛠️ Agent requires tool approval")
                    
                    # EXTRACT TOOL CALL INFO FROM RUN DATA
                    run_data = run._data
                    required_action = run_data.get('required_action', {})
                    submit_tool_approval = required_action.get('submit_tool_approval', {})
                    tool_calls = submit_tool_approval.get('tool_calls', [])
                    
                    if tool_calls:
                        print(f"📋 Found {len(tool_calls)} tool call(s)")
                        
                        tool_outputs = []
                        for tool_call in tool_calls:
                            tool_call_id = tool_call.get('id', '')
                            tool_name = tool_call.get('name', '')
                            tool_args = tool_call.get('arguments', '{}')
                            
                            print(f"\n🔧 Tool call:")
                            print(f"   ID: {tool_call_id}")
                            print(f"   Name: {tool_name}")
                            print(f"   Args: {tool_args}")
                            
                            # Parse arguments
                            try:
                                args_dict = json.loads(tool_args)
                                call_pnr = args_dict.get('pnr', pnr)
                                call_last_name = args_dict.get('last_name', last_name)
                            except:
                                call_pnr = pnr
                                call_last_name = last_name
                            
                            # Execute MCP tool
                            if tool_name == "prepare_recovery_context":
                                print(f"   🚀 Executing MCP tool: {tool_name}")
                                mcp_result = execute_real_mcp_tool(call_pnr, call_last_name)
                                
                                # Format as agent expects: {"mcp_response": <raw JSON>}
                                tool_output = json.dumps({
                                    "mcp_response": json.loads(mcp_result)
                                })
                                
                                tool_outputs.append({
                                    "tool_call_id": tool_call_id,
                                    "output": tool_output
                                })
                                
                                print(f"   ✅ Tool output prepared")
                        
                        # SUBMIT TOOL OUTPUTS PROPERLY
                        if tool_outputs:
                            print(f"\n📤 Submitting {len(tool_outputs)} tool output(s)...")
                            
                            run = client.agents.runs.submit_tool_outputs(
                                thread_id=thread_id,
                                run_id=run_id,
                                tool_outputs=tool_outputs
                            )
                            
                            print("✅ Tool outputs submitted successfully!")
                            break
                    else:
                        print("⚠️ No tool calls found in required_action")
                        break
                
                elif run.status == RunStatus.COMPLETED:
                    print("\n🎉 Agent completed without requiring action")
                    break
            
            # 5. Wait for final completion
            print("\n⏳ Waiting for agent to process tool outputs...")
            for i in range(10):
                time.sleep(2)
                run = client.agents.runs.get(thread_id, run_id)
                
                if run.status == RunStatus.COMPLETED:
                    print(f"✅ Agent completed: {run.status}")
                    break
                elif run.status in [RunStatus.FAILED, RunStatus.CANCELLED]:
                    print(f"⚠️ Agent ended: {run.status}")
                    break
            
            # 6. Show final conversation
            print("\n" + "=" * 70)
            print("💬 FINAL CONVERSATION")
            print("=" * 70)
            
            messages = client.agents.messages.list(
                thread_id=thread_id,
                order=ListSortOrder.ASCENDING
            )
            
            for idx, msg in enumerate(list(messages)):
                print(f"\n{'━' * 40}")
                print(f"Message {idx + 1} - {msg.role.upper()}")
                print(f"{'━' * 40}")
                
                if msg.text_messages:
                    for text_msg in msg.text_messages:
                        content = text_msg.text.value
                        print(content)
                        
                        # Try to parse JSON
                        try:
                            parsed = json.loads(content)
                            print("\n✅ Contains valid JSON:")
                            print(json.dumps(parsed, indent=2))
                        except:
                            pass
                
                print(f"{'━' * 40}")
            
            print("\n" + "=" * 70)
            print("✅ PROCESS COMPLETED SUCCESSFULLY!")
            print(f"📊 Thread ID: {thread_id}")
            print(f"🆔 Run ID: {run_id}")
            print("=" * 70)
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        traceback.print_exc()

def simple_demo():
    """Simple demonstration of the complete flow"""
    print("\n" + "=" * 70)
    print("🎬 DEMO: Complete Azure Agent + MCP Integration")
    print("=" * 70)
    
    print("\n📋 This demonstrates:")
    print("1. Azure Agent calling MCP tool")
    print("2. Extracting tool call information")
    print("3. Executing real MCP logic")
    print("4. Submitting proper tool outputs")
    print("5. Agent returning formatted response")
    
    print("\n🔧 Agent Instructions:")
    print("The agent is configured to:")
    print("- Call prepare_recovery_context exactly once")
    print("- Return: {\"mcp_response\": <raw JSON>}")
    
    print("\n🚀 Starting demo with PNR001, Mehta...")
    time.sleep(2)
    
    submit_proper_tool_outputs("PNR001", "Mehta")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        simple_demo()
    elif len(sys.argv) == 3:
        submit_proper_tool_outputs(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python final_solution.py [PNR] [LAST_NAME]")
        print("\nExamples:")
        print("  python final_solution.py              (run demo)")
        print("  python final_solution.py PNR001 Mehta (custom test)")