"""Unit tests for auth.service.setup_account_password — the patient
account activation flow that broke at demo time.

Demo-day bug: setup_account_password called supabase_client.auth.sign_up
without restoring the service-role postgrest bearer in a finally block.
sign_up mutates the bearer to the newly-created patient's JWT, which
made the subsequent profile-link UPDATE and token-burn UPDATE run under
the patient's identity (subject to RLS) instead of service-role. The
RLS-blocked UPDATEs silently failed (bare except), so:
- the profile was never linked to auth_user_id → patient's NEXT login
  bootstrapped with no profile
- the token was never burned → could be reused or shown as fresh

These tests prevent that regression by:
1. asserting postgrest.auth(service_key) is called after sign_up
   (success path AND error path)
2. asserting the profile row ends up with the new auth_user_id
3. asserting the token row ends up with used_at set
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.modules.auth import service as auth_service
from src.modules.auth.schemas import SetupPasswordRequest
from tests._fakes import FakeSupabaseClient


FUTURE = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    client = FakeSupabaseClient()
    client.store.seed(
        "profiles",
        [
            {"id": 501, "full_name": "Tefa", "role": "patient", "auth_user_id": None},
        ],
    )
    client.store.seed(
        "account_setup_tokens",
        [
            {
                "id": 1,
                "token": "GOODTOKEN",
                "patient_id": 501,
                "email": "tefa@example.com",
                "expires_at": FUTURE,
                "used_at": None,
            }
        ],
    )
    monkeypatch.setattr(auth_service, "supabase_client", client)
    return client


def _fake_session() -> SimpleNamespace:
    return SimpleNamespace(
        access_token="acc",
        refresh_token="ref",
        expires_in=3600,
    )


def _fake_user(user_id: str = "auth-uuid-123") -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="tefa@example.com",
        user_metadata={"full_name": "Tefa", "role": "patient"},
    )


class TestSetupAccountPasswordHappyPath:
    def test_returns_session_and_links_profile(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.auth.set_sign_up_response(
            SimpleNamespace(user=_fake_user("auth-uuid-123"), session=_fake_session())
        )

        result = auth_service.setup_account_password(
            SetupPasswordRequest(token="GOODTOKEN", password="hunter22!")
        )

        assert result.access_token == "acc"
        # The profile is now linked — this is what the demo-day bug broke.
        profile = fake_client.store.rows("profiles")[0]
        assert profile["auth_user_id"] == "auth-uuid-123"
        # And the token is burned.
        token_row = fake_client.store.rows("account_setup_tokens")[0]
        assert token_row["used_at"] is not None

    def test_postgrest_auth_restored_after_sign_up(
        self,
        fake_client: FakeSupabaseClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Spy on restore_service_bearer — that's the real mechanism that
        # mutates the postgrest singleton's Authorization header in
        # supabase-py 2.x (postgrest.auth() does not, see
        # core/database.py docstring).
        spy = MagicMock()
        monkeypatch.setattr(auth_service, "restore_service_bearer", spy)
        fake_client.auth.set_sign_up_response(
            SimpleNamespace(user=_fake_user(), session=_fake_session())
        )

        auth_service.setup_account_password(
            SetupPasswordRequest(token="GOODTOKEN", password="hunter22!")
        )

        spy.assert_called()

    def test_postgrest_auth_restored_even_on_sign_up_error(
        self,
        fake_client: FakeSupabaseClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spy = MagicMock()
        monkeypatch.setattr(auth_service, "restore_service_bearer", spy)
        fake_client.auth.set_sign_up_error(RuntimeError("email already taken"))

        with pytest.raises(HTTPException) as exc:
            auth_service.setup_account_password(
                SetupPasswordRequest(token="GOODTOKEN", password="hunter22!")
            )
        assert exc.value.status_code == 400
        # Even when sign_up fails, the bearer must be restored so the
        # *next* unrelated request isn't poisoned by the leftover JWT.
        spy.assert_called()


class TestSetupAccountPasswordRejections:
    def test_unknown_token_returns_404(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            auth_service.setup_account_password(
                SetupPasswordRequest(token="DOES-NOT-EXIST", password="hunter22!")
            )
        assert exc.value.status_code == 404

    def test_already_used_token_returns_400(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.rows("account_setup_tokens")[0]["used_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        with pytest.raises(HTTPException) as exc:
            auth_service.setup_account_password(
                SetupPasswordRequest(token="GOODTOKEN", password="hunter22!")
            )
        assert exc.value.status_code == 400

    def test_expired_token_returns_410(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        fake_client.store.rows("account_setup_tokens")[0]["expires_at"] = past
        with pytest.raises(HTTPException) as exc:
            auth_service.setup_account_password(
                SetupPasswordRequest(token="GOODTOKEN", password="hunter22!")
            )
        assert exc.value.status_code == 410
