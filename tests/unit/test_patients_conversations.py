"""Unit tests for the conversation reader in patients/service.py.

Verifies the unread count rules (skip own messages, respect
last_read_at), the contact resolution (other-participant lookup), and
the seeded fallback for demo patients 101/102.
"""

import pytest

from src.modules.patients import service as patients_service
from src.modules.patients.schemas import AppRole
from tests._fakes import FakeSupabaseClient


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    client = FakeSupabaseClient()
    # Two profiles for the contact-resolution step.
    client.store.seed(
        "profiles",
        [
            {"id": 108, "full_name": "Tefa", "role": "patient"},
            {"id": 102, "full_name": "Amina", "role": "expert_patient"},
            {"id": 101, "full_name": "Karim", "role": "patient"},
        ],
    )
    monkeypatch.setattr(patients_service, "supabase_client", client)
    return client


class TestFetchConversationsForPatient:
    def test_empty_falls_back_to_seeded_dict_for_demo_patient(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # Patient 101 has seeded conversations in the in-memory dict.
        result = patients_service._fetch_conversations_for_patient(101)
        assert len(result) >= 1
        assert any(c.contact_name == "Amina Saidi" for c in result)

    def test_empty_returns_empty_for_non_demo_patient(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        # No participant rows AND no seeded fallback → []
        result = patients_service._fetch_conversations_for_patient(999)
        assert result == []

    def test_returns_conv_with_other_participant_as_contact(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "conversation_participants",
            [
                {"conversation_id": 1, "user_id": 108, "last_read_at": None},
                {"conversation_id": 1, "user_id": 102, "last_read_at": None},
            ],
        )
        fake_client.store.seed(
            "messages",
            [
                {
                    "conversation_id": 1,
                    "sender_id": 102,
                    "content": "Salut Tefa",
                    "sent_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        result = patients_service._fetch_conversations_for_patient(108)
        assert len(result) == 1
        assert result[0].contact_name == "Amina"
        assert result[0].contact_role == AppRole.EXPERT_PATIENT
        assert result[0].last_message == "Salut Tefa"
        assert result[0].unread_count == 1

    def test_own_messages_not_counted_as_unread(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "conversation_participants",
            [
                {"conversation_id": 1, "user_id": 108, "last_read_at": None},
                {"conversation_id": 1, "user_id": 102, "last_read_at": None},
            ],
        )
        fake_client.store.seed(
            "messages",
            [
                {
                    "conversation_id": 1,
                    "sender_id": 108,
                    "content": "Mine",
                    "sent_at": "2026-05-01T09:00:00+00:00",
                },
                {
                    "conversation_id": 1,
                    "sender_id": 102,
                    "content": "Reply",
                    "sent_at": "2026-05-01T10:00:00+00:00",
                },
            ],
        )
        result = patients_service._fetch_conversations_for_patient(108)
        # 1 message from Amina, our own message ignored.
        assert result[0].unread_count == 1

    def test_last_read_at_filters_older_messages(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "conversation_participants",
            [
                {
                    "conversation_id": 1,
                    "user_id": 108,
                    "last_read_at": "2026-05-01T10:00:00+00:00",
                },
                {"conversation_id": 1, "user_id": 102, "last_read_at": None},
            ],
        )
        fake_client.store.seed(
            "messages",
            [
                {
                    "conversation_id": 1,
                    "sender_id": 102,
                    "content": "Old (already read)",
                    "sent_at": "2026-04-29T08:00:00+00:00",
                },
                {
                    "conversation_id": 1,
                    "sender_id": 102,
                    "content": "Fresh",
                    "sent_at": "2026-05-02T11:00:00+00:00",
                },
            ],
        )
        result = patients_service._fetch_conversations_for_patient(108)
        # Only the post-read message counts.
        assert result[0].unread_count == 1
        assert result[0].last_message == "Fresh"

    def test_conv_without_messages_is_skipped(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "conversation_participants",
            [
                {"conversation_id": 1, "user_id": 108, "last_read_at": None},
                {"conversation_id": 1, "user_id": 102, "last_read_at": None},
            ],
        )
        # No messages seeded → conv is dropped from the output.
        result = patients_service._fetch_conversations_for_patient(108)
        assert result == []

    def test_sorted_by_updated_at_desc(
        self, fake_client: FakeSupabaseClient
    ) -> None:
        fake_client.store.seed(
            "conversation_participants",
            [
                {"conversation_id": 1, "user_id": 108, "last_read_at": None},
                {"conversation_id": 1, "user_id": 102, "last_read_at": None},
                {"conversation_id": 2, "user_id": 108, "last_read_at": None},
                {"conversation_id": 2, "user_id": 101, "last_read_at": None},
            ],
        )
        fake_client.store.seed(
            "messages",
            [
                {
                    "conversation_id": 1,
                    "sender_id": 102,
                    "content": "Old",
                    "sent_at": "2026-04-20T09:00:00+00:00",
                },
                {
                    "conversation_id": 2,
                    "sender_id": 101,
                    "content": "Recent",
                    "sent_at": "2026-05-10T15:00:00+00:00",
                },
            ],
        )
        result = patients_service._fetch_conversations_for_patient(108)
        # Most recent first.
        assert [c.id for c in result] == [2, 1]
