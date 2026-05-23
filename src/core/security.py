from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.core.config import settings
from src.core.database import supabase_client

security_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


class AuthIdentity(BaseModel):
    """Represents the authenticated caller.

    A real user authenticated via Supabase carries `id` (UUID) and optional
    `email`. A service-token caller (CI, demo scripts, mobile dev) has
    `is_service=True` and a synthetic `id`.
    """

    id: str
    email: str | None = None
    is_service: bool = False


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthIdentity:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requis.",
            headers=_UNAUTHORIZED_HEADERS,
        )

    token = credentials.credentials

    if token == settings.api_secret_token:
        return AuthIdentity(id="service", is_service=True)

    try:
        response = supabase_client.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc

    if response is None or response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers=_UNAUTHORIZED_HEADERS,
        )

    return AuthIdentity(
        id=str(response.user.id),
        email=getattr(response.user, "email", None),
        is_service=False,
    )


def require_real_user(identity: AuthIdentity = Depends(get_current_user)) -> AuthIdentity:
    """Dependency that rejects the service-token fallback.

    Use this guard on endpoints that must be invoked by a real authenticated
    user (e.g. self-service profile edits), where the shared service token
    would defeat the purpose of authorization.
    """
    if identity.is_service:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cet endpoint requiert un utilisateur authentifié.",
        )
    return identity


def get_profile_for_identity(identity: AuthIdentity) -> dict | None:
    """Resolve the `profiles` row linked to an authenticated Supabase user.

    Returns None for service-token callers (no link possible) and for real
    users that have no provisioned profile row yet (migration 004 not
    applied, or signup happened before the auto-provisioning).
    """
    if identity.is_service:
        return None
    try:
        response = (
            supabase_client.table("profiles")
            .select("*")
            .eq("auth_user_id", identity.id)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    return response.data[0] if response.data else None
