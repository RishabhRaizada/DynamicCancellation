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
import os
import logging
import base64
from typing import Dict, Any, Optional

import requests
import httpx
from fastmcp import FastMCP
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("indigo-mcp")


# ---------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------

mcp = FastMCP(
    name="IndiGo Unified Flight Services",
    stateless_http=True
)

# ---------------------------------------------------------------------
# Encryption Helper
# ---------------------------------------------------------------------

PUBLIC_KEY_PEM = """
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyuc1oY3hXeeuiFb/9prBVG0m
C1ZcoK7RBin8izPXgiolPPM//0eIlTBf9bUhlVlU4dzPOiEVgedMUvnWzokEvT9tqo8U
1vk6WnMVMbo3OfVcTDKAIq782OJLNN6U0RCrQq4RQdb0dE5WQOxJ7lQnanbEP1uZO7Ex
kD2YE8n0CVTArnRa8u2k4wC9r4CjzDopBKfPYL5GtZVlOxiJYlysHgfRLosnmBsqfL8e
BEXmkICVqaZGa3yRyyQAWfNngGCdytDe1XR/buCjfz4Jj8Y5WKNpZ7OijqyRKnyysW5r
8/G+WV5RPEb06xsbA8iZOwqokQqDvl9Ml6u2Pyz9X/7thU/+RFUJPZO/seEC3tXVr8uO
XoB9Mu/eOIRez3gkzBEJGQXLdIef4S0hBUIPus9OhntMer2OcXTHIryvl+7Lvcqq45fl
A79NpK2e1chOcxBS5/lVMAc6xBjdFi+0WHqhm72he315w0xQp6Mua5bHrKAQvi+Tzw15
TjXcY9mZha/46JVgVX6/PsGyakSCK6F1YBeSSMYLsP4Ej8cH23LOtqkQlbqRKAX2tnEo
/7juHCtx7E9k3xHqB1dKR21qkf3Wq+qLERAtoZK40HcBb25CbKU21StYVI2pwRWCSTUP
GWG/Mtc1dShEX40J3HKVW2XwghjlyCY110G0K8dFAOvSNaUCAwEAAQ==
-----END PUBLIC KEY-----
"""

