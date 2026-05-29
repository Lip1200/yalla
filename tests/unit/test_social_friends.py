"""Unit tests for the friendship state machine in social/service.py.

We mock supabase_client at the module level with our FakeSupabaseClient
so the test reads/writes against an in-memory store. This catches
regressions in:
- pending → accepted transition
- both-direction lookups in list_friends
- exclusion of already-linked profiles in list_friend_suggestions
- idempotency on add_friend
"""

import pytest
from fastapi import HTTPException

from src.modules.social import service as social_service
from tests._fakes import FakeStore, FakeSupabaseClient


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    """Replace social_service.supabase_client with a fresh fake one,
    pre-seeded with a tiny patient roster."""
    client = FakeSupabaseClient()
    client.store.seed(
        "profiles",
        [
            {"id": 108, "full_name": "Tefa", "role": "patient", "primary_goal": "Marcher"},
            {"id": 102, "full_name": "Amina", "role": "expert_patient", "primary_goal": "Animer"},
            {"id": 101, "full_name": "Karim", "role": "patient", "primary_goal": "Stabiliser"},
            {"id": 103, "full_name": "Youssef", "role": "patient", "primary_goal": "Moins de sucre"},
            {"id": 107, "full_name": "Dr. Filipe", "role": "doctor", "primary_goal": ""},
        ],
    )
    monkeypatch.setattr(social_service, "supabase_client", client)
    return client


class TestAddFriend:
    def test_creates_pending_row(self, fake_client: FakeSupabaseClient) -> None:
        result = social_service.add_friend(108, 102)
        assert result.id == 102
        assert result.status == "pending"
        rows = fake_client.store.rows("patient_friends")
        assert len(rows) == 1
        assert rows[0]["patient_id"] == 108
        assert rows[0]["friend_id"] == 102
        assert rows[0]["status"] == "pending"

    def test_idempotent_on_existing_pending(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "pending"}],
        )
        result = social_service.add_friend(108, 102)
        assert result.status == "pending"
        # No duplicate inserted.
        assert len(fake_client.store.rows("patient_friends")) == 1

    def test_returns_existing_accepted_row(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "accepted"}],
        )
        result = social_service.add_friend(108, 102)
        assert result.status == "accepted"
        assert len(fake_client.store.rows("patient_friends")) == 1

    def test_returns_reverse_row_when_other_already_added_us(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 102, "friend_id": 108, "status": "pending"}],
        )
        result = social_service.add_friend(108, 102)
        # The function returns the existing row's status without
        # inserting a duplicate in the reverse direction.
        assert result.status == "pending"
        assert len(fake_client.store.rows("patient_friends")) == 1

    def test_self_add_rejected(self, fake_client: FakeSupabaseClient) -> None:
        with pytest.raises(HTTPException) as exc:
            social_service.add_friend(108, 108)
        assert exc.value.status_code == 400

    def test_unknown_friend_rejected(self, fake_client: FakeSupabaseClient) -> None:
        with pytest.raises(HTTPException) as exc:
            social_service.add_friend(108, 9999)
        assert exc.value.status_code == 404


class TestAcceptFriendRequest:
    def test_flips_status_to_accepted(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "pending"}],
        )
        result = social_service.accept_friend_request(receiver_id=102, requester_id=108)
        assert result.id == 108
        assert result.status == "accepted"
        rows = fake_client.store.rows("patient_friends")
        assert rows[0]["status"] == "accepted"

    def test_404_when_no_pending_row(self, fake_client: FakeSupabaseClient) -> None:
        with pytest.raises(HTTPException) as exc:
            social_service.accept_friend_request(receiver_id=102, requester_id=108)
        assert exc.value.status_code == 404

    def test_does_not_accept_already_accepted(self, fake_client: FakeSupabaseClient) -> None:
        """The update filter is `status=pending` — an already-accepted
        row should still not flip to accepted (no-op, 404)."""
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "accepted"}],
        )
        with pytest.raises(HTTPException) as exc:
            social_service.accept_friend_request(receiver_id=102, requester_id=108)
        assert exc.value.status_code == 404


