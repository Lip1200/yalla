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
    original = db.supabase_client.postgrest.session.headers.get("Authorization")
    yield
    if original is not None:
        db.supabase_client.postgrest.session.headers["Authorization"] = original


class TestRestoreServiceBearer:
    def test_overwrites_a_jwt_bearer_back_to_the_service_key(self) -> None:
        # Simulate what sign_up / sign_in_with_password / get_user do:
        # poison the bearer with a fake JWT.
        db.supabase_client.postgrest.session.headers["Authorization"] = (
            "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6Im_FAKE_JWT_FOR_TEST"
        )

        db.restore_service_bearer()

        assert (
            db.supabase_client.postgrest.session.headers["Authorization"]
            == f"Bearer {settings.supabase_key}"
        )

    def test_idempotent_when_already_service_key(self) -> None:
        db.supabase_client.postgrest.session.headers["Authorization"] = (
            f"Bearer {settings.supabase_key}"
        )

        db.restore_service_bearer()

        assert (
            db.supabase_client.postgrest.session.headers["Authorization"]
            == f"Bearer {settings.supabase_key}"
        )

    def test_does_not_rely_on_postgrest_auth_method(self) -> None:
        # Regression guard: postgrest.auth() in supabase-py 2.x returns a
        # NEW SyncPostgrestClient instance and does NOT mutate the
        # singleton's headers — proven by direct comparison. If we ever
        # try to "simplify" restore_service_bearer back to using
        # postgrest.auth(), this test fails.
        db.supabase_client.postgrest.session.headers["Authorization"] = (
            "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6Im_FAKE_JWT_FOR_TEST"
        )
        before = db.supabase_client.postgrest.session.headers["Authorization"]

        # Call the method that LOOKS right but isn't.
        db.supabase_client.postgrest.auth(settings.supabase_key)

        after = db.supabase_client.postgrest.session.headers["Authorization"]
        assert before == after, (
            "postgrest.auth(token) DID mutate the singleton — "
            "restore_service_bearer is no longer necessary, you can "
            "delete it and switch all call sites back."
        )
