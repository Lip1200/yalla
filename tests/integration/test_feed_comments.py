"""Integration tests for the feed comments endpoints (#TODO).

Exercises the full path: router → service → in-memory supabase, with
service-token auth. The "MOCK button fix" branch wired the patient-app
"Commenter" composer to POST /api/social/feed/{post_id}/comments — these
tests prevent that wiring from silently regressing.
"""

import pytest

from tests._fakes import FakeStore


@pytest.fixture(autouse=True)
def seed(fake_store: FakeStore) -> None:
    fake_store.seed(
        "profiles",
        [
            {"id": 101, "full_name": "Karim", "role": "patient"},
            {"id": 102, "full_name": "Amina", "role": "expert_patient"},
        ],
    )
    fake_store.seed(
        "feed_posts",
        [
            {
                "id": 1,
                "author_id": 101,
                "author_name": "Karim",
                "author_role": "patient",
                "type": "post",
                "content": "Hello",
                "achievement_label": None,
                "likes": 0,
                "comments_count": 0,
                "created_at": "2026-05-29T10:00:00+00:00",
            },
        ],
    )
    fake_store.set_rows("feed_post_comments", [])


class TestFeedComments:
    def test_post_then_get_roundtrip(self, client, auth_headers) -> None:
        # Service token requires explicit user_id query param.
        r = client.post(
            "/api/social/feed/1/comments?user_id=102",
            json={"content": "Bravo Karim !"},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        created = r.json()
        assert created["post_id"] == 1
        assert created["author_id"] == 102
        assert created["author_name"] == "Amina"
        assert created["content"] == "Bravo Karim !"

        listing = client.get(
            "/api/social/feed/1/comments", headers=auth_headers
        )
        assert listing.status_code == 200
        assert [c["content"] for c in listing.json()] == ["Bravo Karim !"]

    def test_comments_count_is_bumped_on_feed_listing(
        self, client, auth_headers
    ) -> None:
        # Initial count is 0.
        feed = client.get("/api/social/feed", headers=auth_headers).json()
        assert next(p for p in feed if p["id"] == 1)["comments_count"] == 0

        client.post(
            "/api/social/feed/1/comments?user_id=102",
            json={"content": "1"},
            headers=auth_headers,
        )
        client.post(
            "/api/social/feed/1/comments?user_id=101",
            json={"content": "2"},
            headers=auth_headers,
        )

        feed = client.get("/api/social/feed", headers=auth_headers).json()
        assert next(p for p in feed if p["id"] == 1)["comments_count"] == 2

    def test_missing_content_rejected_by_pydantic(
        self, client, auth_headers
    ) -> None:
        r = client.post(
            "/api/social/feed/1/comments?user_id=102",
            json={"content": ""},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_missing_post_returns_404(self, client, auth_headers) -> None:
        r = client.post(
            "/api/social/feed/999/comments?user_id=102",
            json={"content": "hi"},
            headers=auth_headers,
        )
        assert r.status_code == 404
