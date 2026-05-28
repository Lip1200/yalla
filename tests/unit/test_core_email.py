"""Unit tests for the transactional email sender.

The send_invitation_email function uses httpx.post against the Resend
REST API. We patch httpx at the module boundary so tests run offline
and assert on payload / headers shape.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.core import email as email_module


@pytest.fixture
def fake_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a non-empty API key so send_invitation_email runs through
    the real httpx call path."""
    monkeypatch.setattr(email_module.settings, "resend_api_key", "re_TESTKEY")
    monkeypatch.setattr(
        email_module.settings,
        "resend_from_email",
        "Yalla <onboarding@resend.dev>",
    )


class TestSendInvitationEmail:
    def test_skips_when_api_key_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(email_module.settings, "resend_api_key", "")
        with patch.object(email_module.httpx, "post") as mock_post:
            ok = email_module.send_invitation_email(
                to="patient@example.com",
                patient_name="Patient",
                invitation_url="https://yalla.example/setup?token=ABC",
            )
        assert ok is False
        mock_post.assert_not_called()

    def test_returns_true_on_resend_200(self, fake_settings: None) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = '{"id":"deadbeef"}'
        with patch.object(email_module.httpx, "post", return_value=response):
            ok = email_module.send_invitation_email(
                to="patient@example.com",
                patient_name="Patient",
                invitation_url="https://yalla.example/setup?token=ABC",
            )
        assert ok is True

    def test_returns_false_on_resend_400(self, fake_settings: None) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 403
        response.text = '{"message":"validation_error"}'
        with patch.object(email_module.httpx, "post", return_value=response):
            ok = email_module.send_invitation_email(
                to="other@example.com",
                patient_name="Patient",
                invitation_url="https://yalla.example/setup?token=ABC",
            )
        assert ok is False

    def test_returns_false_on_network_error(self, fake_settings: None) -> None:
        with patch.object(
            email_module.httpx,
            "post",
            side_effect=httpx.ConnectError("DNS failure"),
        ):
            ok = email_module.send_invitation_email(
                to="patient@example.com",
                patient_name="Patient",
                invitation_url="https://yalla.example/setup?token=ABC",
            )
        assert ok is False

    def test_payload_contains_bare_token_extracted_from_url(self, fake_settings: None) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = "{}"
        with patch.object(email_module.httpx, "post", return_value=response) as mock_post:
            email_module.send_invitation_email(
                to="patient@example.com",
                patient_name="Karim",
                invitation_url="https://yalla.example/setup?token=SECRETTOKEN123",
            )
        # Inspect the kwargs sent to httpx
        _, kwargs = mock_post.call_args
        body = kwargs["json"]
        assert body["to"] == ["patient@example.com"]
        assert body["from"] == "Yalla <onboarding@resend.dev>"
        assert "SECRETTOKEN123" in body["html"]
        assert "Karim" in body["html"]
        assert kwargs["headers"]["Authorization"] == "Bearer re_TESTKEY"

    def test_falls_back_to_generic_greeting_when_name_blank(
        self, fake_settings: None
    ) -> None:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = "{}"
        with patch.object(email_module.httpx, "post", return_value=response) as mock_post:
            email_module.send_invitation_email(
                to="patient@example.com",
                patient_name="   ",
                invitation_url="https://yalla.example/setup?token=X",
            )
        _, kwargs = mock_post.call_args
        assert "patient" in kwargs["json"]["html"].lower()
