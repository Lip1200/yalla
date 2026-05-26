from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ConsentScope(StrEnum):
    """Granular consent scopes presented to the patient.

    Each scope is independent — the patient grants or revokes each one
    individually. Add new scopes here (and document them in the consent
    text shown to the patient) when introducing new data-sensitive
    features.
    """

    HEALTH_STEPS = "health_steps"
    HEALTH_HEART_RATE = "health_heart_rate"
    HEALTH_WEIGHT = "health_weight"
    HEALTH_SLEEP = "health_sleep"
    SHARE_WITH_DOCTOR = "share_with_doctor"
    MARKETING = "marketing"


SCOPE_HUMAN_LABELS: dict[ConsentScope, str] = {
    ConsentScope.HEALTH_STEPS: "Synchroniser mes pas (Apple Health / Health Connect)",
    ConsentScope.HEALTH_HEART_RATE: "Synchroniser ma fréquence cardiaque",
    ConsentScope.HEALTH_WEIGHT: "Synchroniser mon poids",
    ConsentScope.HEALTH_SLEEP: "Synchroniser mon sommeil",
    ConsentScope.SHARE_WITH_DOCTOR: "Partager mes données avec mon médecin",
    ConsentScope.MARKETING: "Recevoir des communications de Yalla",
}


class ConsentGrant(BaseModel):
    """Body for `POST /api/consents` — patient grants or revokes a scope."""

    scope: ConsentScope
    granted: bool = Field(description="True grants, False revokes.")
    text_version: str = Field(
        min_length=1,
        max_length=40,
        description=(
            "Version of the consent text the patient just saw and accepted. "
            "Bump this whenever the legal text changes so consent stays "
            "explicit-per-version."
        ),
    )


class ConsentRecord(BaseModel):
    """One row in the audit log."""

    id: int
    patient_id: int
    scope: ConsentScope
    granted: bool
    text_version: str
    recorded_at: datetime


class ConsentStatus(BaseModel):
    """Current state of a single consent scope for the caller."""

    scope: ConsentScope
    label: str
    granted: bool
    text_version: str | None = None
    last_change_at: datetime | None = None


class ConsentScopeDescriptor(BaseModel):
    """Static catalogue entry returned by `GET /api/consents/scopes`."""

    scope: ConsentScope
    label: str
