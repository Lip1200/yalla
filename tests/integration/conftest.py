"""Integration test fixtures.

`client` provides a FastAPI TestClient with `supabase_client` swapped
out at every module that imports it. All authenticated requests use
the service token (matches `API_SECRET_TOKEN=test-secret` set in
tests/conftest.py) so we exercise the real `get_current_user` path and
the downstream routers, but never hit the network.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests._fakes import FakeStore, FakeSupabaseClient


# All modules that hold a `supabase_client` binding at import time.
# The integration fixture replaces it on every one of them at once so
# the in-memory store is shared.
_PATCH_TARGETS = [
    "src.core.database",
    "src.core.security",
    "src.modules.auth.service",
    "src.modules.challenges.service",
    "src.modules.consents.service",
    "src.modules.doctors.service",
    "src.modules.health.service",
    "src.modules.messaging.service",
    "src.modules.patients.service",
    "src.modules.restaurants.service",
    "src.modules.social.service",
    "src.modules.users.service",
    "src.modules.users.router",
]


@pytest.fixture
def fake_store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def fake_supabase(fake_store: FakeStore) -> FakeSupabaseClient:
    return FakeSupabaseClient(store=fake_store)


@pytest.fixture
def client(
    fake_supabase: FakeSupabaseClient,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    import importlib

    for target in _PATCH_TARGETS:
        try:
            mod = importlib.import_module(target)
        except ImportError:
            # Some modules may not exist on a partial branch — skip.
            continue
        if hasattr(mod, "supabase_client"):
            monkeypatch.setattr(mod, "supabase_client", fake_supabase)

    # Reload main to pick up the patched modules.
    from src.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Service-token headers. tests/conftest.py set
    API_SECRET_TOKEN=test-secret."""
    return {"Authorization": "Bearer test-secret"}
