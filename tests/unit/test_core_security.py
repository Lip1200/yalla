"""Unit tests for core/security.py — the dependency-injection layer
between Supabase Auth and our FastAPI handlers."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core import security as security_module
from src.core.security import AuthIdentity, get_current_user, get_profile_for_identity
from tests._fakes import FakeSupabaseClient


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    client = FakeSupabaseClient()
    client.store.seed(
        "profiles",
        [
            {"id": 108, "full_name": "Tefa", "role": "patient", "auth_user_id": "user-tefa"},
            {"id": 107, "full_name": "Dr. Filipe", "role": "doctor", "auth_user_id": "user-doctor"},
        ],
    )
    # postgrest mock so the .auth(key) restore call in get_current_user
    # doesn't AttributeError.
    client.postgrest = MagicMock()
    # auth submodule — get_user is mocked per-test.
    client.auth = MagicMock()
    monkeypatch.setattr(security_module, "supabase_client", client)
    return client


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestGetProfileForIdentity:
    def test_returns_none_for_service_identity(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="service", is_service=True)
        assert get_profile_for_identity(identity) is None

    def test_returns_profile_for_real_user(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="user-tefa", is_service=False)
        profile = get_profile_for_identity(identity)
        assert profile is not None
        assert profile["id"] == 108

    def test_returns_none_when_no_linked_profile(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="user-unknown", is_service=False)
        assert get_profile_for_identity(identity) is None


class TestGetCurrentUser:
    def test_missing_credentials_returns_401(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=None)
        assert exc.value.status_code == 401

    def test_empty_token_returns_401(self, fake_client: FakeSupabaseClient) -> None:
        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=_creds(""))
        assert exc.value.status_code == 401

    def test_service_token_returns_service_identity(
        self, fake_client: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(security_module.settings, "api_secret_token", "secret-X")
        identity = get_current_user(credentials=_creds("secret-X"))
        assert identity.is_service is True
        assert identity.id == "service"

    def test_valid_supabase_jwt_returns_real_identity(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_user = MagicMock()
        fake_user.id = "user-tefa"
        fake_user.email = "tefa@example.com"
        fake_response = MagicMock()
        fake_response.user = fake_user
        fake_client.auth.get_user.return_value = fake_response

        identity = get_current_user(credentials=_creds("real-jwt"))
        assert identity.is_service is False
        assert identity.id == "user-tefa"
        assert identity.email == "tefa@example.com"

    def test_postgrest_auth_restored_after_success(
        self, fake_client: FakeSupabaseClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The whole point of the finally block: postgrest.auth must be
        # called with the service key even on success path.
        monkeypatch.setattr(
            security_module.settings, "supabase_key", "service-role-key"
        )
        fake_user = MagicMock()
        fake_user.id = "user-tefa"
        fake_user.email = "tefa@example.com"
        fake_response = MagicMock()
        fake_response.user = fake_user
        fake_client.auth.get_user.return_value = fake_response

        get_current_user(credentials=_creds("real-jwt"))
        fake_client.postgrest.auth.assert_called_with("service-role-key")

    def test_postgrest_auth_restored_after_failure(
        self, fake_client: FakeSupabaseClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            security_module.settings, "supabase_key", "service-role-key"
        )
        fake_client.auth.get_user.side_effect = RuntimeError("boom")

        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=_creds("bad-jwt"))
        assert exc.value.status_code == 401
        fake_client.postgrest.auth.assert_called_with("service-role-key")

    def test_get_user_returns_none_user_raises_401(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # Supabase reports the JWT is invalid by returning user=None.
        fake_response = MagicMock()
        fake_response.user = None
        fake_client.auth.get_user.return_value = fake_response
        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=_creds("expired-jwt"))
        assert exc.value.status_code == 401
