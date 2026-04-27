import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, messaging

load_dotenv()

_app: firebase_admin.App | None = None
_db = None


def initialize() -> None:
    """
    Call once from FastAPI lifespan (app/main.py).
    Reads FIREBASE_CREDENTIALS_PATH from .env.
    Falls back to Application Default Credentials if env var missing
    (useful when deployed to Google Cloud Run / Firebase Hosting).
    """
    global _app, _db

    if _app is not None:
        return  # already initialised (e.g. hot-reload)

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if cred_path:
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
    else:
        # Application Default Credentials (Cloud Run, GKE, etc.)
        _app = firebase_admin.initialize_app()

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
