# autorecovery_testing.py

import time
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json as json_module

# Azure imports
try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    from azure.ai.agents.models import ListSortOrder, ToolOutput
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("⚠️ Azure libraries not available. Running in local mode only.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("autorecovery-test")

# ==============================
# CONFIGURATION
# ==============================

# MCP Server Configuration
AUTORECOVERY_MCP_URL = "http://127.0.0.1:8003/mcp"

# Azure AI Agent Configuration (if using)
PROJECT_ENDPOINT = "https://testapiagent-resource.services.ai.azure.com/api/projects/testapiagent"
AGENT_ID = "asst_fVKKUVovJ6FGONPYJOV3pe21"

# Test Configuration
TEST_CANCELLATION_FILE = "cancellation_trigger.json"
TOOL_APPROVAL_PORT = 8004

# Test Data
TEST_CASES = [
    {
        "last_name": "Mehta",
        "email_or_phone": "karan.mehta1@mail.com",
        "pnr": "PNR001",
        "description": "High spender user with cancelled Business class flight"
    },
    {
        "last_name": "Patel", 
        "email_or_phone": "rita.patel13@test.com",
        "pnr": "PNR003",
        "description": "Business class passenger"
    },
    {
        "last_name": "Yadav",
        "email_or_phone": "suresh.yadav2@test.com",
        "pnr": "PNR002",
        "description": "Economy class passenger"
    }
]

# ==============================
# TOOL APPROVAL SERVER
# ==============================

class ToolApprovalHandler(BaseHTTPRequestHandler):
    """HTTP handler to automatically approve tool calls from Azure AI Agents"""
    
    def do_POST(self):
        """Handle tool approval requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = json_module.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON: {e}")
            self.send_error(400, "Invalid JSON")
            return
        
        # Log the request
        method = request_data.get("method", "unknown")
        logger.info(f"📋 Tool call request received: {method}")
        
        # Extract tool details
        tool_name = method.split("/")[-1] if "/" in method else method
        params = request_data.get("params", {})
        
        # Log detailed information
        logger.info(f"🛠️  Tool: {tool_name}")
        if "arguments" in params:
            logger.info(f"📝 Arguments: {json_module.dumps(params['arguments'], indent=2)}")
        
        # Always approve the request
        response = {
            "jsonrpc": "2.0",
            "id": request_data.get("id", 1),
            "result": {
                "status": "approved",
                "message": f"Automatically approved {tool_name}",
                "result": {
                    "content": [{
                        "type": "text",
                        "text": f"Tool {tool_name} approved automatically for testing"
                    }]
                }
            }
        }
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json_module.dumps(response).encode('utf-8'))
        
        logger.info(f"✅ Automatically approved: {tool_name}")

def start_tool_approval_server(port=TOOL_APPROVAL_PORT):
    """Start the tool approval server in a separate thread"""
    def run_server():
        server = HTTPServer(('localhost', port), ToolApprovalHandler)
        logger.info(f"✅ Tool approval server started on http://localhost:{port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

# ==============================
# MCP TOOL EXECUTOR
# ==============================

def execute_mcp_tool(tool_name: str, arguments: dict) -> Dict[str, Any]:
    """Execute MCP tool using correct protocol"""
    
    logger.info(f"🔮 Executing {tool_name} via MCP")
    logger.info(f"📝 Arguments: {json.dumps(arguments, indent=2)}")
    
    # Use MCP protocol
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
        "Accept": "application/json, text/event-stream, */*",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            AUTORECOVERY_MCP_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📡 MCP Response Status: {response.status_code}")
        
        if response.status_code != 200:
            error_msg = f"MCP call failed: {response.status_code} {response.text[:200]}"
            logger.error(f"❌ {error_msg}")
            return {"error": error_msg}
        
        # Parse the response (MCP stream format)
        lines = response.text.splitlines()
        for line in lines:
            if line.startswith("data:"):
                data_line = line.replace("data:", "", 1).strip()
                try:
                    mcp_payload = json.loads(data_line)
                    
                    if "result" in mcp_payload:
                        result = mcp_payload["result"]
                        
                        # Extract structured content
                        if "structuredContent" in result and "content" in result["structuredContent"]:
                            content = result["structuredContent"]["content"]
                            if content and len(content) > 0:
                                tool_data = content[0].get("json", {})
                                logger.info("✅ Tool executed successfully")
                                return tool_data
                        elif "content" in result:
                            # Alternative format
                            for item in result["content"]:
                                if item.get("type") == "json":
                                    tool_data = item.get("json", {})
                                    logger.info("✅ Tool executed successfully")
                                    return tool_data
                        
                        # Return whatever result we have
                        return result
                    
                    return mcp_payload
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse JSON: {e}")
                    return {"error": f"Failed to parse JSON: {str(e)}"}
        
        return {"error": "No valid response received"}
            
    except Exception as e:
        error_msg = f"MCP call exception: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"error": error_msg}

# ==============================
# DIRECT TOOL TESTING
# ==============================

def test_mcp_server_connection():
    """Test if MCP server is running and get available tools"""
    logger.info("=" * 60)
    logger.info("🔍 Testing MCP Server Connection")
    logger.info("=" * 60)
    
    try:
        response = requests.post(AUTORECOVERY_MCP_URL, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "list_tools"
        }, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                tools = data["result"].get("tools", [])
                logger.info("✅ MCP Server is running")
                logger.info(f"📋 Available tools:")
                for tool in tools:
                    logger.info(f"  • {tool.get('name')}: {tool.get('description', 'No description')[:80]}...")
                return True
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ MCP Server is not running")
        logger.error("Please start the autorecovery MCP server first:")
        logger.error("  python autorecovery_mcp.py")
        return False

def run_direct_tool_test():
    """Run direct tool tests without Azure agent"""
    logger.info("=" * 60)
    logger.info("🧪 Running Direct Tool Tests")
    logger.info("=" * 60)
    
    # Test case
    test_case = TEST_CASES[0]
    
    # Test 1: Get User Profile
    logger.info("\n1. Testing get_user_profile...")
    result = execute_mcp_tool("get_user_profile", {
        "last_name": test_case["last_name"],
        "email_or_phone": test_case["email_or_phone"]
    })
    
    if "error" not in result:
        logger.info("✅ get_user_profile test passed")
        if "data" in result:
            user_data = result["data"]
            if isinstance(user_data, list) and len(user_data) > 0:
                user = user_data[0].get("user_info", {})
                logger.info(f"   Found user: {user.get('USR_FIRSTNAME')} {user.get('USR_LASTNAME')}")
    else:
        logger.error(f"❌ get_user_profile test failed: {result.get('error')}")
    
    # Test 2: Check Eligibility
    logger.info("\n2. Testing check_autorecovery_eligibility...")
    result = execute_mcp_tool("check_autorecovery_eligibility", {
        "last_name": test_case["last_name"],
        "email_or_phone": test_case["email_or_phone"]
    })
    
    if "error" not in result:
        logger.info("✅ check_autorecovery_eligibility test passed")
        logger.info(f"   Result: {json.dumps(result, indent=2)}")
    else:
        logger.error(f"❌ check_autorecovery_eligibility test failed: {result.get('error')}")
    
    # Test 3: Get Available Seats
    logger.info("\n3. Testing get_available_seats...")
    result = execute_mcp_tool("get_available_seats", {})
    
    if "error" not in result:
        logger.info("✅ get_available_seats test passed")
        logger.info(f"   Total available seats: {result.get('total_available_seats', 0)}")
        logger.info(f"   Total flights: {result.get('total_flights', 0)}")
    else:
        logger.error(f"❌ get_available_seats test failed: {result.get('error')}")
    
    # Test 4: Get All Data (Integration Test)
    logger.info("\n4. Testing get_all_data_for_autorecovery...")
    result = execute_mcp_tool("get_all_data_for_autorecovery", {
        "last_name": test_case["last_name"],
        "email_or_phone": test_case["email_or_phone"],
        "pnr_number": test_case["pnr"]
    })
    
    if "error" not in result:
        logger.info("✅ get_all_data_for_autorecovery test passed")
        
        # Print summary
        if "analysis_summary" in result:
            summary = result["analysis_summary"]
            logger.info(f"\n📊 Analysis Summary:")
            logger.info(f"   Cancelled route: {summary.get('cancelled_route')}")
            logger.info(f"   User eligible: {summary.get('user_eligible')}")
            logger.info(f"   Alternative flights found: {summary.get('alternative_flights_found')}")
        
        # Show alternative flights
        if "alternative_flights" in result:
            alternatives = result["alternative_flights"]
            flights = alternatives.get("matching_flights", [])
            if flights:
                logger.info(f"\n🛫 Alternative Flights ({len(flights)} found):")
                for i, flight in enumerate(flights[:3], 1):
                    logger.info(f"   {i}. {flight.get('flight_number')}: {flight.get('total_available_seats')} seats")
    else:
        logger.error(f"❌ get_all_data_for_autorecovery test failed: {result.get('error')}")
    
    return True

# ==============================
# AZURE AI AGENT INTEGRATION
# ==============================

def run_agent_query(user_query: str, use_tool_approval: bool = True) -> Optional[Dict[str, Any]]:
    """Run a query through Azure AI Agent"""
    
    if not AZURE_AVAILABLE:
        logger.error("❌ Azure libraries not available. Cannot run agent query.")
        return None
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🔍 Processing via Azure AI Agent: {user_query}")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential()
        )
        
        with client:
            # 1. Create thread
            thread = client.agents.threads.create()
            logger.info("✅ Thread created")
            
            # 2. Send user query
            client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_query
            )
            logger.info("📨 User query sent")
            
            # 3. Start agent run
            run = client.agents.runs.create(
                thread_id=thread.id,
                agent_id=AGENT_ID
            )
            logger.info(f"⚡ Agent run started | Run ID: {run.id}")
            
            # 4. Wait for agent to complete
            while run.status in ["queued", "in_progress"]:
                time.sleep(1)
                run = client.agents.runs.get(thread.id, run.id)
            
            logger.info(f"📊 Agent completed with status: {run.status}")
            
            # 5. Get agent's messages
            messages = client.agents.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING
            )
            
            # Find assistant message with tool calls
            planning_json = None
            for msg in reversed(list(messages)):
                if msg.role == "assistant" and msg.text_messages:
                    for text_msg in msg.text_messages:
                        content = text_msg.text.value.strip()
                        if content:
                            # Try to find JSON with tool calls
                            try:
                                data = json.loads(content)
                                if "tool_calls" in data or "intent" in data:
                                    planning_json = data
                                    logger.info("✅ Found planning JSON from agent")
                                    break
                            except:
                                # Check if it contains autorecovery keywords
                                if any(keyword in content.lower() for keyword in 
                                      ["autorecovery", "cancelled", "flight", "seat", "reallocate"]):
                                    planning_json = {"text": content}
                                    break
                    if planning_json:
                        break
            
            if not planning_json:
                logger.info("ℹ️ No structured planning found, returning text response")
                # Return the last assistant message
                for msg in reversed(list(messages)):
                    if msg.role == "assistant" and msg.text_messages:
                        for text_msg in msg.text_messages:
                            return {
                                "query": user_query,
                                "response": text_msg.text.value,
                                "execution_time": time.time() - start_time
                            }
                return None
            
            logger.info("\n" + "=" * 40)
            logger.info("📋 AGENT PLANNING OUTPUT")
            logger.info("=" * 40)
            logger.info(json.dumps(planning_json, indent=2))
            
            # 6. Execute MCP tools based on agent's plan
            tool_results = []
            
            if "tool_calls" in planning_json:
                tool_calls = planning_json["tool_calls"]
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    arguments = tool_call.get("arguments", {})
                    
                    logger.info(f"\n🛠️ Executing tool: {tool_name}")
                    logger.info(f"📝 Arguments: {json.dumps(arguments, indent=2)}")
                    
                    # Execute MCP tool
                    tool_result = execute_mcp_tool(tool_name, arguments)
                    tool_results.append({
                        "tool": tool_name,
                        "result": tool_result
                    })
                    
                    # Send result back to agent if needed
                    if "error" not in tool_result:
                        # Create ToolOutput for Azure agent
                        tool_output = ToolOutput(
                            tool_call_id=tool_call.get("id", "unknown"),
                            output=json.dumps(tool_result)
                        )
                        
                        # Submit tool output to agent
                        client.agents.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=[tool_output]
                        )
                        
                        logger.info("✅ Tool result submitted to agent")
            
            # 7. Get final answer from agent
            logger.info("\n⏳ Waiting for agent's final response...")
            
            # Wait for agent to process tool outputs
            time.sleep(2)
            
            # Get updated messages
            final_messages = client.agents.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING
            )
            
            logger.info("\n" + "=" * 60)
            logger.info("🎯 FINAL AGENT RESPONSE")
            logger.info("=" * 60)
            
            final_answer = None
            for msg in reversed(list(final_messages)):
                if msg.role == "assistant" and msg.text_messages:
                    for text_msg in msg.text_messages:
                        content = text_msg.text.value.strip()
                        if content:
                            logger.info(content)
                            final_answer = content
                    break
            
            return {
                "query": user_query,
                "planning": planning_json,
                "tool_results": tool_results,
                "final_answer": final_answer,
                "execution_time": time.time() - start_time
            }
            
    except Exception as e:
        logger.error(f"❌ Agent query failed: {str(e)}")
        return {"error": str(e)}

# ==============================
# TEST SCENARIOS
# ==============================

def run_test_scenarios():
    """Run predefined test scenarios"""
    logger.info("=" * 60)
    logger.info("🚀 Running Test Scenarios")
    logger.info("=" * 60)
    
    scenarios = [
        {
            "name": "Basic Eligibility Check",
            "query": "Check if Karan Mehta with email karan.mehta1@mail.com is eligible for autorecovery"
        },
        {
            "name": "Flight Cancellation Case",
            "query": "Flight PNR001 for Karan Mehta (karan.mehta1@mail.com) has been cancelled. Find autorecovery options."
        },
        {
            "name": "Complete Autorecovery",
            "query": "Process autorecovery for Rita Patel (rita.patel13@test.com) whose flight PNR003 was cancelled. She was in Business class."
        },
        {
            "name": "Alternative Flight Search",
            "query": "Find alternative flights from DEL to BOM with Business class seats available."
        }
    ]
    
    results = []
    
    for scenario in scenarios:
        logger.info(f"\n{'='*40}")
        logger.info(f"SCENARIO: {scenario['name']}")
        logger.info(f"{'='*40}")
        logger.info(f"Query: {scenario['query']}")
        
        if AZURE_AVAILABLE:
            result = run_agent_query(scenario["query"])
        else:
            # Direct tool execution
            if "eligibility" in scenario["query"].lower():
                tool_name = "check_autorecovery_eligibility"
                args = {"last_name": "Mehta", "email_or_phone": "karan.mehta1@mail.com"}
            elif "alternative" in scenario["query"].lower():
                tool_name = "search_available_flights"
                args = {"origin": "DEL", "destination": "BOM", "cabin_class": "C"}
            else:
                tool_name = "get_all_data_for_autorecovery"
                args = {
                    "last_name": "Mehta",
                    "email_or_phone": "karan.mehta1@mail.com",
                    "pnr_number": "PNR001"
                }
            
            result = execute_mcp_tool(tool_name, args)
        
        results.append({
            "scenario": scenario["name"],
            "success": "error" not in result if result else False,
            "result": result
        })
        
        # Brief pause between scenarios
        time.sleep(1)
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SCENARIOS SUMMARY")
    logger.info("=" * 60)
    
    successful = sum(1 for r in results if r["success"])
    logger.info(f"✅ Successful: {successful}/{len(results)}")
    logger.info(f"❌ Failed: {len(results) - successful}/{len(results)}")
    
    for i, r in enumerate(results, 1):
        status = "✅" if r["success"] else "❌"
        logger.info(f"{i}. {status} {r['scenario']}")

# ==============================
# INTERACTIVE MODE
# ==============================

def interactive_mode():
    """Interactive testing mode"""
    logger.info("=" * 60)
    logger.info("🤖 AUTORECOVERY TESTING - INTERACTIVE MODE")
    logger.info("=" * 60)
    
    logger.info("\n📋 Available Commands:")
    logger.info("  • test tools    - Run direct tool tests")
    logger.info("  • scenarios     - Run test scenarios")
    logger.info("  • agent <query> - Send query to Azure agent")
    logger.info("  • tool <name> <args> - Execute specific tool")
    logger.info("  • quit          - Exit")
    
    # Start tool approval server
    logger.info("\n🚀 Starting tool approval server...")
    approval_thread = start_tool_approval_server()
    time.sleep(1)
    
    while True:
        print("\n" + "-" * 60)
        command = input("👉 Enter command: ").strip()
        
        if command.lower() in ['quit', 'exit', 'q']:
            logger.info("👋 Exiting. Goodbye!")
            break
        
        if not command:
            continue
        
        if command == "test tools":
            run_direct_tool_test()
        
        elif command == "scenarios":
            run_test_scenarios()
        
        elif command.startswith("agent "):
            query = command[6:]  # Remove "agent "
            if AZURE_AVAILABLE:
                result = run_agent_query(query)
                if result and "final_answer" in result:
                    logger.info("\n🎯 Final Answer:")
                    logger.info(result["final_answer"])
            else:
                logger.error("❌ Azure AI Agent not available")
        
        elif command.startswith("tool "):
            parts = command[5:].split(" ", 1)
            if len(parts) >= 1:
                tool_name = parts[0]
                args_str = parts[1] if len(parts) > 1 else "{}"
                
                try:
                    if args_str:
                        args = json.loads(args_str)
                    else:
                        args = {}
                    
                    result = execute_mcp_tool(tool_name, args)
                    logger.info("\n📊 Tool Result:")
                    logger.info(json.dumps(result, indent=2))
                except json.JSONDecodeError:
                    logger.error("❌ Invalid JSON arguments")
                except Exception as e:
                    logger.error(f"❌ Tool execution failed: {str(e)}")
        
        else:
            logger.error("❌ Unknown command")
            logger.info("Available commands: test tools, scenarios, agent <query>, tool <name> <args>, quit")

# ==============================
# QUICK START FUNCTION
# ==============================

def quick_start():
    """Quick start with basic tests"""
    logger.info("=" * 60)
    logger.info("🚀 AUTORECOVERY SYSTEM QUICK START")
    logger.info("=" * 60)
    
    # Check MCP server
    logger.info("\n🔍 Checking MCP server...")
    if not test_mcp_server_connection():
        logger.error("\n❌ Please start the MCP server first:")
        logger.error("  python autorecovery_mcp.py")
        return
    
    # Start tool approval server
    logger.info("\n🚀 Starting tool approval server...")
    start_tool_approval_server()
    time.sleep(2)
    
    # Run basic tests
    logger.info("\n🧪 Running basic tests...")
    run_direct_tool_test()
    
    # Offer interactive mode
    logger.info("\n" + "=" * 60)
    logger.info("📝 Ready for interactive testing")
    logger.info("=" * 60)
    
    choice = input("\n👉 Enter interactive mode? (y/n): ").strip().lower()
    if choice == 'y':
        interactive_mode()

# ==============================
# MAIN FUNCTION
# ==============================

def main():
    """Main entry point"""
    print("=" * 60)
    print("🤖 AUTORECOVERY SYSTEM TESTING SUITE")
    print("=" * 60)
    
    print("\n📋 SELECT MODE:")
    print("1. Quick Start (Recommended)")
    print("2. Interactive Testing Mode")
    print("3. Direct Tool Tests Only")
    print("4. Test Scenarios")
    print("5. Exit")
    
    while True:
        choice = input("\n👉 Select mode (1-5): ").strip()
        
        if choice == "1":
            quick_start()
            break
        elif choice == "2":
            interactive_mode()
            break
        elif choice == "3":
            if test_mcp_server_connection():
                run_direct_tool_test()
            break
        elif choice == "4":
            run_test_scenarios()
            break
        elif choice == "5":
            print("\n👋 Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")