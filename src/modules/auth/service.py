from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.auth.schemas import (
    AuthSession,
    AuthUser,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)


def signup(payload: SignupRequest) -> AuthSession:
    try:
        response = supabase_client.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {"data": {"full_name": payload.full_name}},
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inscription échouée : {exc}",
        ) from exc

    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inscription échouée : utilisateur non créé.",
        )

    _ensure_profile_for_auth_user(response.user, payload.full_name)

    if response.session is None:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Inscription enregistrée. Confirmation par email requise avant connexion.",
        )

    return _session_to_schema(response.session, response.user, payload.full_name)


def _ensure_profile_for_auth_user(user, full_name: str) -> None:
    """Best-effort creation of a `profiles` row linked to a freshly signed-up
    auth user. Silently no-ops if a row with this `auth_user_id` already
    exists (idempotent for repeated signups) or if the link column is
    missing (migration 004 not yet applied)."""
    try:
        existing = (
            supabase_client.table("profiles")
            .select("id")
            .eq("auth_user_id", str(user.id))
            .limit(1)
            .execute()
        )
        if existing.data:
            return

        next_id = _next_profile_id()
        supabase_client.table("profiles").insert(
            {
                "id": next_id,
                "auth_user_id": str(user.id),
                "full_name": full_name,
                "role": "patient",
                "privacy_level": "Données limitées",
                "primary_goal": "",
                "weekly_activity_minutes": 0,
                "challenge_completion_rate": 0,
                "activity_completion_rate": 0,
                "has_app_access": True,
            }
        ).execute()
    except Exception:
        # Best-effort: never block signup on profile provisioning.
        return


def _next_profile_id() -> int:
    response = (
        supabase_client.table("profiles")
        .select("id")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return 1001
    return int(response.data[0]["id"]) + 1


def login(payload: LoginRequest) -> AuthSession:
    try:
        response = supabase_client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides.",
        ) from exc

    if response.user is None or response.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides.",
        )

    return _session_to_schema(response.session, response.user)


def refresh(payload: RefreshRequest) -> AuthSession:
    try:
        response = supabase_client.auth.refresh_session(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide.",
        ) from exc

    if response.user is None or response.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide.",
        )

    return _session_to_schema(response.session, response.user)


def get_user(access_token: str) -> AuthUser:
    try:
        response = supabase_client.auth.get_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou invalide.",
        ) from exc

    if response is None or response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou invalide.",
        )

    return _user_to_schema(response.user)


def logout(access_token: str) -> None:
    try:
        supabase_client.auth.set_session(access_token, "")
        supabase_client.auth.sign_out()
    except Exception:
        pass


def _session_to_schema(session, user, full_name_fallback: str | None = None) -> AuthSession:
    return AuthSession(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=getattr(session, "expires_in", None),
        user=_user_to_schema(user, full_name_fallback),
    )


def _user_to_schema(user, full_name_fallback: str | None = None) -> AuthUser:
    metadata = getattr(user, "user_metadata", None) or {}
    full_name = metadata.get("full_name") if isinstance(metadata, dict) else None
    return AuthUser(
        id=str(user.id),
        email=getattr(user, "email", None),
        full_name=full_name or full_name_fallback,
    )
