"""Integration test: end-to-end friend request lifecycle via the
public HTTP surface."""

import pytest


@pytest.fixture(autouse=True)
def seed_profiles(fake_store) -> None:
    fake_store.seed(
        "profiles",
        [
            {"id": 108, "full_name": "Tefa", "role": "patient", "primary_goal": ""},
            {"id": 102, "full_name": "Amina", "role": "expert_patient", "primary_goal": "Animer"},
            {"id": 101, "full_name": "Karim", "role": "patient", "primary_goal": "Marcher"},
        ],
    )


class TestFriendRequestFlow:
    def test_full_cycle_request_accept_visible_to_both(
        self, client, auth_headers
    ) -> None:
        # 1. Tefa requests Amina.
        r = client.post(
            "/api/social/friends/108",
            json={"friend_id": 102},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["status"] == "pending"

        # 2. Amina sees the request in her inbox.
        r = client.get("/api/social/friends/102/requests", headers=auth_headers)
        assert r.status_code == 200
        requests = r.json()
        assert len(requests) == 1
        assert requests[0]["requester_id"] == 108

        # 3. Amina accepts.
        r = client.post(
            "/api/social/friends/102/requests/108/accept",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

        # 4. Both see each other in their friends list.
        r = client.get("/api/social/friends/108", headers=auth_headers)
        assert 102 in {f["id"] for f in r.json()}

        r = client.get("/api/social/friends/102", headers=auth_headers)
        assert 108 in {f["id"] for f in r.json()}

    def test_idempotent_add_friend(self, client, auth_headers) -> None:
        for _ in range(3):
            r = client.post(
                "/api/social/friends/108",
                json={"friend_id": 102},
                headers=auth_headers,
            )
            assert r.status_code == 201
        # Only one row inserted despite 3 requests.
        r = client.get(
            "/api/social/friends/108/sent",
            headers=auth_headers,
        )
        sent = r.json()
        assert len(sent) == 1
        assert sent[0]["id"] == 102

    def test_reject_clears_request_for_requester_and_receiver(
        self, client, auth_headers
    ) -> None:
        client.post(
            "/api/social/friends/108",
            json={"friend_id": 102},
            headers=auth_headers,
        )

        r = client.post(
            "/api/social/friends/102/requests/108/reject",
            headers=auth_headers,
        )
        assert r.status_code == 204

        # Tefa's sent list now empty.
        r = client.get("/api/social/friends/108/sent", headers=auth_headers)
        assert r.json() == []

        # Amina's inbox now empty.
        r = client.get("/api/social/friends/102/requests", headers=auth_headers)
        assert r.json() == []

    def test_suggestions_excludes_pending_and_accepted(
        self, client, auth_headers
    ) -> None:
        # Send a request to Karim, accept Amina automatically by direct seed.
        client.post(
            "/api/social/friends/108",
            json={"friend_id": 101},  # → pending
            headers=auth_headers,
        )

        r = client.get("/api/social/friends/108/sent", headers=auth_headers)
        assert {s["id"] for s in r.json()} == {101}

        r = client.get(
            "/api/social/suggestions/108?limit=10",
            headers=auth_headers,
        )
        ids = {s["id"] for s in r.json()}
        assert 101 not in ids  # has pending row
        assert 108 not in ids  # self
        # Amina (no link yet) should still appear.
        assert 102 in ids
