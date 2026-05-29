"""Unit tests for restore_service_bearer.

This is the second-attempt fix for the patient-activation demo bug.
MR #47's `postgrest.auth(supabase_key)` call inside a `finally` block
looked correct but was a no-op in supabase-py 2.x: that method returns
a new SyncPostgrestClient with the auth set, but does NOT mutate the
shared singleton's `session.headers`. So after `auth.sign_up()`, the
postgrest singleton kept the new patient's JWT as the bearer, and the
follow-up profile-link UPDATE / token-burn UPDATE ran under that
patient's RLS (silently returning empty result sets — no profile link,
no token burn, login-loop on second connect).

restore_service_bearer fixes this by setting the Authorization header
directly on `supabase_client.postgrest.session.headers`, which IS what
supabase-py reads on every request.
"""

import pytest

from src.core import database as db
from src.core.config import settings


@pytest.fixture(autouse=True)
def reset_bearer():
    sess_orig = db.supabase_client.postgrest.session.headers.get("Authorization")
    pg_orig = db.supabase_client.postgrest.headers.get("Authorization")
    yield
    if sess_orig is not None:
        db.supabase_client.postgrest.session.headers["Authorization"] = sess_orig
    if pg_orig is not None:
        db.supabase_client.postgrest.headers["Authorization"] = pg_orig


FAKE_JWT = "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6Im_FAKE_JWT_FOR_TEST"


class TestRestoreServiceBearer:
    def test_overwrites_both_header_dicts_back_to_the_service_key(self) -> None:
        # Simulate what sign_up / sign_in_with_password / get_user do:
        # poison BOTH header stores with a fake JWT.
        db.supabase_client.postgrest.session.headers["Authorization"] = FAKE_JWT
        db.supabase_client.postgrest.headers["Authorization"] = FAKE_JWT

        db.restore_service_bearer()

        expected = f"Bearer {settings.supabase_key}"
        # Both must be restored — the builder chain reads
        # postgrest.headers, raw httpx reads session.headers. Missing
        # either one reintroduces the demo bug.
        assert (
            db.supabase_client.postgrest.session.headers["Authorization"]
            == expected
        )
        assert (
            db.supabase_client.postgrest.headers["Authorization"] == expected
        )

    def test_idempotent_when_already_service_key(self) -> None:
        expected = f"Bearer {settings.supabase_key}"
        db.supabase_client.postgrest.session.headers["Authorization"] = expected
        db.supabase_client.postgrest.headers["Authorization"] = expected

        db.restore_service_bearer()

        assert (
            db.supabase_client.postgrest.session.headers["Authorization"]
            == expected
        )
        assert (
            db.supabase_client.postgrest.headers["Authorization"] == expected
        )

    def test_postgrest_auth_method_does_not_reset_session_headers(
        self,
    ) -> None:
        # Regression guard for the supabase-py 2.x asymmetry:
        # `postgrest.auth(key)` resets postgrest.headers (the builder
        # chain reads from this dict) but leaves session.headers
        # untouched. Code paths that issue raw httpx requests via the
        # session would still send the stale JWT.
        #
        # Our restore writes BOTH dicts to cover both paths. If someone
        # "simplifies" the restore back to a single
        # `postgrest.auth(key)` call, this test fails — telling them
        # session.headers is still leaking the JWT.
        db.supabase_client.postgrest.session.headers["Authorization"] = FAKE_JWT
        db.supabase_client.postgrest.headers["Authorization"] = FAKE_JWT

        db.supabase_client.postgrest.auth(settings.supabase_key)

        # postgrest.headers IS restored by pg.auth() — that's fine.
        # The failure mode: session.headers stays at the JWT.
        assert (
            db.supabase_client.postgrest.session.headers["Authorization"]
            == FAKE_JWT
        ), (
            "postgrest.auth(token) DID reset session.headers — "
            "restore_service_bearer may now be safely simplified to a "
            "single postgrest.auth() call. Verify with a real sign_up "
            "+ raw httpx round-trip in prod before deleting."
        )
