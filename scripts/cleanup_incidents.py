import asyncio
import os
from firebase_admin import credentials, firestore, initialize_app

# Initialize Firebase
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "secrets/serviceAccount.json")
if not os.path.exists(cred_path):
    print(f"Error: Firebase credentials not found at {cred_path}")
    exit(1)

cred = credentials.Certificate(cred_path)
initialize_app(cred)
db = firestore.client()

async def cleanup_incidents():
    print("--- ARIA Incident Cleanup ---")
    
    # 1. Resolve all active incidents
    incidents = db.collection("incidents").where("status", "==", "active").stream()
    count = 0
    for doc in incidents:
        doc.reference.update({"status": "resolved", "resolved_at": firestore.SERVER_TIMESTAMP})
        count += 1
    print(f"Resolved {count} active incidents.")

    # 2. Mark all pending dispatches as ACKNOWLEDGED or CANCELLED
    dispatches = db.collection("dispatches").where("ack_status", "==", "PENDING").stream()
    count = 0
    for doc in dispatches:
        doc.reference.update({"ack_status": "CANCELLED"})
        count += 1
    print(f"Cancelled {count} pending dispatches.")
    
    print("Done. The watchdog should be quiet now.")

if __name__ == "__main__":
    asyncio.run(cleanup_incidents())
