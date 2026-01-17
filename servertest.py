# # autorecovery_simple_test.py

# import requests
# import json
# import time

# # Configuration
# MCP_URL = "http://127.0.0.1:8003/mcp"

# def test_mcp_connection():
#     """Test if MCP server is responding"""
#     print("=" * 60)
#     print("🔍 Testing MCP Server Connection")
#     print("=" * 60)
    
#     try:
#         # Try to list tools with CORRECT headers
#         response = requests.post(MCP_URL, json={
#             "jsonrpc": "2.0",
#             "id": 1,
#             "method": "list_tools"
#         }, headers={
#             "Content-Type": "application/json",
#             "Accept": "application/json, text/event-stream, */*"  # MUST include text/event-stream
#         }, timeout=5)
        
#         print(f"Status Code: {response.status_code}")
        
#         if response.status_code == 200:
#             print("✅ MCP Server is responding")
            
#             # Try to parse the response
#             try:
#                 data = response.json()
#                 print(f"✅ Response parsed as JSON")
#                 if "result" in data and "tools" in data["result"]:
#                     tools = data["result"]["tools"]
#                     print(f"\n📋 Available tools ({len(tools)}):")
#                     for tool in tools:
#                         print(f"  • {tool.get('name')}")
#                         desc = tool.get('description', 'No description')
#                         print(f"    {desc[:80]}...")
#                 return True
#             except json.JSONDecodeError:
#                 # Might be streaming response
#                 print("📦 Stream response received")
#                 lines = response.text.splitlines()
#                 for line in lines:
#                     if line.startswith("data:"):
#                         try:
#                             data = json.loads(line[5:])
#                             print(json.dumps(data, indent=2))
#                         except:
#                             print(f"Line: {line}")
#                 return True
#         else:
#             print(f"❌ Server returned {response.status_code}")
#             print(f"Response: {response.text[:200]}")
#             return False
            
#     except requests.exceptions.ConnectionError:
#         print("❌ Cannot connect to MCP server")
#         print("Make sure the server is running:")
#         print("  python autorecovery_mcp.py")
#         return False
#     except Exception as e:
#         print(f"❌ Error: {str(e)}")
#         return False

# def execute_tool_simple(tool_name: str, arguments: dict):
#     """Simple tool execution with correct MCP protocol"""
#     print(f"\n{'='*60}")
#     print(f"🔧 Executing: {tool_name}")
#     print(f"Arguments: {json.dumps(arguments, indent=2)}")
#     print(f"{'='*60}")
    
#     # Correct MCP protocol format
#     payload = {
#         "jsonrpc": "2.0",
#         "method": "tools/call",  # This is the MCP protocol method
#         "params": {
#             "name": tool_name,
#             "arguments": arguments
#         },
#         "id": 1
#     }
    
#     headers = {
#         "Content-Type": "application/json",
#         "Accept": "application/json, text/event-stream, */*"  # CRITICAL: Must include text/event-stream
#     }
    
#     try:
#         response = requests.post(
#             MCP_URL,
#             json=payload,
#             headers=headers,
#             timeout=30
#         )
        
#         print(f"📡 HTTP Status: {response.status_code}")
        
#         if response.status_code == 200:
#             # Handle streaming response (MCP uses Server-Sent Events)
#             print("\n📦 Parsing response...")
            
#             # Split into lines and look for data: lines
#             lines = response.text.strip().split('\n')
#             results = []
            
#             for line in lines:
#                 line = line.strip()
#                 if line.startswith('data:'):
#                     data_str = line[5:].strip()
#                     if data_str:
#                         try:
#                             data = json.loads(data_str)
#                             results.append(data)
#                         except json.JSONDecodeError as e:
#                             print(f"❌ JSON decode error: {e}")
#                             print(f"Raw line: {data_str[:100]}")
            
#             if results:
#                 print(f"\n✅ Received {len(results)} response(s):")
#                 for i, result in enumerate(results):
#                     print(f"\n📄 Response {i+1}:")
#                     print(json.dumps(result, indent=2))
#                 return results[-1] if results else None
#             else:
#                 # Try to parse as regular JSON
#                 try:
#                     data = response.json()
#                     print(f"\n✅ JSON response:")
#                     print(json.dumps(data, indent=2))
#                     return data
#                 except json.JSONDecodeError:
#                     print(f"\n📦 Raw response:")
#                     print(response.text[:1000])
#                     return {"raw": response.text}
#         else:
#             print(f"❌ Error {response.status_code}:")
#             print(response.text[:500])
#             return {"error": f"HTTP {response.status_code}"}
            