class TestRejectFriendRequest:
    def test_deletes_pending_row(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "pending"}],
        )
        social_service.reject_friend_request(receiver_id=102, requester_id=108)
        assert fake_client.store.rows("patient_friends") == []

    def test_noop_when_already_accepted(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "accepted"}],
        )
        social_service.reject_friend_request(receiver_id=102, requester_id=108)
        # The accepted row is left untouched.
        assert len(fake_client.store.rows("patient_friends")) == 1


class TestListFriends:
    def test_includes_both_directions_when_accepted(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 108, "friend_id": 102, "status": "accepted"},
                {"patient_id": 103, "friend_id": 108, "status": "accepted"},
            ],
        )
        friends = social_service.list_friends(108)
        ids = {f.id for f in friends}
        assert ids == {102, 103}

    def test_excludes_pending_rows(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 108, "friend_id": 102, "status": "accepted"},
                {"patient_id": 108, "friend_id": 101, "status": "pending"},
            ],
        )
        ids = {f.id for f in social_service.list_friends(108)}
        assert ids == {102}

    def test_empty_when_no_links(self, fake_client: FakeSupabaseClient) -> None:
        assert social_service.list_friends(108) == []

    def test_deduplicates_double_directional_link(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # Pathological: both rows exist for the same pair. List should
        # still surface each friend exactly once.
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 108, "friend_id": 102, "status": "accepted"},
                {"patient_id": 102, "friend_id": 108, "status": "accepted"},
            ],
        )
        friends = social_service.list_friends(108)
        ids = [f.id for f in friends]
        assert ids == [102]


class TestListFriendRequests:
    def test_returns_pending_received(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 102, "friend_id": 108, "status": "pending"},
                {"patient_id": 101, "friend_id": 108, "status": "pending"},
                {"patient_id": 103, "friend_id": 108, "status": "accepted"},
            ],
        )
        requests = social_service.list_friend_requests(108)
        assert {r.requester_id for r in requests} == {102, 101}

    def test_does_not_include_sent_requests(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "patient_friends",
            [{"patient_id": 108, "friend_id": 102, "status": "pending"}],
        )
        # 108 sent the request to 102. From 108's POV nothing was
        # received — list_friend_requests(108) should be empty.
        assert social_service.list_friend_requests(108) == []


class TestListSentFriendRequests:
    def test_returns_pending_sent(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 108, "friend_id": 102, "status": "pending"},
                {"patient_id": 108, "friend_id": 101, "status": "accepted"},
                {"patient_id": 108, "friend_id": 103, "status": "pending"},
            ],
        )
        sent = social_service.list_sent_friend_requests(108)
        assert {s.id for s in sent} == {102, 103}
        for s in sent:
            assert s.status == "pending"


class TestRemoveFriend:
    def test_clears_both_directional_rows(self, fake_client: FakeSupabaseClient) -> None:
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 108, "friend_id": 102, "status": "accepted"},
                {"patient_id": 102, "friend_id": 108, "status": "accepted"},
            ],
        )
        social_service.remove_friend(108, 102)
        assert fake_client.store.rows("patient_friends") == []


class TestListFriendSuggestions:
    def test_excludes_self(self, fake_client: FakeSupabaseClient) -> None:
        suggestions = social_service.list_friend_suggestions(108, limit=10)
        ids = {s.id for s in suggestions}
        assert 108 not in ids

    def test_excludes_doctors(self, fake_client: FakeSupabaseClient) -> None:
        suggestions = social_service.list_friend_suggestions(108, limit=10)
        ids = {s.id for s in suggestions}
        assert 107 not in ids  # Dr. Filipe

    def test_excludes_existing_links_either_direction(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "patient_friends",
            [
                {"patient_id": 108, "friend_id": 102, "status": "accepted"},
                {"patient_id": 101, "friend_id": 108, "status": "pending"},
            ],
        )
        suggestions = social_service.list_friend_suggestions(108, limit=10)
        ids = {s.id for s in suggestions}
        assert 102 not in ids  # accepted outbound
        assert 101 not in ids  # pending inbound
        assert 103 in ids  # untouched

    def test_respects_limit(self, fake_client: FakeSupabaseClient) -> None:
        suggestions = social_service.list_friend_suggestions(108, limit=1)
        assert len(suggestions) == 1
