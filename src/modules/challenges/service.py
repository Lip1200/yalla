from datetime import date, datetime, timedelta

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.challenges.schemas import (
    Challenge,
    ChallengeCategory,
    ChallengeCreate,
    ChallengeDifficulty,
    ChallengeStatus,
    ChallengeUnit,
    ChallengeUpdate,
    PatientChallenge,
    PatientChallengeAssign,
    PatientChallengeProgressUpdate,
)

CHALLENGES_TABLE = "challenges"
PATIENT_CHALLENGES_TABLE = "patient_challenges"
PROFILES_TABLE = "profiles"


def list_challenges(
    category: ChallengeCategory | None = None,
    difficulty: ChallengeDifficulty | None = None,
    templates_only: bool = False,
) -> list[Challenge]:
    query = supabase_client.table(CHALLENGES_TABLE).select("*").order("id", desc=False)
    if category is not None:
        query = query.eq("category", category.value)
    if difficulty is not None:
        query = query.eq("difficulty", difficulty.value)
    if templates_only:
        query = query.eq("is_template", True)
    response = query.execute()
    return [_row_to_challenge(row) for row in response.data]


def get_challenge(challenge_id: int) -> Challenge:
    response = (
        supabase_client.table(CHALLENGES_TABLE).select("*").eq("id", challenge_id).execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Défi introuvable.",
        )
    return _row_to_challenge(response.data[0])


def create_challenge(payload: ChallengeCreate) -> Challenge:
    insert_data = _payload_to_row(payload.model_dump(exclude_none=False))
    response = supabase_client.table(CHALLENGES_TABLE).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de créer le défi.",
        )
    return _row_to_challenge(response.data[0])


def update_challenge(challenge_id: int, payload: ChallengeUpdate) -> Challenge:
    get_challenge(challenge_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun champ à mettre à jour.",
        )
    update_data = _payload_to_row(changes)
    response = (
        supabase_client.table(CHALLENGES_TABLE)
        .update(update_data)
        .eq("id", challenge_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mise à jour du défi échouée.",
        )
    return _row_to_challenge(response.data[0])


def delete_challenge(challenge_id: int) -> None:
    get_challenge(challenge_id)
    supabase_client.table(CHALLENGES_TABLE).delete().eq("id", challenge_id).execute()


def assign_to_patient(payload: PatientChallengeAssign) -> PatientChallenge:
    _get_profile_or_404(payload.patient_id)
    challenge = get_challenge(payload.challenge_id)

    started_at = datetime.now()
    due_on = payload.due_on or (started_at.date() + timedelta(days=challenge.duration_days))

    insert_data = {
        "patient_id": payload.patient_id,
        "challenge_id": payload.challenge_id,
        "due_on": due_on.isoformat(),
        "progress": 0,
        "current_value": 0,
        "status": ChallengeStatus.ACTIVE.value,
    }
    response = supabase_client.table(PATIENT_CHALLENGES_TABLE).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible d'assigner le défi.",
        )
    return _row_to_patient_challenge(response.data[0], challenge)


def list_patient_challenges(
    patient_id: int, status_filter: ChallengeStatus | None = None
) -> list[PatientChallenge]:
    _get_profile_or_404(patient_id)
    query = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .select("*")
        .eq("patient_id", patient_id)
        .order("started_at", desc=True)
    )
    if status_filter is not None:
        query = query.eq("status", status_filter.value)
    response = query.execute()

    results: list[PatientChallenge] = []
    for row in response.data:
        challenge = get_challenge(row["challenge_id"])
        results.append(_row_to_patient_challenge(row, challenge))
    return results


def update_patient_challenge(
    assignment_id: int, payload: PatientChallengeProgressUpdate
) -> PatientChallenge:
    row = _get_assignment_or_404(assignment_id)
    challenge = get_challenge(row["challenge_id"])

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun champ à mettre à jour.",
        )

    if "status" in changes and changes["status"] is not None:
        changes["status"] = (
            changes["status"].value if hasattr(changes["status"], "value") else changes["status"]
        )
        if changes["status"] == ChallengeStatus.COMPLETED.value and "completed_at" not in changes:
            changes["completed_at"] = datetime.now().isoformat()
            changes.setdefault("progress", 100)

    response = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .update(changes)
        .eq("id", assignment_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mise à jour de l'assignation échouée.",
        )
    return _row_to_patient_challenge(response.data[0], challenge)


def _get_assignment_or_404(assignment_id: int) -> dict:
    response = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .select("*")
        .eq("id", assignment_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignation introuvable.",
        )
    return response.data[0]


def _get_profile_or_404(profile_id: int) -> dict:
    response = (
        supabase_client.table(PROFILES_TABLE).select("id").eq("id", profile_id).execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient introuvable.",
        )
    return response.data[0]


def _payload_to_row(payload: dict) -> dict:
    row = dict(payload)
    for key in ("category", "target_unit", "difficulty"):
        value = row.get(key)
        if value is not None and hasattr(value, "value"):
            row[key] = value.value
    return row


def _row_to_challenge(row: dict) -> Challenge:
    created_raw = row.get("created_at")
    created_at = (
        datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        if isinstance(created_raw, str)
        else created_raw or datetime.now()
    )
    return Challenge(
        id=row["id"],
        title=row["title"],
        description=row.get("description") or "",
        category=_safe_enum(ChallengeCategory, row.get("category"), ChallengeCategory.ACTIVITY),
        target_value=row["target_value"],
        target_unit=_safe_enum(ChallengeUnit, row.get("target_unit"), ChallengeUnit.MINUTES),
        duration_days=row.get("duration_days") or 7,
        difficulty=_safe_enum(ChallengeDifficulty, row.get("difficulty"), ChallengeDifficulty.MEDIUM),
        is_template=bool(row.get("is_template", True)),
        created_at=created_at,
    )


def _row_to_patient_challenge(row: dict, challenge: Challenge) -> PatientChallenge:
    started_raw = row.get("started_at")
    started_at = (
        datetime.fromisoformat(started_raw.replace("Z", "+00:00"))
        if isinstance(started_raw, str)
        else started_raw or datetime.now()
    )
    completed_raw = row.get("completed_at")
    completed_at = (
        datetime.fromisoformat(completed_raw.replace("Z", "+00:00"))
        if isinstance(completed_raw, str)
        else completed_raw
    )
    due_raw = row.get("due_on")
    due_on = (
        date.fromisoformat(due_raw) if isinstance(due_raw, str) else due_raw or date.today()
    )
    return PatientChallenge(
        id=row["id"],
        patient_id=row["patient_id"],
        challenge_id=row["challenge_id"],
        challenge=challenge,
        progress=row.get("progress") or 0,
        current_value=row.get("current_value") or 0,
        started_at=started_at,
        due_on=due_on,
        completed_at=completed_at,
        status=_safe_enum(ChallengeStatus, row.get("status"), ChallengeStatus.ACTIVE),
    )


def _safe_enum(enum_cls, value, fallback):
    if value is None:
        return fallback
    try:
        return enum_cls(value)
    except ValueError:
        return fallback
