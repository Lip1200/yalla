from datetime import date, datetime, timedelta

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.core.security import AuthIdentity, get_profile_for_identity
from src.modules.challenges.schemas import (
    Badge,
    BadgeCriteriaKind,
    Challenge,
    ChallengeCategory,
    ChallengeCreate,
    ChallengeDifficulty,
    ChallengeLogRequest,
    ChallengeLogResponse,
    ChallengeStatus,
    ChallengeUnit,
    ChallengeUpdate,
    PatientBadge,
    PatientChallenge,
    PatientChallengeAssign,
    PatientChallengeProgressUpdate,
)

CHALLENGES_TABLE = "challenges"
PATIENT_CHALLENGES_TABLE = "patient_challenges"
PROFILES_TABLE = "profiles"
BADGES_TABLE = "badges"
PATIENT_BADGES_TABLE = "patient_badges"


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


def assign_to_patient(
    payload: PatientChallengeAssign,
    identity: AuthIdentity | None = None,
) -> PatientChallenge:
    """Assign a challenge to a patient.

    Permission rules (issue #41):
    - Service token (`identity.is_service`) → always allowed.
    - Real user → allowed if either (a) self-assignment
      (payload.patient_id matches the caller's own profile.id), or
      (b) caller's role is 'doctor' or 'expert_patient'.
    - A regular patient assigning a challenge to *someone else* → 403.

    `identity=None` keeps backward compatibility for internal callers
    (e.g. tests, future bulk-assign scripts) — they bypass the check.
    """
    _get_profile_or_404(payload.patient_id)
    challenge = get_challenge(payload.challenge_id)

    if identity is not None and not identity.is_service:
        caller_profile = get_profile_for_identity(identity)
        caller_id = caller_profile.get("id") if caller_profile else None
        caller_role = caller_profile.get("role") if caller_profile else None
        is_self_assignment = caller_id == payload.patient_id
        is_authorised_role = caller_role in ("doctor", "expert_patient")
        if not is_self_assignment and not is_authorised_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez assigner un défi qu'à vous-même.",
            )

    # Idempotency: if an active assignment for this (patient, challenge) pair
    # already exists, return it instead of creating a duplicate row. Avoids
    # the "Mes défis" duplication when the patient-app fires the join twice
    # (double-tap, network retry, etc.).
    existing = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .select("*")
        .eq("patient_id", payload.patient_id)
        .eq("challenge_id", payload.challenge_id)
        .eq("status", ChallengeStatus.ACTIVE.value)
        .limit(1)
        .execute()
    )
    if existing.data:
        return _row_to_patient_challenge(existing.data[0], challenge)

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


# ===========================================================================
# Progress logging + badge attribution (issue #22)
# ===========================================================================


def log_challenge_progress(assignment_id: int, payload: ChallengeLogRequest) -> ChallengeLogResponse:
    """Increment an assignment's `current_value`, recompute `progress`, and
    award any newly-deserved badges if the assignment crosses the completion
    threshold (progress reaches 100% or current_value reaches target_value)."""
    row = _get_assignment_or_404(assignment_id)
    challenge = get_challenge(row["challenge_id"])

    if row.get("status") and row["status"] != ChallengeStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible d'enregistrer un progrès sur un défi en status '{row['status']}'.",
        )

    new_value = int(row.get("current_value") or 0) + payload.value
    new_progress = min(100, int(round(new_value * 100 / max(1, challenge.target_value))))

    changes: dict = {"current_value": new_value, "progress": new_progress}
    just_completed = False
    if new_progress >= 100:
        changes["status"] = ChallengeStatus.COMPLETED.value
        changes["completed_at"] = datetime.now().isoformat()
        changes["progress"] = 100
        just_completed = True

    response = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .update(changes)
        .eq("id", assignment_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enregistrement du progrès échoué.",
        )

    updated_assignment = _row_to_patient_challenge(response.data[0], challenge)
    newly_awarded: list[Badge] = []
    if just_completed:
        newly_awarded = evaluate_and_award_badges(updated_assignment.patient_id, updated_assignment)

    return ChallengeLogResponse(assignment=updated_assignment, newly_awarded_badges=newly_awarded)


def list_badges() -> list[Badge]:
    response = supabase_client.table(BADGES_TABLE).select("*").order("id", desc=False).execute()
    return [_row_to_badge(row) for row in response.data]


