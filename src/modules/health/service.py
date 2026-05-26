from datetime import datetime

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.core.security import AuthIdentity, get_profile_for_identity
from src.modules.consents.schemas import ConsentScope
from src.modules.consents.service import is_consent_granted
from src.modules.health.schemas import (
    DEFAULT_UNIT,
    KIND_TO_CONSENT,
    HealthObservation,
    HealthObservationBatch,
    HealthObservationBatchResult,
    HealthObservationCreate,
    ObservationKind,
    ObservationSource,
)

OBSERVATIONS_TABLE = "health_observations"
PROFILES_TABLE = "profiles"


def record_observation(
    identity: AuthIdentity,
    payload: HealthObservationCreate,
    explicit_patient_id: int | None = None,
) -> HealthObservation:
    patient_id = _resolve_patient_id(identity, explicit_patient_id)
    _ensure_consent_or_403(identity, payload.kind)
    return _insert_one(patient_id, payload)


def record_observations_batch(
    identity: AuthIdentity,
    payload: HealthObservationBatch,
    explicit_patient_id: int | None = None,
) -> HealthObservationBatchResult:
    patient_id = _resolve_patient_id(identity, explicit_patient_id)
    accepted: list[HealthObservation] = []
    rejected: list[dict] = []
    for observation in payload.observations:
        try:
            _ensure_consent_or_403(identity, observation.kind)
        except HTTPException as exc:
            rejected.append({"kind": observation.kind.value, "reason": exc.detail})
            continue
        try:
            accepted.append(_insert_one(patient_id, observation))
        except Exception as exc:
            rejected.append({"kind": observation.kind.value, "reason": f"Insert error: {exc}"})
    return HealthObservationBatchResult(accepted=accepted, rejected=rejected)


def list_observations(
    caller: AuthIdentity,
    patient_id: int,
    kind: ObservationKind | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> list[HealthObservation]:
    _ensure_read_access_or_403(caller, patient_id)
    query = (
        supabase_client.table(OBSERVATIONS_TABLE)
        .select("*")
        .eq("patient_id", patient_id)
        .order("recorded_at", desc=True)
        .limit(max(1, min(limit, 500)))
    )
    if kind is not None:
        query = query.eq("kind", kind.value)
    if since is not None:
        query = query.gte("recorded_at", since.isoformat())
    if until is not None:
        query = query.lte("recorded_at", until.isoformat())
    response = query.execute()
    return [_row_to_observation(row) for row in response.data or []]


def latest_per_kind(caller: AuthIdentity, patient_id: int) -> dict[str, HealthObservation]:
    """Return the most recent observation per kind for a patient — used by
    the doctor dashboard summary and the patient progress home screen."""
    _ensure_read_access_or_403(caller, patient_id)
    response = (
        supabase_client.table(OBSERVATIONS_TABLE)
        .select("*")
        .eq("patient_id", patient_id)
        .order("recorded_at", desc=True)
        .execute()
    )
    latest: dict[str, HealthObservation] = {}
    for row in response.data or []:
        kind_value = row.get("kind")
        if kind_value in latest:
            continue
        latest[kind_value] = _row_to_observation(row)
    return latest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_patient_id(identity: AuthIdentity, explicit: int | None) -> int:
    """Derive the target patient id.

    - Real user: must self-target (explicit=None or matching own id) OR be
      a doctor/expert (then any patient_id is allowed).
    - Service token: explicit patient_id required (no profile to derive
      from).
    """
    if identity.is_service:
        if explicit is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id requis pour les appels via service token.",
            )
        return explicit

    profile = get_profile_for_identity(identity)
    if not profile or "id" not in profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun profil rattaché à ce compte.",
        )
    caller_id = int(profile["id"])
    caller_role = profile.get("role")

    if explicit is None or explicit == caller_id:
        return caller_id

    if caller_role in ("doctor", "expert_patient"):
        return explicit

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Vous ne pouvez enregistrer des observations que pour vous-même.",
    )


def _ensure_consent_or_403(identity: AuthIdentity, kind: ObservationKind) -> None:
    required = KIND_TO_CONSENT.get(kind)
    if required is None:
        # No consent scope mapped — allowed by default (e.g. clinical
        # metrics entered by the doctor: glucose, blood pressure).
        return
    if identity.is_service:
        return
    if not is_consent_granted(identity, required):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Consentement requis : '{required.value}'. "
                "Activez ce consentement dans vos réglages Yalla avant d'envoyer ce type de mesure."
            ),
        )


def _ensure_read_access_or_403(caller: AuthIdentity, patient_id: int) -> None:
    """A caller may read a patient's observations if:
    - service token (admin/dev), or
    - same caller as the patient (read own), or
    - doctor / expert_patient (clinical / animator view).
    """
    if caller.is_service:
        return
    profile = get_profile_for_identity(caller)
    if not profile or "id" not in profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun profil rattaché à ce compte.",
        )
    if int(profile["id"]) == patient_id:
        return
    if profile.get("role") in ("doctor", "expert_patient"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Vous ne pouvez consulter que vos propres observations santé.",
    )


def _insert_one(patient_id: int, payload: HealthObservationCreate) -> HealthObservation:
    unit = payload.unit or DEFAULT_UNIT.get(payload.kind, "")
    insert_data = {
        "patient_id": patient_id,
        "kind": payload.kind.value,
        "value": payload.value,
        "unit": unit,
        "recorded_at": payload.recorded_at.isoformat(),
        "source": payload.source.value,
    }
    response = supabase_client.table(OBSERVATIONS_TABLE).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enregistrement de l'observation échoué.",
        )
    return _row_to_observation(response.data[0])


def _row_to_observation(row: dict) -> HealthObservation:
    recorded_raw = row.get("recorded_at")
    recorded_at = (
        datetime.fromisoformat(recorded_raw.replace("Z", "+00:00"))
        if isinstance(recorded_raw, str)
        else recorded_raw or datetime.now()
    )
    created_raw = row.get("created_at")
    created_at = (
        datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        if isinstance(created_raw, str)
        else created_raw or datetime.now()
    )
    try:
        kind = ObservationKind(row["kind"])
    except ValueError:
        kind = ObservationKind.STEPS_DAILY  # safety fallback; should never trigger
    try:
        source = ObservationSource(row.get("source") or ObservationSource.MANUAL.value)
    except ValueError:
        source = ObservationSource.MANUAL
    return HealthObservation(
        id=row["id"],
        patient_id=row["patient_id"],
        kind=kind,
        value=float(row["value"]),
        unit=row.get("unit") or "",
        recorded_at=recorded_at,
        source=source,
        created_at=created_at,
    )
