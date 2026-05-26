from datetime import datetime

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.core.security import AuthIdentity, get_profile_for_identity
from src.modules.consents.schemas import (
    SCOPE_HUMAN_LABELS,
    ConsentGrant,
    ConsentRecord,
    ConsentScope,
    ConsentScopeDescriptor,
    ConsentStatus,
)

CONSENTS_TABLE = "consents"


def _resolve_patient_id_or_403(identity: AuthIdentity) -> int:
    """Return the integer profile id for an authenticated real user.

    Raises 403 if the caller is a service token (consents are per-patient,
    a generic service token doesn't represent one) or if no profile row
    is linked to the auth user yet (migration 004 not applied or signup
    happened before the auto-provisioning of profiles).
    """
    if identity.is_service:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les consentements doivent être posés par un utilisateur réel, pas par le service token.",
        )
    profile = get_profile_for_identity(identity)
    if not profile or "id" not in profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun profil rattaché à ce compte.",
        )
    return int(profile["id"])


def record_consent(identity: AuthIdentity, payload: ConsentGrant) -> ConsentRecord:
    """Append a new immutable row to the audit log."""
    patient_id = _resolve_patient_id_or_403(identity)

    insert_data = {
        "patient_id": patient_id,
        "scope": payload.scope.value,
        "granted": payload.granted,
        "text_version": payload.text_version,
    }
    response = supabase_client.table(CONSENTS_TABLE).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enregistrement du consentement échoué.",
        )
    return _row_to_record(response.data[0])


def revoke_consent(identity: AuthIdentity, scope: ConsentScope) -> ConsentRecord:
    """Convenience around `record_consent` with granted=false. Uses the
    most recent known `text_version` if any so the revocation is tied to
    the same legal text the patient originally consented to."""
    patient_id = _resolve_patient_id_or_403(identity)
    latest = _latest_record_for(patient_id, scope)
    text_version = latest.text_version if latest else "revoke"

    return record_consent(
        identity,
        ConsentGrant(scope=scope, granted=False, text_version=text_version),
    )


def list_my_consents(identity: AuthIdentity) -> list[ConsentStatus]:
    """Return current consent status (latest record per scope) for every
    declared scope, including ones the patient never interacted with
    (granted=False by default)."""
    patient_id = _resolve_patient_id_or_403(identity)

    response = (
        supabase_client.table(CONSENTS_TABLE)
        .select("*")
        .eq("patient_id", patient_id)
        .order("recorded_at", desc=True)
        .execute()
    )

    seen: dict[str, dict] = {}
    for row in response.data or []:
        scope_value = row.get("scope")
        if scope_value not in seen:
            seen[scope_value] = row

    result: list[ConsentStatus] = []
    for scope in ConsentScope:
        row = seen.get(scope.value)
        if row is None:
            result.append(
                ConsentStatus(scope=scope, label=SCOPE_HUMAN_LABELS[scope], granted=False)
            )
            continue
        recorded_raw = row.get("recorded_at")
        recorded_at = (
            datetime.fromisoformat(recorded_raw.replace("Z", "+00:00"))
            if isinstance(recorded_raw, str)
            else recorded_raw
        )
        result.append(
            ConsentStatus(
                scope=scope,
                label=SCOPE_HUMAN_LABELS[scope],
                granted=bool(row.get("granted")),
                text_version=row.get("text_version"),
                last_change_at=recorded_at,
            )
        )
    return result


def list_scopes() -> list[ConsentScopeDescriptor]:
    """Static catalogue of scopes — used by the frontend to render
    checkboxes without hardcoding the labels client-side."""
    return [
        ConsentScopeDescriptor(scope=scope, label=label)
        for scope, label in SCOPE_HUMAN_LABELS.items()
    ]


def is_consent_granted(identity: AuthIdentity, scope: ConsentScope) -> bool:
    """Cheap check used by other modules (issue #23/#36) to gate
    health-data ingestion. Service tokens bypass (CI/admin)."""
    if identity.is_service:
        return True
    try:
        patient_id = _resolve_patient_id_or_403(identity)
    except HTTPException:
        return False
    latest = _latest_record_for(patient_id, scope)
    return bool(latest and latest.granted)


def _latest_record_for(patient_id: int, scope: ConsentScope) -> ConsentRecord | None:
    response = (
        supabase_client.table(CONSENTS_TABLE)
        .select("*")
        .eq("patient_id", patient_id)
        .eq("scope", scope.value)
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _row_to_record(response.data[0])


def _row_to_record(row: dict) -> ConsentRecord:
    recorded_raw = row.get("recorded_at")
    recorded_at = (
        datetime.fromisoformat(recorded_raw.replace("Z", "+00:00"))
        if isinstance(recorded_raw, str)
        else recorded_raw or datetime.now()
    )
    try:
        scope = ConsentScope(row["scope"])
    except ValueError:
        # Persist legacy / unknown scope as MARKETING for safety; in
        # practice this never happens because the API enforces the enum.
        scope = ConsentScope.MARKETING
    return ConsentRecord(
        id=row["id"],
        patient_id=row["patient_id"],
        scope=scope,
        granted=bool(row.get("granted")),
        text_version=row.get("text_version") or "",
        recorded_at=recorded_at,
    )
