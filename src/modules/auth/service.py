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

    if response.session is None:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Inscription enregistrée. Confirmation par email requise avant connexion.",
        )

    return _session_to_schema(response.session, response.user, payload.full_name)


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
