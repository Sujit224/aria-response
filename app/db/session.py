"""
Replaces the Redis-based session.py.
The get_db() shim is kept so that graph nodes calling
'from app.db.session import AsyncSessionLocal' don't break
during the transition period.
"""
from app.db.firebase import get_db  # noqa: F401 — re-export for compat


class _FakeSessionLocal:
    """
    Compatibility stub.  The LangGraph nodes have been migrated to use
    app.db.collections directly, but any leftover import of AsyncSessionLocal
    will not crash the server.
    """
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


AsyncSessionLocal = _FakeSessionLocal


async def init_db():
    """No-op — Firestore is schema-less, no migrations needed."""
    pass