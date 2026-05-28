"""Transactional email sender backed by Resend's REST API.

We don't pull the official `resend` Python SDK — a single httpx call is
enough for the volume the demo needs (one invitation per patient
enrolment). Failures are logged but never propagate to the caller:
the doctor always gets the invitation URL back from
`create_patient_account` and can share it manually if the email side
glitches.
"""

import logging

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_invitation_email(*, to: str, patient_name: str, invitation_url: str) -> bool:
    """POST a single transactional email to the patient inviting them to
    finish their Yalla account setup. Returns True on success, False on
    any failure (network, auth, missing API key)."""
    if not settings.resend_api_key:
        logger.info("send_invitation_email: RESEND_API_KEY unset, skipping email send")
        return False

    safe_name = (patient_name or "").strip() or "patient"
    # Extract the bare token from the invitation_url so the patient can
    # paste it into the patient-app's SetupAccountScreen. The URL itself
    # would land on doctor-web's domain — useless on a phone.
    bare_token = invitation_url.rsplit("token=", 1)[-1]
    payload = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": "Ton invitation à rejoindre Yalla",
        "html": (
            f"<p>Bonjour {safe_name},</p>"
            "<p>Ton médecin t'invite à rejoindre Yalla pour t'accompagner "
            "dans ton parcours diabète.</p>"
            "<p><strong>Pour activer ton compte&nbsp;:</strong></p>"
            "<ol>"
            "<li>Installe <strong>Expo Go</strong> depuis l'App Store ou Play Store</li>"
            "<li>Ouvre l'app <strong>Yalla</strong> (depuis l'invitation que ton médecin t'a partagée)</li>"
            "<li>Sur l'écran de connexion, appuie sur <em>« J'ai un code d'invitation »</em></li>"
            "<li>Colle ce code&nbsp;:</li>"
            "</ol>"
            f'<p style="font-family:monospace;font-size:15px;background:#f1f5f9;border:1px solid #cbd5e1;border-radius:8px;padding:14px 16px;word-break:break-all">{bare_token}</p>'
            "<p>Puis choisis ton mot de passe et c'est parti.</p>"
            "<p style=\"color:#64748b;font-size:13px\">Le code expire dans 7 jours. Pour toute question, contacte ton médecin.</p>"
            "<p>— L'équipe Yalla</p>"
        ),
    }
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(_RESEND_ENDPOINT, json=payload, headers=headers, timeout=10.0)
    except httpx.HTTPError as exc:
        logger.warning("send_invitation_email: network error %s", exc)
        return False
    if response.status_code >= 400:
        logger.warning(
            "send_invitation_email: resend returned %d — %s",
            response.status_code,
            response.text[:300],
        )
        return False
    logger.info("send_invitation_email: queued for %s", to)
    return True
