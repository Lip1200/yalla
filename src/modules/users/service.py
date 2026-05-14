from datetime import date

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.users.schemas import (
    Profile,
    ProfileCreate,
    ProfileReplace,
    ProfileUpdate,
    UserRole,
)

TABLE_NAME = "profiles"


def list_profiles(limit: int = 50, offset: int = 0) -> list[Profile]:
    response = (
        supabase_client.table(TABLE_NAME)
        .select("*")
        .order("id", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return [_row_to_profile(row) for row in response.data]


def get_profile(user_id: int) -> Profile:
    response = supabase_client.table(TABLE_NAME).select("*").eq("id", user_id).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil introuvable.",
        )
    return _row_to_profile(response.data[0])


def create_profile(payload: ProfileCreate) -> Profile:
    insert_data = _profile_payload_to_row(payload.model_dump(exclude_none=False))
    response = supabase_client.table(TABLE_NAME).insert(insert_data).execute()
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossible de créer le profil.",
        )
    return _row_to_profile(response.data[0])


def update_profile(user_id: int, payload: ProfileUpdate) -> Profile:
    get_profile(user_id)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun champ à mettre à jour.",
        )

    update_data = _profile_payload_to_row(changes)
    response = (
        supabase_client.table(TABLE_NAME)
        .update(update_data)
        .eq("id", user_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mise à jour du profil échouée.",
        )
    return _row_to_profile(response.data[0])


def replace_profile(user_id: int, payload: ProfileReplace) -> Profile:
    get_profile(user_id)

    replacement = _profile_payload_to_row(payload.model_dump(exclude_none=False))
    response = (
        supabase_client.table(TABLE_NAME)
        .update(replacement)
        .eq("id", user_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Remplacement du profil échoué.",
        )
    return _row_to_profile(response.data[0])


def delete_profile(user_id: int) -> None:
    get_profile(user_id)
    supabase_client.table(TABLE_NAME).delete().eq("id", user_id).execute()


def _profile_payload_to_row(payload: dict) -> dict:
    row = dict(payload)
    if "role" in row and row["role"] is not None:
        role_value = row["role"]
        row["role"] = role_value.value if isinstance(role_value, UserRole) else role_value
    if "last_check_in" in row and isinstance(row["last_check_in"], date):
        row["last_check_in"] = row["last_check_in"].isoformat()
    return row


def _row_to_profile(row: dict) -> Profile:
    role_str = row.get("role") or UserRole.PATIENT.value
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.PATIENT

    last_check_in_raw = row.get("last_check_in")
    last_check_in_value: date | None = None
    if last_check_in_raw:
        last_check_in_value = (
            last_check_in_raw
            if isinstance(last_check_in_raw, date)
            else date.fromisoformat(last_check_in_raw)
        )

    return Profile(
        id=row["id"],
        full_name=row["full_name"],
        role=role,
        privacy_level=row.get("privacy_level") or "Données limitées",
        primary_goal=row.get("primary_goal") or "",
        age=row.get("age"),
        weekly_activity_minutes=row.get("weekly_activity_minutes") or 0,
        challenge_completion_rate=row.get("challenge_completion_rate") or 0,
        activity_completion_rate=row.get("activity_completion_rate") or 0,
        has_app_access=bool(row.get("has_app_access", True)),
        last_check_in=last_check_in_value,
        status=row.get("status"),
    )
