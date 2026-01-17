"""
Production MCP Server for Flight Recovery
Connects with Azure AI Agent via MCP protocol
"""

import json
import logging
import time
from datetime import datetime
from fastmcp import FastMCP
from typing import Dict, Any, Optional

# Import your existing tools
from tools.validator import validate_request
from tools.profile import find_users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("flight_recovery_mcp")

# Initialize MCP server
mcp = FastMCP("flight_recovery_mcp")  # Simplified initialization

# -------------------------------------------------
# DATA LOADING
# -------------------------------------------------

def load_data():
    """Load all required data files"""
    try:
        with open("data/cancell_trigger.json", "r", encoding="utf-8") as f:
            cancellations = json.load(f)
        
        with open("data/available_seats.json", "r", encoding="utf-8") as f:
            available_seats = json.load(f)
        
        logger.info(f"✅ Loaded {len(cancellations)} cancellations and {len(available_seats)} flight options")
        return cancellations, available_seats
        
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        raise

CANCELLATIONS, AVAILABLE_SEATS = load_data()

# -------------------------------------------------
# RECOVERY ENGINE
# -------------------------------------------------

class RecoveryEngine:
    """Core recovery logic"""
    
    @staticmethod
    def find_cancellation(pnr: str) -> Optional[Dict[str, Any]]:
        """Find cancellation record by PNR"""
        for cancellation in CANCELLATIONS:
            if cancellation.get("pnr") == pnr:
                return cancellation
        return None
    
    @staticmethod
    def validate_passenger(cancellation: Dict[str, Any], last_name: str) -> Dict[str, Any]:
        """Validate passenger eligibility"""
        user_info = cancellation.get("user_info", {})
        email = user_info.get("USR_EMAIL")
        phone = str(user_info.get("USR_MOBILE", ""))
        
        eligibility = validate_request(
            last_name=last_name,
            email_or_phone=email or phone
        )
        
        return {
            "eligible": eligibility.get("eligible", False) if eligibility else False,
            "details": eligibility,
            "contact": {"email": email, "phone": phone}
        }
    
    @staticmethod
    def find_best_recovery_option() -> Dict[str, Any]:
        """Find the best available flight and seat"""
        if not AVAILABLE_SEATS:
            return {"flight": None, "seat": None}
        
        # Simple algorithm: first available flight with window seat
        for flight in AVAILABLE_SEATS:
            for seat in flight.get("seats", []):
                if seat.get("available") and seat.get("type", "").lower() == "window":
                    return {"flight": flight, "seat": seat}
            
            # Fallback: any available seat
            for seat in flight.get("seats", []):
                if seat.get("available"):
                    return {"flight": flight, "seat": seat}
        
        # Default to first flight, no seat
        return {"flight": AVAILABLE_SEATS[0], "seat": None}

# -------------------------------------------------
# MCP TOOLS
# -------------------------------------------------

@mcp.tool()
def prepare_recovery_context(pnr: str, last_name: str) -> str:
    """
    Main recovery tool for Azure AI Agent.
    
    Args:
        pnr: Passenger name record
        last_name: Passenger's last name for verification
        
    Returns:
        JSON string with recovery details
    """
    logger.info(f"🔧 Tool called: prepare_recovery_context(pnr={pnr}, last_name={last_name})")
    
    start_time = time.time()
    recovery_engine = RecoveryEngine()
    
    # Step 1: Find cancellation
    cancellation = recovery_engine.find_cancellation(pnr)
    if not cancellation:
        return json.dumps({
            "status": "error",
            "error_code": "PNR_NOT_FOUND",
            "message": f"No cancellation found for PNR: {pnr}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    # Step 2: Validate passenger
    validation = recovery_engine.validate_passenger(cancellation, last_name)
    if not validation["eligible"]:
        return json.dumps({
            "status": "error",
            "error_code": "NOT_ELIGIBLE",
            "message": "Passenger not eligible for automatic recovery",
            "validation_details": validation["details"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    # Step 3: Get passenger profile
    profile = find_users(
        last_name=last_name,
        email_or_phone=validation["contact"]["email"] or validation["contact"]["phone"]
    )
    
    # Step 4: Find recovery option
    recovery_option = recovery_engine.find_best_recovery_option()
    
    # Step 5: Build response
    response = {
        "status": "success",
        "recovery_id": f"REC-{pnr}-{int(time.time())}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "processing_time_ms": int((time.time() - start_time) * 1000),
        
        "passenger": {
            "pnr": pnr,
            "last_name": last_name,
            "first_name": cancellation.get("user_info", {}).get("USR_FIRSTNAME", ""),
            **validation["contact"],
            "profile_summary": {
                "loyalty_tier": "Gold" if validation.get("details", {}).get("eligible", False) else "Standard",
                "high_value": validation.get("details", {}).get("high_value", False)
            }
        },
        
        "cancelled_flight": {
            "flight_number": cancellation.get("flight_number"),
            "origin": cancellation.get("origin"),
            "destination": cancellation.get("destination"),
            "scheduled_departure": cancellation.get("scheduled_departure"),
            "cabin_class": cancellation.get("cabin_class")
        },
        
        "recovery_flight": recovery_option["flight"],
        "assigned_seat": recovery_option["seat"],
        
        "recovery_summary": {
            "status": "CONFIRMED",
            "action": "Auto-rebooked on next available flight",
            "compensation": ["₹2,000 meal voucher", "Priority boarding"],
            "notes": "Baggage will be automatically transferred"
        }
    }
    
    logger.info(f"✅ Recovery prepared for {pnr}/{last_name} in {response['processing_time_ms']}ms")
    return json.dumps(response, indent=2)

@mcp.tool()
def check_recovery_status(recovery_id: str) -> str:
    """
    Check status of an existing recovery.
    
    Args:
        recovery_id: Recovery ID from prepare_recovery_context
        
    Returns:
        JSON string with current status
    """
    logger.info(f"🔧 Tool called: check_recovery_status(recovery_id={recovery_id})")
    
    # In production, this would check a database
    # For now, return mock status
    return json.dumps({
        "status": "success",
        "recovery_id": recovery_id,
        "current_status": "CONFIRMED",
        "checkin_status": "READY",
        "boarding_pass": "AVAILABLE",
        "last_updated": datetime.utcnow().isoformat() + "Z"
    })

# -------------------------------------------------
# SERVER STARTUP
# -------------------------------------------------

if __name__ == "__main__":
    logger.info("🚀 Starting Flight Recovery MCP Server")
    logger.info("🔧 Available tools:")
    logger.info("   • prepare_recovery_context(pnr, last_name)")
    logger.info("   • check_recovery_status(recovery_id)")
    logger.info(f"📡 Server URL: http://127.0.0.1:8003/mcp")
    logger.info("💡 Description: Flight disruption recovery system for Azure AI Agents")
    
    mcp.run(
        transport="http",  # Changed from streamable-http for compatibility
        host="127.0.0.1",
        port=8003,
        path="/mcp"
    )