def list_patient_badges(patient_id: int) -> list[PatientBadge]:
    _get_profile_or_404(patient_id)
    response = (
        supabase_client.table(PATIENT_BADGES_TABLE)
        .select("*")
        .eq("patient_id", patient_id)
        .order("earned_at", desc=True)
        .execute()
    )
    results: list[PatientBadge] = []
    for row in response.data:
        badge = _fetch_badge_by_id(row["badge_id"])
        if badge is None:
            continue
        earned_raw = row.get("earned_at")
        earned_at = (
            datetime.fromisoformat(earned_raw.replace("Z", "+00:00"))
            if isinstance(earned_raw, str)
            else earned_raw or datetime.now()
        )
        results.append(
            PatientBadge(
                badge=badge,
                earned_at=earned_at,
                source_assignment_id=row.get("source_assignment_id"),
            )
        )
    return results


def evaluate_and_award_badges(
    patient_id: int, completed_assignment: PatientChallenge
) -> list[Badge]:
    """Re-evaluate every badge criterion against the patient's history and
    award (idempotently) those that are met. Returns the freshly-awarded
    badges only (badges already earned are skipped)."""
    already_earned = {row["badge_id"] for row in _patient_badge_rows(patient_id)}

    completed_count = _count_completed_assignments(patient_id)
    completed_by_category = _count_completed_by_category(patient_id)

    candidates: list[tuple[Badge, bool]] = []
    for badge in list_badges():
        if badge.id in already_earned:
            continue
        if _matches_criterion(badge, completed_count, completed_by_category):
            candidates.append((badge, True))

    newly_awarded: list[Badge] = []
    for badge, _ in candidates:
        try:
            supabase_client.table(PATIENT_BADGES_TABLE).insert(
                {
                    "patient_id": patient_id,
                    "badge_id": badge.id,
                    "source_assignment_id": completed_assignment.id,
                }
            ).execute()
            newly_awarded.append(badge)
        except Exception:
            # Idempotent insert: ignore race conditions where the badge was
            # awarded by a concurrent log call.
            continue
    return newly_awarded


def _matches_criterion(
    badge: Badge,
    completed_count: int,
    completed_by_category: dict[str, int],
) -> bool:
    if badge.criteria_kind == BadgeCriteriaKind.FIRST_COMPLETION:
        return completed_count >= 1
    if badge.criteria_kind == BadgeCriteriaKind.COMPLETION_COUNT:
        return completed_count >= badge.criteria_threshold
    if badge.criteria_kind == BadgeCriteriaKind.CATEGORY_COMPLETION:
        if badge.criteria_category is None:
            return False
        category_value = badge.criteria_category.value
        return completed_by_category.get(category_value, 0) >= badge.criteria_threshold
    return False


def _count_completed_assignments(patient_id: int) -> int:
    response = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .select("id", count="exact")
        .eq("patient_id", patient_id)
        .eq("status", ChallengeStatus.COMPLETED.value)
        .execute()
    )
    return response.count or len(response.data or [])


def _count_completed_by_category(patient_id: int) -> dict[str, int]:
    completed = (
        supabase_client.table(PATIENT_CHALLENGES_TABLE)
        .select("challenge_id")
        .eq("patient_id", patient_id)
        .eq("status", ChallengeStatus.COMPLETED.value)
        .execute()
    )
    counts: dict[str, int] = {}
    for row in completed.data or []:
        challenge_row = (
            supabase_client.table(CHALLENGES_TABLE)
            .select("category")
            .eq("id", row["challenge_id"])
            .limit(1)
            .execute()
        )
        if not challenge_row.data:
            continue
        category = challenge_row.data[0].get("category") or ChallengeCategory.ACTIVITY.value
        counts[category] = counts.get(category, 0) + 1
    return counts


def _patient_badge_rows(patient_id: int) -> list[dict]:
    response = (
        supabase_client.table(PATIENT_BADGES_TABLE)
        .select("badge_id")
        .eq("patient_id", patient_id)
        .execute()
    )
    return response.data or []


def _fetch_badge_by_id(badge_id: int) -> Badge | None:
    response = (
        supabase_client.table(BADGES_TABLE).select("*").eq("id", badge_id).limit(1).execute()
    )
    return _row_to_badge(response.data[0]) if response.data else None


def _row_to_badge(row: dict) -> Badge:
    created_raw = row.get("created_at")
    created_at = (
        datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        if isinstance(created_raw, str)
        else created_raw or datetime.now()
    )
    return Badge(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        description=row.get("description") or "",
        icon=row.get("icon") or "🏅",
        criteria_kind=BadgeCriteriaKind(row["criteria_kind"]),
        criteria_threshold=int(row.get("criteria_threshold") or 1),
        criteria_category=_safe_enum(ChallengeCategory, row.get("criteria_category"), None)
        if row.get("criteria_category")
        else None,
        created_at=created_at,
    )