#     except Exception as e:
#         print(f"❌ Exception: {str(e)}")
#         return {"error": str(e)}

# def run_quick_tests():
#     """Run quick tests"""
#     print("\n" + "=" * 60)
#     print("🧪 Running Quick Tests")
#     print("=" * 60)
    
#     test_results = []
    
#     # Test 1: Get available seats (no arguments needed)
#     print("\n1️⃣ Testing get_available_seats...")
#     result = execute_tool_simple("get_available_seats", {})
#     test_results.append("error" not in result)
    
#     # Test 2: Check eligibility
#     print("\n2️⃣ Testing check_autorecovery_eligibility...")
#     result = execute_tool_simple("check_autorecovery_eligibility", {
#         "last_name": "Mehta",
#         "email_or_phone": "karan.mehta1@mail.com"
#     })
#     test_results.append("error" not in result)
    
#     # Test 3: Get user profile
#     print("\n3️⃣ Testing get_user_profile...")
#     result = execute_tool_simple("get_user_profile", {
#         "last_name": "Mehta",
#         "email_or_phone": "karan.mehta1@mail.com"
#     })
#     test_results.append("error" not in result)
    
#     # Test 4: Get cancellation details
#     print("\n4️⃣ Testing get_cancellation_details...")
#     result = execute_tool_simple("get_cancellation_details", {
#         "pnr_number": "PNR001",
#         "last_name": "Mehta"
#     })
#     test_results.append("error" not in result)
    
#     # Summary
#     print("\n" + "=" * 60)
#     print("📊 Test Summary")
#     print("=" * 60)
#     passed = sum(test_results)
#     total = len(test_results)
#     print(f"✅ Passed: {passed}/{total}")
#     print(f"❌ Failed: {total - passed}/{total}")

# def test_all_tools():
#     """Test all tools with proper MCP protocol"""
#     print("\n" + "=" * 60)
#     print("🧪 Testing All Tools")
#     print("=" * 60)
    
#     tests = [
#         {
#             "name": "get_available_seats",
#             "args": {},
#             "desc": "Get all available seats"
#         },
#         {
#             "name": "get_user_profile", 
#             "args": {"last_name": "Mehta", "email_or_phone": "karan.mehta1@mail.com"},
#             "desc": "Get user profile"
#         },
#         {
#             "name": "check_autorecovery_eligibility",
#             "args": {"last_name": "Mehta", "email_or_phone": "karan.mehta1@mail.com"},
#             "desc": "Check eligibility"
#         },
#         {
#             "name": "get_cancellation_details",
#             "args": {"pnr_number": "PNR001", "last_name": "Mehta"},
#             "desc": "Get cancellation details"
#         },
#         {
#             "name": "search_available_flights",
#             "args": {"origin": "DEL", "destination": "BOM", "cabin_class": "C"},
#             "desc": "Search flights"
#         },
#         {
#             "name": "get_all_data_for_autorecovery",
#             "args": {"last_name": "Mehta", "email_or_phone": "karan.mehta1@mail.com", "pnr_number": "PNR001"},
#             "desc": "Get all data"
#         }
#     ]
    
#     results = []
#     for test in tests:
#         print(f"\n{'='*40}")
#         print(f"🛠️  {test['name']}")
#         print(f"{'='*40}")
#         print(f"📝 {test['desc']}")
        
#         result = execute_tool_simple(test["name"], test["args"])
#         success = "error" not in result
#         results.append(success)
        
#         # Brief pause
#         time.sleep(0.5)
    
#     # Summary
#     print("\n" + "=" * 60)
#     print("📊 All Tools Test Summary")
#     print("=" * 60)
#     for i, (test, success) in enumerate(zip(tests, results), 1):
#         status = "✅" if success else "❌"
#         print(f"{i}. {status} {test['name']}: {test['desc']}")
    
