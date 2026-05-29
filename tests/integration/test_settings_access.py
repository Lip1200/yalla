"""Integration test: PATCH /patients/{id}/settings/access persists each
flag independently (issue #53) and the cascading privacy switch."""

import pytest


@pytest.fixture(autouse=True)
def seed_patient(fake_store) -> None:
    fake_store.seed(
        "profiles",
        [
            {
                "id": 108,
                "full_name": "Tefa",
                "role": "patient",
                "primary_goal": "Marcher",
                "age": None,
                "privacy_level": "Partage sélectif",
                "weekly_activity_minutes": 0,
                "challenge_completion_rate": 0,
                "activity_completion_rate": 0,
                "has_app_access": True,
                "last_check_in": None,
                "status": None,
                "share_activity": True,
                "share_challenges": True,
                "share_restaurants": True,
            },
        ],
    )


class TestAccessFlags:
    def test_get_settings_reflects_seeded_defaults(
        self, client, auth_headers
    ) -> None:
        r = client.get("/api/patients/108/settings", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["share_activity"] is True
        assert body["share_challenges"] is True
        assert body["share_restaurants"] is True

    def test_patch_one_flag_only(self, client, auth_headers) -> None:
        r = client.patch(
            "/api/patients/108/settings/access",
            json={"share_activity": False},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["share_activity"] is False
        # The others stay True.
        assert body["share_challenges"] is True
        assert body["share_restaurants"] is True

    def test_patch_multiple_flags(self, client, auth_headers) -> None:
        client.patch(
            "/api/patients/108/settings/access",
            json={"share_activity": False, "share_restaurants": False},
            headers=auth_headers,
        )
        r = client.get("/api/patients/108/settings", headers=auth_headers)
        body = r.json()
        assert body["share_activity"] is False
        assert body["share_challenges"] is True
        assert body["share_restaurants"] is False

    def test_omitted_field_unchanged(self, client, auth_headers) -> None:
        # First flip share_activity to false.
        client.patch(
            "/api/patients/108/settings/access",
            json={"share_activity": False},
            headers=auth_headers,
        )
        # Then PATCH with only share_challenges — share_activity must
        # stay False (not reset to default True).
        client.patch(
            "/api/patients/108/settings/access",
            json={"share_challenges": False},
            headers=auth_headers,
        )
        r = client.get("/api/patients/108/settings", headers=auth_headers)
        body = r.json()
        assert body["share_activity"] is False
        assert body["share_challenges"] is False


class TestPrivacyLevelEndpoint:
    def test_patch_privacy_level(self, client, auth_headers) -> None:
        r = client.patch(
            "/api/patients/108/settings/privacy",
            json={"privacy_level": "Données privées"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["profile"]["privacy_level"] == "Données privées"
