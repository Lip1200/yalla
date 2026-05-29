"""Unit tests for assign_to_patient — both the authorization branches
(#41) and the idempotency guard introduced after duplicate-tap
incidents."""

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from src.core.security import AuthIdentity
from src.modules.challenges import service as challenges_service
from src.modules.challenges.schemas import PatientChallengeAssign
from tests._fakes import FakeSupabaseClient


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    client = FakeSupabaseClient()
    client.store.seed(
        "profiles",
        [
            {"id": 108, "full_name": "Tefa", "role": "patient", "auth_user_id": "user-tefa"},
            {"id": 107, "full_name": "Dr. Filipe", "role": "doctor", "auth_user_id": "user-doctor"},
            {"id": 102, "full_name": "Amina", "role": "expert_patient", "auth_user_id": "user-amina"},
        ],
    )
    client.store.seed(
        "challenges",
        [
            {
                "id": 1,
                "title": "20 min marche",
                "description": "Marcher 20 min",
                "category": "activity",
                "target_value": 20,
                "target_unit": "minutes",
                "duration_days": 7,
                "difficulty": "easy",
                "is_template": True,
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        ],
    )
    monkeypatch.setattr(challenges_service, "supabase_client", client)
    # Also patch the security module's supabase_client so
    # get_profile_for_identity sees the same fake.
    from src.core import security
    monkeypatch.setattr(security, "supabase_client", client)
    return client


def _payload(patient_id: int = 108, challenge_id: int = 1) -> PatientChallengeAssign:
    return PatientChallengeAssign(patient_id=patient_id, challenge_id=challenge_id)


class TestAssignToPatientIdempotency:
    def test_first_call_inserts_row(self, fake_client: FakeSupabaseClient) -> None:
        challenges_service.assign_to_patient(_payload(), identity=None)
        rows = fake_client.store.rows("patient_challenges")
        assert len(rows) == 1
        assert rows[0]["patient_id"] == 108
        assert rows[0]["challenge_id"] == 1
        assert rows[0]["status"] == "active"

    def test_duplicate_call_returns_existing_without_insert(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        challenges_service.assign_to_patient(_payload(), identity=None)
        challenges_service.assign_to_patient(_payload(), identity=None)
        # Idempotent — still one row.
        assert len(fake_client.store.rows("patient_challenges")) == 1

    def test_due_on_defaults_to_started_plus_duration(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        challenges_service.assign_to_patient(_payload(), identity=None)
        rows = fake_client.store.rows("patient_challenges")
        due = date.fromisoformat(rows[0]["due_on"])
        # duration_days=7 → due_on ≈ today+7. Allow 1 day slack for
        # clock weirdness across test runs.
        delta = (due - date.today()).days
        assert 6 <= delta <= 8


class TestAssignToPatientAuthorization:
    def test_service_token_can_assign_to_anyone(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="service", is_service=True)
        # patient_id=108 (Tefa), called via the service token from CI.
        challenges_service.assign_to_patient(_payload(108), identity=identity)
        assert len(fake_client.store.rows("patient_challenges")) == 1

    def test_doctor_can_assign_to_other_patient(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="user-doctor", is_service=False)
        challenges_service.assign_to_patient(_payload(108), identity=identity)
        assert len(fake_client.store.rows("patient_challenges")) == 1

    def test_expert_patient_can_assign_to_other_patient(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="user-amina", is_service=False)
        challenges_service.assign_to_patient(_payload(108), identity=identity)
        assert len(fake_client.store.rows("patient_challenges")) == 1

    def test_patient_self_assignment_allowed(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        identity = AuthIdentity(id="user-tefa", is_service=False)
        challenges_service.assign_to_patient(_payload(108), identity=identity)
        assert len(fake_client.store.rows("patient_challenges")) == 1

    def test_patient_cross_assignment_forbidden(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # Tefa is a regular patient → cannot assign to Amina.
        identity = AuthIdentity(id="user-tefa", is_service=False)
        with pytest.raises(HTTPException) as exc:
            challenges_service.assign_to_patient(_payload(102), identity=identity)
        assert exc.value.status_code == 403

    def test_identity_none_bypasses_auth_check(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # Internal callers (tests, scripts) pass identity=None.
        challenges_service.assign_to_patient(_payload(102), identity=None)
        assert len(fake_client.store.rows("patient_challenges")) == 1


class TestAssignToPatientErrors:
    def test_404_when_patient_missing(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            challenges_service.assign_to_patient(
                _payload(patient_id=9999), identity=None
            )
        assert exc.value.status_code == 404

    def test_404_when_challenge_missing(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            challenges_service.assign_to_patient(
                _payload(challenge_id=9999), identity=None
            )
        assert exc.value.status_code == 404