#     passed = sum(results)
#     total = len(results)
#     print(f"\n✅ Total Passed: {passed}/{total}")
#     print(f"❌ Total Failed: {total - passed}/{total}")

# def interactive_test():
#     """Interactive testing"""
#     print("\n" + "=" * 60)
#     print("🔧 Interactive Tool Testing")
#     print("=" * 60)
    
#     while True:
#         print("\n📋 Available tools:")
#         print("1. get_user_profile - Get user profile")
#         print("2. check_autorecovery_eligibility - Check eligibility")
#         print("3. get_available_seats - Get all available seats")
#         print("4. get_cancellation_details - Get cancellation details")
#         print("5. search_available_flights - Search flights")
#         print("6. get_all_data_for_autorecovery - Get all data")
#         print("7. Test all tools")
#         print("8. Exit")
        
#         choice = input("\n👉 Select option (1-8): ").strip()
        
#         if choice == "1":
#             args = {
#                 "last_name": input("Last name [Mehta]: ").strip() or "Mehta",
#                 "email_or_phone": input("Email/phone [karan.mehta1@mail.com]: ").strip() or "karan.mehta1@mail.com"
#             }
#             execute_tool_simple("get_user_profile", args)
        
#         elif choice == "2":
#             args = {
#                 "last_name": input("Last name [Mehta]: ").strip() or "Mehta",
#                 "email_or_phone": input("Email/phone [karan.mehta1@mail.com]: ").strip() or "karan.mehta1@mail.com"
#             }
#             execute_tool_simple("check_autorecovery_eligibility", args)
        
#         elif choice == "3":
#             execute_tool_simple("get_available_seats", {})
        
#         elif choice == "4":
#             args = {
#                 "pnr_number": input("PNR [PNR001]: ").strip() or "PNR001",
#                 "last_name": input("Last name [Mehta]: ").strip() or "Mehta"
#             }
#             execute_tool_simple("get_cancellation_details", args)
        
#         elif choice == "5":
#             args = {
#                 "origin": input("Origin [DEL]: ").strip() or "DEL",
#                 "destination": input("Destination [BOM]: ").strip() or "BOM",
#                 "cabin_class": input("Cabin class (C/Y) [C]: ").strip() or "C"
#             }
#             execute_tool_simple("search_available_flights", args)
        
#         elif choice == "6":
#             args = {
#                 "last_name": input("Last name [Mehta]: ").strip() or "Mehta",
#                 "email_or_phone": input("Email/phone [karan.mehta1@mail.com]: ").strip() or "karan.mehta1@mail.com",
#                 "pnr_number": input("PNR [PNR001]: ").strip() or "PNR001"
#             }
#             execute_tool_simple("get_all_data_for_autorecovery", args)
        
#         elif choice == "7":
#             test_all_tools()
#             break
        
#         elif choice == "8":
#             print("\n👋 Goodbye!")
#             break
        
#         else:
#             print("❌ Invalid choice")

# def main():
#     """Main function"""
#     print("🤖 Autorecovery MCP Tester")
#     print("=" * 60)
    
#     # First test connection
#     if not test_mcp_connection():
#         return
    
#     print("\n📋 Testing Options:")
#     print("1. Run quick tests")
#     print("2. Test all tools")
#     print("3. Interactive testing")
#     print("4. Exit")
    
#     while True:
#         choice = input("\n👉 Select option (1-4): ").strip()
        
#         if choice == "1":
#             run_quick_tests()
#             break
#         elif choice == "2":
#             test_all_tools()
#             break
#         elif choice == "3":
#             interactive_test()
#             break
#         elif choice == "4":
#             print("\n👋 Goodbye!")
#             break
#         else:
#             print("❌ Invalid choice")

# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\n\n👋 Interrupted by user")
#     except Exception as e:
#         print(f"\n❌ Error: {str(e)}")

import requests
import json

payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "recover_passenger",
        "arguments": {
            "pnr": "PNR001",
            "last_name": "Mehta"
        }
    },
    "id": 1
}

r = requests.post(
    "http://127.0.0.1:8003/mcp",
    json=payload,
    headers={
        "Accept": "application/json, text/event-stream, */*",
        "Content-Type": "application/json"
    }
)

print(r.text)
