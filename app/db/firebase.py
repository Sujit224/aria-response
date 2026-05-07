import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, messaging

load_dotenv()

_app: firebase_admin.App | None = None
_db = None


def initialize() -> None:
    """
    Call once from FastAPI lifespan (app/main.py).
    1. Checks FIREBASE_SERVICE_ACCOUNT for a JSON string (Railway/Production).
    2. Falls back to FIREBASE_CREDENTIALS_PATH (Local Dev).
    3. Falls back to Application Default Credentials.
    """
    global _app, _db

    if _app is not None:
        return  # already initialised (e.g. hot-reload)

    # 1. Try to load from JSON string variable
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    
    if service_account_json:
        try:
            cred_info = json.loads(service_account_json)
            cred = credentials.Certificate(cred_info)
            _app = firebase_admin.initialize_app(cred)
            print("[ARIA] Firebase initialized from FIREBASE_SERVICE_ACCOUNT env var")
        except Exception as e:
            print(f"[ARIA] Error parsing FIREBASE_SERVICE_ACCOUNT: {e}")
            raise e
            
    # 2. Fall back to the path
    else:
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path:
            cred = credentials.Certificate(cred_path)
            _app = firebase_admin.initialize_app(cred)
            print(f"[ARIA] Firebase initialized from path: {cred_path}")
        else:
            # Application Default Credentials (Cloud Run, GKE, etc.)
            _app = firebase_admin.initialize_app()
            print("[ARIA] Firebase initialized from Application Default Credentials")

    _db = firestore.client()
    print("[ARIA] Firebase Firestore client ready")


def get_db():
    """
    Returns the synchronous Firestore client.
    All writes/reads are wrapped with asyncio.run_in_executor
    in collections.py to stay non-blocking inside async FastAPI handlers.
    """
    if _db is None:
        raise RuntimeError(
            "Firebase not initialised — call firebase.initialize() at startup."
        )
    return _db


def get_messaging():
    """Returns the firebase_admin.messaging module for FCM sends."""
    return messaging