def encrypt(value: str) -> str:
    key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())
    encrypted = key.encrypt(
        value.encode(),
        padding.OAEP(
            mgf=padding.MGF1(hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None,
        )
    )
    return base64.b64encode(encrypted).decode()
# =====================================================
# CDP PREFERENCE EXTRACTION
# =====================================================


# =====================================================
# AUTO SEAT SELECTION (NO USER INPUT)
# =====================================================

def auto_select_seat(seats_resp: Dict[str, Any], seat_preference: Optional[str]) -> Optional[Dict[str, Any]]:
    try:
        # data = seats_resp.get("data", {}).get("structuredContent",{})
        seat_maps = seats_resp.get("data", {}).get("seatMaps", [])
        passengers = seats_resp.get("data", {}).get("passengers", [])
        pax_count = len(passengers)
        seats=[]
        for sm in seat_maps:
            compartments = sm["seatMap"]["decks"]["1"]["compartments"]
            if "C" not in compartments:
                continue
            
            for seat in compartments["C"].get("units", []):
                if not seat.get("assignable"):
                    continue
                selected_seat = None
                if seat_preference is not None:
                    for prop in seat.get("properties", []):
                        if prop.get("code").lower() == seat_preference and prop.get("value").lower() == "true":
                            selected_seat = seat
                            break 
                    if(selected_seat is None):
                        continue
                            
                else:
                    selected_seat = seat
                    
                    
                if(len(seats) < pax_count): # and seat.get("availability",0) >=5):
                    selected_seat["passengerKey"]=passengers[len(seats)].get("passengerKey","")
                    seats.append(selected_seat)
                else:
                    return seats
            if(len(seats) < pax_count):
                for seat in compartments["C"].get("units", []):
                    if not seat.get("assignable"):
                        continue
                    taken = [taken_seat for taken_seat in seats if seat.get("unitKey","") == taken_seat.get("unitKey","")]
                    if(len(taken) >0):
                        continue
                    
                    if(len(seats) < pax_count): # and seat.get("availability",0) >=5):
                        seat["passengerKey"]=passengers[len(seats)].get("passengerKey","")
                        seats.append(seat)
    

    except Exception as ex:
        return None

    return seats

def extract_seat_preferences(cdp_profile: Dict[str, Any]) -> Dict[str, Any]:
    preferences = {}
    try:
        data = cdp_profile.get("structuredContent",{}).get("data", {})
        if(data == {}):
            data = {
                "age": 0,
                "agentcorP_MOBILEAPP": 0,
                "agentcorP_WEB": 0,
                "aisle": 0,
                "annualtrips": 2,
                "avgweightdom": "5.00",
                "avgweightint": "0.00",
                "b2C_MOBILEAPP": 0,
                "b2C_OTA": 0,
                "b2C_WEB": 0,
                "beaches": 0,
                "bookconnection": 0,
                "bundleproducts": 0,
                "business": 0,
                "cancellatioN_COUNT": 0,
                "changE_COUNT": 0,
                "child": 0,
                "companion": 0,
                "corporate": 0,
                "dayflight": 0,
                "defense": 0,
                "departurE_FY": 2023,
                "dependenttravel": 0,
                "detractor": 0,
                "doctoR_NURSE": 0,
                "domestic": 2,
                "earlyplanner": 2,
                "email": "mananbhatia02@gmail.com",
                "eveningflight": 1,
                "excessbaggage": 0,
                "family": 0,
                "familY_FARE": 0,
                "female": 0,
                "festivaltraveler": 0,
                "ffwd": 0,
                "firstdateofdeparture": "Wed, 24 Aug 2022 05:05:00 GMT",
                "firstname": "MANAN",
                "firsT_USR_UNIQUE_ID": "FA-C673CBC2B0314FA5-984974775",
                "flewbeforE2FY": "Y",
                "flexi": 0,
                "fliesconnection": 0,
                "flyingafteR2FY": "N",
                "foreigncurrency": 0,
                "group": 0,
                "guid": "654e0c6a-40fe-4eef-a86f-04e53f608639",
                "highspenderhighfreq": "N",
                "highspenderlowfreq": "N",
                "hotelcustomer": "N",
                "infant": 0,
                "international": 0,
                "lastchannel": "Other_Agents_TMC_B2B_etc",
                "lastminuteflyer": 0,
                "lastname": "BHATIA",
                "leisure": 2,
                "lowspenderhighfreq": "N",
                "lowspenderlowfreq": "Y",
                "male": 1,
                "metrO_METRO": 0,
                "metrO_NONMETRO": 1,
                "middle": 3,
                "mobile": "9718822702",
                "morningflight": 1,
                "mountains": 0,
                "multicity": 0,
                "newcustomer": "Y",
                "nobaggagesegments": 0,
                "nofilteR_COLLAB": "N",
                "nonmetrO_METRO": 1,
                "nonmetrO_NONMETRO": 0,
                "noN_VEG_MEAL": 0,
                "onetimeflier": 1,
                "oneway": 0,
                "otherbooked": 0,
                "others": 0,
                "otheR_AGENTS_TMC_B2B_ETC": 1,
                "otheR_FARE_TYPES": 0,
                "passive": 0,
                "plains": 2,
                "preferreddestination": "DEL",
                "preferredorigin": "DEL",
                "promo": 2,
                "promocode": 0,
                "promoter": 0,
                "redeyeflight": 0,
                "repeatcustomer": "N",
                "return": 0,
                "roundtrip": 2,
                "roundtripS_DIFFPNR": 0,
                "saver": 0,
                "secondlastchannel": "",
                "selfbooked": 1,
                "skai": 0,
                "sme": 0,
                "solo": 1,
                "spotifY_COLLAB": "N",
                "sR_CITIZEN": 0,
                "stretch": 0,
                "student": 0,
                "supeR6E": 0,
                "totalnoshowsegments": 0,
                "totalpnr": 1,
                "totalsegments": 2,
                "totalspend": "11066.00",
                "totaltrips": 2,
                "totaL_INFLIGHT_SPEND": "0.00",
                "tripS_INSURED": 0,
                "unaccompanieD_MINOR": 0,
                "uniquedestinations": 2,
                "uniqueorigins": 2,
                "veG_MEAL": 0,
                "weekdaytravel": 2,
                "weekendtravel": 0,
                "wheelchair": 0,
                "window": 2,
                "xl": 0,
                "msg": None
            }
        seat_preference = None
        level_of_preference = 0
        for k,v in data.items():
            if "aisle" in k.lower() and v > 0 and level_of_preference < v:                
                seat_preference = "aisle"
                level_of_preference = v
            if "window" in k.lower() and v > 0 and level_of_preference < v:
                seat_preference = "window"
                level_of_preference = v
            if "middle" in k.lower() and v > 0 and level_of_preference < v:
                seat_preference = "middle"
                level_of_preference = v
            
        return seat_preference
    except Exception:
        pass
    return preferences
# ---------------------------------------------------------------------
# MCP TOOL: Upgrade Bundle POP Sector Level
# ---------------------------------------------------------------------
# @mcp.tool(name ="upgrade_bundle",
#           description="Check and suggest sector-level stretch seat upgrade options for a given PNR and Last Name",)
def pop_sector_upgrade_agent(
    pnr: str,
    last_name: str,
    email: Optional[str] = None,
    mobile: Optional[str] = None
) -> Dict[str, Any]:

    # --------------------------------------------------
    # Step 1: Generate Token
    # --------------------------------------------------
    token_resp = generate_token()
    if token_resp["data"] == None:
        return {"suggestion": "NO", "reason": "Token generation failed"}
    data = token_resp#.get("data", {}).get("structuredContent", {})
    token = data["data"].get("token")
    if not token:
        return {"suggestion": "NO", "reason": "Invalid token"}

    # --------------------------------------------------
    # Step 2: Eligibility (PNR Level)
    # --------------------------------------------------
    eligibility = Eligibility(pnr, last_name, token)
    data = eligibility#.get("data", {}).get("structuredContent", {})
    print(data)
    flags = data.get("retrieve", {}).get("upgradeEligiblityDetails", {})
    

    if flags.get("isPlanB") or flags.get("isSlt") or flags.get("isGroupBooking"):
        return {"suggestion": "NO", "reason": "PNR not eligible"}

    # --------------------------------------------------
    # Step 3: Availability (Retrieve)
    # --------------------------------------------------
    avail = availability(token)
    journeys = avail.get("data", {}).get("journeys", [])#["data"].get("structuredContent", {})
    upgradable_journeys = []
    for journey in journeys:
        useKey = journey.get("useKey","")
        if(useKey and useKey == "fareAvailabilityKey"):
            upgradable_journeys.append(journey)
            continue
        upgradable_segments = []
        for segment in journey.get("segments", []):
            key = segment.get("classModifyKey", "")
            if key and len(key) > 0:
                upgradable_segments.append(segment)
                break
        if(len(upgradable_segments) > 0):
            journey["segments"] = upgradable_segments
            upgradable_journeys.append(journey)

    if len(upgradable_journeys) == 0:
        return {"suggestion": "NO", "reason": "No sector-level upgrade available"}

     # --------------------------------------------------
    # Step 5: CDP Preferences (AUTO)
    # --------------------------------------------------
    seat_preference = None
    if email and mobile:
        cdp_token = cdp_token_generation()
        if cdp_token["status"] == "success":
            profile = retrieve_customer_details(email, mobile)
            seat_preference = extract_seat_preferences(profile.get("data", {}))

    # --------------------------------------------------
    # Step 4: Dynamic Pricing
    # --------------------------------------------------
    results = []
    for journey in upgradable_journeys:
        d = journey.get("designator", {})
        origin, destination = None, None
        segements = journey.get("segments", [])
        if len(segements) > 0:
            origin = segements[0].get("designator", {}).get("origin")
            destination = segements[-1].get("designator", {}).get("destination")
        
        sector = f"{origin}-{destination}"
        fare_price = None
        if("fareAvailabilityKey" in journey and journey["fareAvailabilityKey"] is not None and len(journey["fareAvailabilityKey"]) > 0):
            fare_price = journey.get("fareOptions", [{}])[0].get("totals" , {}).get("fareTotal", None)
        journey.get("fareOptions", [])
        price_resp = dynamic_price(sector, token)

        price = price_resp.get("data", {}).get("price") or fare_price or 10000
        journey["upgradePrice"] = price

        # --------------------------------------------------
        # Step 6: Seat Map + Auto Selection
        # --------------------------------------------------
        seats_resp =  get_entire_seats(token)
        seats = auto_select_seat(seats_resp, seat_preference)
        if not seats or len(seats) < 0:
            return {"suggestion": "NO", "reason": "No eligible seats found"}

        # --------------------------------------------------
        # Step 7: Final POP Bundle
        # --------------------------------------------------
        results.append( {
            "suggestion": "YES",
            "bundle": {
                "type": "Best_SECTOR_LEVEL_Available_Stretch_Bundle",
                "sector": sector,
                "journey_details": journey,
                "seat": seats,
                "price": price,
                "autoSelected": True
            }
        })
    mx=0
    result=[]
    for res in results:
        if(res["bundle"]["price"] > mx):
            mx=res["bundle"]["price"]
            result=[res]
    return {"results": result}

# ---------------------------------------------------------------------
# 1. Generate Token
# ---------------------------------------------------------------------

TOKEN_API_URL = "https://dotrezapi45-nonprod-3scale-apicast-production.apps.ocpnonprodcl01.goindigo.in/api/nsk/v2/token"
TOKEN_USER_KEY = os.getenv("TOKEN_USER_KEY", "b606c5f2277c7278d0be64a600635a21")

def generate_token() -> Dict[str, Any]:
    response = requests.post(
        TOKEN_API_URL,
        headers={
            "Content-Type": "application/json",
            "user_key": TOKEN_USER_KEY
        },
        json={},
        timeout=15
    )
    response.raise_for_status()
    return response.json()

# ---------------------------------------------------------------------
# 2. Eligibility
# ---------------------------------------------------------------------

ELIGIBILITY_API_URL = "https://api-uat-skyplus.goindigo.in/flightupgrade/v1/upgradestretch/eligibility"
ELIGIBILITY_USER_KEY = "2945e931b5e99bceed811fd202713432"
ELIGIBILITY_TIMEOUT_SEC = 15

# Alias for compatibility with the corrected function
encrypt_with_public_key = encrypt

def Eligibility(RecordLocator: str, LastName: str, token: str) -> Dict[str, Any]:
    """
   Flow:
    1. Use the provided token.
    2. Call Retrieve endpoint with required body and LastName.
    3. Return retrieve JSON response or error.
    
    Args:
        RecordLocator: The booking record locator (required)
        LastName: The passenger's last name (required)
        token: The authorization token (required)
    """
    # Build input data from individual parameters
    input_data = {
        "RecordLocator": RecordLocator,
        "LastName": LastName,
    }
    
    # Encrypt all values for query params
    params = {k: encrypt_with_public_key(v) for k, v in input_data.items() if v is not None}

    # Step 1: Used the Generated_Token from the tool generate_token
    response =requests.get(RETRIEVE_API),
    
    # Step 2: Call eligibility endpoint
    headers = {
        "Authorization": token,
        "user_key": ELIGIBILITY_USER_KEY,
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(
            ELIGIBILITY_API_URL,
            headers=headers,
            params=params,
            timeout=ELIGIBILITY_TIMEOUT_SEC,
        )
        response.raise_for_status()
        final_response = {
            "retrieve": response.json(),
            "token_used": token,
        }
        return final_response
    except requests.HTTPError as http_err:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        return {"status": response.status_code, "error": str(http_err), "response": detail}
    except Exception as e:
        return {"status": 500, "error": str(e)}

# ---------------------------------------------------------------------
# 3. Availability
# ---------------------------------------------------------------------

RETRIEVE_API = "https://api-uat-skyplus.goindigo.in/flightupgrade/v1/upgradestretch/retrieve"
def availability(token: str) -> Dict[str, Any]:
    response = requests.get(
        RETRIEVE_API,
        headers={
            "Authorization": token,
            "user_key": ELIGIBILITY_USER_KEY
        },
        timeout=15
    )
    response.raise_for_status()
    result = response.json()
    found_key = False
    use_key = ""
    if("data" in result and result["data"] is not None and "journeys" in result["data"] and result["data"]["journeys"] is not None and len(result["data"]["journeys"]) > 0):
        for journey in result["data"]["journeys"]:
            found_key = False
            use_key = ""
            if("segments" in journey and journey["segments"] is not None and len(journey["segments"]) > 0):
                for segment in journey["segments"]:
                    if("classModifyKey" in segment and segment["classModifyKey"] is not None):
                        journey["classModifyKey"] = segment["classModifyKey"]
                        found_key = True
                        journey["useKey"] = "classModifyKey"
            if(found_key):
                continue
            if("fareOptions" in journey and journey["fareOptions"] is not None and len(journey["fareOptions"]) > 0):
                for fareOption in journey["fareOptions"]:
                    if("fareAvailabilityKey" in fareOption and fareOption["fareAvailabilityKey"] is not None):
                        journey["fareAvailabilityKey"] = fareOption["fareAvailabilityKey"]
                        journey["useKey"] = "fareAvailabilityKey"
                        found_key = True
                        break
    return result

# ---------------------------------------------------------------------
# 4. Dynamic Price
# ---------------------------------------------------------------------

DYNAMIC_PRICE_API = "https://ancillaryengine-nonprod-3scale-apicast-production.apps.ocpnonprodcl01.goindigo.in/stretch/recommendation"
STRETCH_USER_KEY = "a7d511cec49d91aa4978b1937cbd4451"
def dynamic_price(sector: str, authorization_token: str) -> Dict[str, Any]:
    response = requests.post(
        DYNAMIC_PRICE_API,
        headers={
            "authorization": authorization_token,
            "user_key": STRETCH_USER_KEY,
            "Content-Type": "application/json"
        },
        json={"sector": sector},
        timeout=15
    )
    # response.raise_for_status()
    return response.json()

# ---------------------------------------------------------------------
# Flight Upgrade Tool
# ---------------------------------------------------------------------

UPGRADE_API_URL = r"https://api-uat-skyplus.goindigo.in/flightupgrade/v1/upgradestretch/upgrade"
def upgradeStretchBooking(journeyKey: str, classModifyKey: Optional[str], fareAvailabilityKey: Optional[str], token: str) -> Dict[str, Any]:
    """
    Flow:
    1. Use the provided token.
    2. Call upgrade endpoint with required headers and journey data.
    3. Return upgrade JSON response or error.
    
    Args:
        journeyKey: The journey key identifier (required)
        classModifyKey: The class modification key (required)
        token: The authorization token (required)
    """
    
    payload = {}
    print(journeyKey, classModifyKey, fareAvailabilityKey)
    # Step 2: Build payload from individual parameters
    if(classModifyKey is not None and classModifyKey != ""):
        payload = {
            "journeysToUpgrade": [
                {
                    "journeyKey": journeyKey,
                    "classModifyKey": classModifyKey
                }
            ]
        }
    elif(fareAvailabilityKey is not None and fareAvailabilityKey != ""):
        payload = {
            "journeysToUpgrade": [
                {
                    "journeyKey": journeyKey,
                    "fareKey": fareAvailabilityKey
                }
            ]
        }
    else:
        return {
            "status": 400,
            "error": "Either classModifyKey or fareAvailabilityKey must be provided."
        }
    print(payload)
    # Step 3: Call upgrade endpoint
    headers = {
        "Authorization": token,
        "user_key": ELIGIBILITY_USER_KEY,
        "Content-Type": "application/json",
        "Cookie": "0e301b3d9667a680d70f059c3902e4b1=d3c15babc1f494e3c474d6c32a397e37; 6b3f2552215b6b1885935a0b015c2546=e37873bf04697e711eaa77eecb9cec0b"
    }
    
    try:
        logger.info(f"Calling upgrade API: {UPGRADE_API_URL}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")
        
        response = requests.post(
            UPGRADE_API_URL,
            headers=headers,
            json=payload,
            timeout=ELIGIBILITY_TIMEOUT_SEC,
        )
        print(response)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        try:
            response.raise_for_status()
            result = response.json()
            logger.info("Flight upgrade processed successfully")
            
            final_response = {
                "upgrade": result,
                "token": token,
            }
            return final_response
            
        except requests.HTTPError as http_err:
            try:
                detail = response.json()
                # Check if the customer is already upgraded
                return {
                    "status": "already_upgraded",
                    "message": "You are already upgraded to Stretch seat. No further upgrade is needed.",
                    "customer_message": "Your seat has already been upgraded. Enjoy your enhanced travel experience!",
                    "details": detail
                }
            except Exception:
                detail = response.text
                # Check text response for upgrade status
                return {
                    "status": "already_upgraded", 
                    "message": "You are already upgraded to Stretch seat. No further upgrade is needed.",
                    "customer_message": "Your seat has already been upgraded. Enjoy your enhanced travel experience!",
                    "details": detail
                }
            
            # logger.error(f"HTTP error: {http_err} | Details: {detail}")
            # return {
            #     "status": response.status_code, 
            #     "error": str(http_err), 
            #     "response": detail,
            # }
            
    except requests.Timeout:
        logger.error(f"Request timed out after {ELIGIBILITY_TIMEOUT_SEC}s")
        return {
            "status": 500, 
            "error": f"Request timeout after {ELIGIBILITY_TIMEOUT_SEC}s"
        }
    except Exception as e:
        logger.error(f"Upgrade API call failed: {e}")
        return {"status": 500, "error": f"API call failed: {str(e)}"}

# ---------------------------------------------------------------------
# 5. Get Entire Seats
# -------------------------------------------------------------------
def get_entire_seats(authorization: str) -> Dict[str, Any]:
    # if not authorization.startswith("Bearer "):
    #     authorization = f"Bearer {authorization}"

     
        response = requests.get(
            "https://api-qa-seat-selection-skyplus6e.goindigo.in/v1/seat/getentireseats",
            headers={
                "Authorization": authorization,
                "user_key": "9ad8345ab99a9874003b26b2fa5d3bea"
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result
        # if("data" in result and result["data"] is not None and "seatMaps" in result["data"] and result["data"]["seatMaps"] is not None and len(result["data"]["seatMaps"]) > 0):
        #     for seatMap in result["data"]["seatMaps"]:

                
        #         if("seatMap" in seatMap and seatMap["seatMap"] is not None and "decks" in seatMap["seatMap"] and "1" in seatMap["seatMap"]["decks"] and seatMap["seatMap"]["decks"]["1"] is not None and "compartments" in seatMap["seatMap"]["decks"]["1"] and seatMap["seatMap"]["decks"]["1"]["compartments"] is not None):
        #                 compartment = seatMap["seatMap"]["decks"]["1"]["compartments"]
        #                 if("C" in compartment and compartment["C"] is not None and "units" in compartment["C"] and compartment["C"]["units"] is not None and len(compartment["C"]["units"]) > 0):
        #                     if("availableUnits" in compartment["C"] and compartment["C"]["availableUnits"] is not None and compartment["C"]["availableUnits"] <= 0):
        #                         return result
        #                     for unit in compartment["C"]["units"]:
        #                         if("availability" in unit and unit["availability"] is not None and unit["availability"] == 5):
        #                             return result
                    
        # return result

# ---------------------------------------------------------------------
# 6. CDP Token Generation (FirstHive)
# ---------------------------------------------------------------------

def cdp_token_generation(
    username: str = "InOther",
    password: str = "bgcHisrO",
    role: str = "reader"
) -> Dict[str, Any]:
    response = requests.post(
        "https://ind1-de.firsthive.com/GentokenAPI_ID",
        json={
            "username": username,
            "password": password,
            "role": role
        },
        timeout=15
    )
    response.raise_for_status()
    return response.json()

# ---------------------------------------------------------------------
# 7. Retrieve Customer Details
# ---------------------------------------------------------------------
async def retrieve_customer_details(email: str, mobile: str, fy: str = "2025",) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://ind1-de.firsthive.com/customerDetailAPI",
            json={"email": email, "mobile": mobile, "fy": fy},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        path="/mcp"
    )
