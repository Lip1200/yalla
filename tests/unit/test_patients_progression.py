"""Unit tests for _fetch_active_challenges_for_patient — the helper
that the patient-app's 'Mes défis' relies on. Key invariants:
- Empty patient_challenges → falls back to seeded demo dict
- Maps the *assignment* id to the legacy Challenge.id (not the
  template's id) so joinedChallengeIds in the patient-app can match
- Skips orphan rows (template deleted)
"""

from datetime import date

import pytest

from src.modules.patients import service as patients_service
from tests._fakes import FakeSupabaseClient


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    client = FakeSupabaseClient()
    monkeypatch.setattr(patients_service, "supabase_client", client)
    return client


class TestFetchActiveChallengesForPatient:
    def test_empty_falls_back_to_seeded_dict_for_demo_patient(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        result = patients_service._fetch_active_challenges_for_patient(101)
        # Patient 101 has seeded Karim challenges.
        assert len(result) >= 1

    def test_empty_returns_empty_for_non_demo_patient(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        assert patients_service._fetch_active_challenges_for_patient(999) == []

    def test_maps_assignment_id_to_challenge_id(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # The patient-app tracks joinedChallengeIds by assignment id.
        # This is critical — the test name says it all.
        fake_client.store.seed(
            "patient_challenges",
            [
                {
                    "id": 555,
                    "patient_id": 108,
                    "challenge_id": 1,
                    "progress": 30,
                    "due_on": "2026-05-30",
                    "status": "active",
                    "started_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        fake_client.store.seed(
            "challenges",
            [
                {
                    "id": 1,
                    "title": "20 min marche",
                    "description": "Marcher 20 min",
                    "category": "activity",
                },
            ],
        )
        result = patients_service._fetch_active_challenges_for_patient(108)
        assert len(result) == 1
        assert result[0].id == 555  # assignment id, not challenge_id=1
        assert result[0].title == "20 min marche"

    def test_skips_orphan_assignments(self, fake_client: FakeSupabaseClient) -> None:
        # patient_challenges row references a deleted challenge.
        fake_client.store.seed(
            "patient_challenges",
            [
                {
                    "id": 1,
                    "patient_id": 108,
                    "challenge_id": 1,
                    "progress": 0,
                    "due_on": "2026-05-30",
                    "status": "active",
                    "started_at": "2026-05-01T10:00:00+00:00",
                },
                {
                    "id": 2,
                    "patient_id": 108,
                    "challenge_id": 99,  # orphan
                    "progress": 0,
                    "due_on": "2026-05-30",
                    "status": "active",
                    "started_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        fake_client.store.seed(
            "challenges",
            [{"id": 1, "title": "Marche", "description": "", "category": "activity"}],
        )
        result = patients_service._fetch_active_challenges_for_patient(108)
        assert len(result) == 1
        assert result[0].id == 1

    def test_due_on_iso_parsed(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_challenges",
            [
                {
                    "id": 1,
                    "patient_id": 108,
                    "challenge_id": 1,
                    "progress": 0,
                    "due_on": "2026-06-15",
                    "status": "active",
                    "started_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        fake_client.store.seed(
            "challenges",
            [{"id": 1, "title": "X", "description": "", "category": "activity"}],
        )
        result = patients_service._fetch_active_challenges_for_patient(108)
        assert result[0].due_on == date(2026, 6, 15)

    def test_progress_defaulted_when_missing(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "patient_challenges",
            [
                {
                    "id": 1,
                    "patient_id": 108,
                    "challenge_id": 1,
                    "progress": None,
                    "due_on": "2026-06-15",
                    "status": "active",
                    "started_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        fake_client.store.seed(
            "challenges",
            [{"id": 1, "title": "X", "description": "", "category": "activity"}],
        )
        result = patients_service._fetch_active_challenges_for_patient(108)
        assert result[0].progress == 0

    def test_category_defaulted_to_empty_string(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "patient_challenges",
            [
                {
                    "id": 1,
                    "patient_id": 108,
                    "challenge_id": 1,
                    "progress": 50,
                    "due_on": "2026-06-15",
                    "status": "active",
                    "started_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        fake_client.store.seed(
            "challenges",
            [{"id": 1, "title": "X", "description": "", "category": None}],
        )
        result = patients_service._fetch_active_challenges_for_patient(108)
        assert result[0].category == ""
