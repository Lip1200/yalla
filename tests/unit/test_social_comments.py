"""Unit tests for the feed comments service.

Covers the new endpoints introduced for the patient-app "Commenter"
composer (POST /api/social/feed/{post_id}/comments + GET): persistence,
denormalized comments_count refresh, ordering, and 404s on missing
post/author.
"""

import pytest
from fastapi import HTTPException

from src.modules.social import service as social_service
from src.modules.social.schemas import FeedCommentCreate
from tests._fakes import FakeSupabaseClient


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    client = FakeSupabaseClient()
    client.store.seed(
        "profiles",
        [
            {"id": 101, "full_name": "Karim", "role": "patient"},
            {"id": 102, "full_name": "Amina", "role": "expert_patient"},
        ],
    )
    client.store.seed(
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
    client.store.set_rows("feed_post_comments", [])
    monkeypatch.setattr(social_service, "supabase_client", client)
    return client


class TestAddComment:
    def test_persists_comment_and_returns_author_name(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        comment = social_service.add_comment(
            post_id=1, author_id=102, payload=FeedCommentCreate(content="Bravo!")
        )
        assert comment.post_id == 1
        assert comment.author_id == 102
        assert comment.author_name == "Amina"
        assert comment.content == "Bravo!"
        assert fake_client.store.rows("feed_post_comments")[0]["content"] == "Bravo!"

    def test_bumps_denormalized_comments_count(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        assert fake_client.store.rows("feed_posts")[0]["comments_count"] == 0
        social_service.add_comment(1, 102, FeedCommentCreate(content="A"))
        social_service.add_comment(1, 101, FeedCommentCreate(content="B"))
        assert fake_client.store.rows("feed_posts")[0]["comments_count"] == 2

    def test_raises_404_when_post_missing(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            social_service.add_comment(999, 102, FeedCommentCreate(content="hi"))
        assert exc.value.status_code == 404

    def test_raises_404_when_author_missing(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            social_service.add_comment(1, 999, FeedCommentCreate(content="hi"))
        assert exc.value.status_code == 404


class TestListComments:
    def test_returns_empty_list_when_post_has_no_comments(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        assert social_service.list_comments(1) == []

    def test_returns_comments_oldest_first(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "feed_post_comments",
            [
                {
                    "id": 1,
                    "post_id": 1,
                    "author_id": 102,
                    "content": "second",
                    "created_at": "2026-05-29T11:00:00+00:00",
                },
                {
                    "id": 2,
                    "post_id": 1,
                    "author_id": 101,
                    "content": "first",
                    "created_at": "2026-05-29T10:30:00+00:00",
                },
            ],
        )
        comments = social_service.list_comments(1)
        assert [c.content for c in comments] == ["first", "second"]
        # The list path resolves author_name via _row_to_comment.
        assert comments[0].author_name == "Karim"
        assert comments[1].author_name == "Amina"

    def test_filters_by_post_id(self, fake_client: FakeSupabaseClient) -> None:
        # A comment on another post must not leak.
        fake_client.store.seed(
            "feed_posts",
            [
                *fake_client.store.rows("feed_posts"),
                {
                    "id": 2,
                    "author_id": 101,
                    "author_name": "Karim",
                    "author_role": "patient",
                    "type": "post",
                    "content": "Other",
                    "achievement_label": None,
                    "likes": 0,
                    "comments_count": 0,
                    "created_at": "2026-05-29T09:00:00+00:00",
                },
            ],
        )
        fake_client.store.seed(
            "feed_post_comments",
            [
                {
                    "id": 1,
                    "post_id": 1,
                    "author_id": 102,
                    "content": "for post 1",
                    "created_at": "2026-05-29T10:30:00+00:00",
                },
                {
                    "id": 2,
                    "post_id": 2,
                    "author_id": 102,
                    "content": "for post 2",
                    "created_at": "2026-05-29T10:31:00+00:00",
                },
            ],
        )
        result = social_service.list_comments(1)
        assert len(result) == 1
        assert result[0].content == "for post 1"

    def test_raises_404_when_post_missing(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            social_service.list_comments(999)
        assert exc.value.status_code == 404
