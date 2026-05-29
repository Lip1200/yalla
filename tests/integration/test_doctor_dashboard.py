"""Integration test for the doctor dashboard endpoint — combines the
patient filter (#fixme excluded doctors) and the privacy mask
cascading through _to_summary."""

import pytest


@pytest.fixture(autouse=True)
def seed(fake_store) -> None:
    base = {
        "primary_goal": "x",
        "age": 45,
        "has_app_access": True,
        "activity_completion_rate": 50,
        "challenge_completion_rate": 60,
        "weekly_activity_minutes": 100,
        "last_check_in": "2026-05-01",
        "status": "En progrès",
        "share_activity": True,
        "share_challenges": True,
        "share_restaurants": True,
    }
    fake_store.seed(
        "profiles",
        [
            {**base, "id": 107, "full_name": "Dr. Filipe", "role": "doctor", "privacy_level": "Partage sélectif"},
            {**base, "id": 108, "full_name": "Tefa", "role": "patient", "privacy_level": "Partage sélectif"},
            {**base, "id": 102, "full_name": "Amina", "role": "expert_patient", "privacy_level": "Partage sélectif"},
            {**base, "id": 999, "full_name": "Private Patient", "role": "patient", "privacy_level": "Données privées"},
        ],
    )


class TestDoctorDashboard:
    def test_returns_dashboard_shape(self, client, auth_headers) -> None:
        r = client.get("/api/doctors/107/dashboard", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "doctor" in body
        assert "patients" in body
        assert "total_patients" in body

    def test_doctor_profiles_excluded_from_patient_list(
        self, client, auth_headers
    ) -> None:
        r = client.get("/api/doctors/107/dashboard", headers=auth_headers)
        ids = {p["id"] for p in r.json()["patients"]}
        assert 107 not in ids  # The doctor herself isn't a patient.

    def test_expert_patient_included(self, client, auth_headers) -> None:
        r = client.get("/api/doctors/107/dashboard", headers=auth_headers)
        ids = {p["id"] for p in r.json()["patients"]}
        assert 102 in ids

    def test_private_patient_progress_masked(self, client, auth_headers) -> None:
        r = client.get("/api/doctors/107/dashboard", headers=auth_headers)
        patients = {p["id"]: p for p in r.json()["patients"]}
        # Tefa: shared → real values
        assert patients[108]["progress"]["weekly_activity_minutes"] == 100
        # 999 (Données privées) → masked
        assert patients[999]["progress"]["weekly_activity_minutes"] == 0
        assert patients[999]["progress"]["status"] == "Mode privé"
