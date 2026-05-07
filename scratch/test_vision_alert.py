
import os
import sys
import argparse
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.vision.aria_bridge import ARIABridge

def test_dispatch(alert_type="WEAPON"):
    load_dotenv()
    
    bridge = ARIABridge()
    
    # Mock data based on type
    if alert_type.upper() == "FIRE":
        alert = {
            "type": "FIRE",
            "source": "smoke_detector",
            "location": "Middle-Left",
        }
        threat_result = {
            "threat_level": "HIGH",
            "threat_message": "TEST: Smoke and fire detected at Middle-Left. Automatic evacuation routes computed.",
        }
    else:
        alert = {
            "type": "WEAPON",
            "source": "weapon_detector",
            "location": "Bottom-Right",
        }
        threat_result = {
            "threat_level": "CRITICAL",
            "threat_message": "TEST: Person with a firearm detected at Bottom-Right. Lockdown initiated.",
        }
    
    print(f"Dispatching mock {alert_type} vision alert to ARIA...")
    bridge.dispatch(alert, threat_result)
    print("Alert dispatched! Check the Staff Dashboard and Guest PWA.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="WEAPON", choices=["WEAPON", "FIRE"], help="Type of alert to simulate")
    args = parser.parse_args()
    
    test_dispatch(args.type)
