import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """
    Several test files instantiate `TestClient(app)` at module level without a
    `with` block. Newer Starlette only runs FastAPI's lifespan (which creates
    tables via Base.metadata.create_all) inside a context-managed TestClient, so
    those tests would otherwise hit "no such table" against a fresh DB. Creating
    tables directly here is version-independent and doesn't require touching
    every test file's TestClient usage.
    """
    from app.database.base import Base
    from app.database.session import engine
    import app.models.entities  # noqa: F401 -- registers all models on Base.metadata

    Base.metadata.create_all(bind=engine)
