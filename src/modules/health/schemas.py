from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.modules.consents.schemas import ConsentScope


class ObservationKind(StrEnum):
    """Supported metric types. Adding a new one is the trigger to also:
    - add the corresponding unit hint in DEFAULT_UNIT below,
    - add a consent scope mapping in KIND_TO_CONSENT below (or document
      the omission if no consent is required)."""

    STEPS_DAILY = "steps_daily"
    HEART_RATE_RESTING = "heart_rate_resting"
    HEART_RATE_ACTIVE = "heart_rate_active"
    WEIGHT_KG = "weight_kg"
    SLEEP_MINUTES = "sleep_minutes"
    GLUCOSE_MG_DL = "glucose_mg_dl"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"


DEFAULT_UNIT: dict[ObservationKind, str] = {
    ObservationKind.STEPS_DAILY: "steps",
    ObservationKind.HEART_RATE_RESTING: "bpm",
    ObservationKind.HEART_RATE_ACTIVE: "bpm",
    ObservationKind.WEIGHT_KG: "kg",
    ObservationKind.SLEEP_MINUTES: "minutes",
    ObservationKind.GLUCOSE_MG_DL: "mg/dL",
    ObservationKind.BLOOD_PRESSURE_SYSTOLIC: "mmHg",
    ObservationKind.BLOOD_PRESSURE_DIASTOLIC: "mmHg",
}


# Mapping from observation kind to the consent scope required to persist
# it. Kinds absent from this dict are *not* consent-gated (used today for
# glucose / BP — clinical metrics typically entered in a consultation
# context). When adding a new sensitive scope, add the mapping here.
KIND_TO_CONSENT: dict[ObservationKind, ConsentScope] = {
    ObservationKind.STEPS_DAILY: ConsentScope.HEALTH_STEPS,
    ObservationKind.HEART_RATE_RESTING: ConsentScope.HEALTH_HEART_RATE,
    ObservationKind.HEART_RATE_ACTIVE: ConsentScope.HEALTH_HEART_RATE,
    ObservationKind.WEIGHT_KG: ConsentScope.HEALTH_WEIGHT,
    ObservationKind.SLEEP_MINUTES: ConsentScope.HEALTH_SLEEP,
}


class ObservationSource(StrEnum):
    MANUAL = "manual"
    APPLE_HEALTH = "apple_health"
    HEALTH_CONNECT = "health_connect"
    DOCTOR_ENTRY = "doctor_entry"


class HealthObservationCreate(BaseModel):
    kind: ObservationKind
    value: float = Field(gt=0)
    unit: str | None = Field(
        default=None,
        max_length=20,
        description="Optional unit override. Defaults to DEFAULT_UNIT[kind] when null.",
    )
    recorded_at: datetime
    source: ObservationSource = ObservationSource.MANUAL


class HealthObservationBatch(BaseModel):
    observations: list[HealthObservationCreate] = Field(min_length=1, max_length=500)


class HealthObservation(BaseModel):
    id: int
    patient_id: int
    kind: ObservationKind
    value: float
    unit: str
    recorded_at: datetime
    source: ObservationSource
    created_at: datetime


class HealthObservationBatchResult(BaseModel):
    accepted: list[HealthObservation]
    rejected: list[dict] = Field(
        default_factory=list,
        description="Items the server rejected with a reason — usually a missing consent scope.",
    )
