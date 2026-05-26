from datetime import datetime, timezone

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.auth.schemas import (
    AuthSession,
    AuthUser,
    DoctorSignupRequest,
    LoginRequest,
    PatientSignupRequest,
    RefreshRequest,
    SetupPasswordRequest,
    SignupRequest,
)

ACCOUNT_SETUP_TOKENS_TABLE = "account_setup_tokens"
PROFILES_TABLE = "profiles"


def signup_patient(payload: PatientSignupRequest) -> AuthSession:
    """Create a patient account. Server hardcodes role='patient' — the
    client has no way to set the role from outside (no `role` field on
    PatientSignupRequest)."""
    return _do_signup(
        email=str(payload.email),
        password=payload.password,
        metadata={
            "full_name": payload.full_name,
            "role": "patient",
        },
        full_name=payload.full_name,
    )


def signup_doctor(payload: DoctorSignupRequest) -> AuthSession:
    """Create a doctor account. Server hardcodes role='doctor'. Specialty
    and facility are accepted because they are profile data, not
    authorization fields."""
    return _do_signup(
        email=str(payload.email),
        password=payload.password,
        metadata={
            "full_name": payload.full_name,
            "specialty": payload.specialty,
            "facility": payload.facility,
            "role": "doctor",
        },
        full_name=payload.full_name,
    )


def signup(payload: SignupRequest) -> AuthSession:
    """DEPRECATED — kept for backward compatibility with the
    doctor-web LoginScreen that still POSTs /api/auth/signup. Forwards
    to `signup_doctor` (the only historical use case). New code should
    target `/api/auth/signup/doctor` or `/api/auth/signup/patient`
    explicitly."""
    return signup_doctor(payload)


def _do_signup(
    email: str,
    password: str,
    metadata: dict,
    full_name: str,
) -> AuthSession:
    try:
        response = supabase_client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": metadata},
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

    _ensure_profile_for_auth_user(response.user, full_name)

    if response.session is None:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Inscription enregistrée. Confirmation par email requise avant connexion.",
        )

    return _session_to_schema(response.session, response.user, full_name)


_VALID_PROFILE_ROLES = {"patient", "doctor", "expert_patient"}


def _ensure_profile_for_auth_user(user, full_name: str) -> None:
    """Best-effort creation of a `profiles` row linked to a freshly signed-up
    auth user.

    Reads `role`, `specialty` and `facility` from the auth user's
    `user_metadata` to support both patient and doctor signup flows from a
    single endpoint (the doctor signup form populates these via the
    SignupRequest fields). Defaults to role='patient' when unset.

    Silently no-ops if a row with this `auth_user_id` already exists
    (idempotent for repeated signups) or if the link column is missing
    (migration 004 not yet applied)."""
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

        metadata = getattr(user, "user_metadata", None) or {}
        raw_role = metadata.get("role") if isinstance(metadata, dict) else None
        role = raw_role if raw_role in _VALID_PROFILE_ROLES else "patient"
        specialty = (metadata.get("specialty") if isinstance(metadata, dict) else None) or ""
        facility = (metadata.get("facility") if isinstance(metadata, dict) else None) or ""

        next_id = _next_profile_id()
        insert_data = {
            "id": next_id,
            "auth_user_id": str(user.id),
            "full_name": full_name,
            "role": role,
            "privacy_level": "Données limitées",
            "primary_goal": "",
            "weekly_activity_minutes": 0,
            "challenge_completion_rate": 0,
            "activity_completion_rate": 0,
            "has_app_access": True,
            "specialty": specialty,
            "facility": facility,
        }
        try:
            supabase_client.table("profiles").insert(insert_data).execute()
        except Exception:
            # Fallback for environments where migration 006 hasn't been
            # applied yet: retry without the new columns.
            insert_data.pop("specialty", None)
            insert_data.pop("facility", None)
            supabase_client.table("profiles").insert(insert_data).execute()
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


def setup_account_password(payload: SetupPasswordRequest) -> AuthSession:
    """Finalize a patient account created by a doctor (issue #33 flow).

    Validates the one-shot token, creates the Supabase Auth user with the
    patient-chosen password, links it back to the pre-provisioned profile
    row via `auth_user_id`, and returns a fresh AuthSession so the patient
    is logged in immediately.
    """
    token_row = _fetch_setup_token_or_404(payload.token)

    if token_row.get("used_at"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien d'invitation déjà utilisé.",
        )

    expires_raw = token_row.get("expires_at")
    expires_at = (
        datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        if isinstance(expires_raw, str)
        else expires_raw
    )
    if expires_at and datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Lien d'invitation expiré. Demandez à votre médecin de le régénérer.",
        )

    email = token_row.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien d'invitation invalide (email manquant).",
        )

    profile_id = token_row.get("patient_id")
    profile_row = (
        supabase_client.table(PROFILES_TABLE).select("full_name").eq("id", profile_id).limit(1).execute()
    )
    full_name = (
        profile_row.data[0]["full_name"]
        if profile_row.data
        else email.split("@")[0]
    )

    try:
        signup_response = supabase_client.auth.sign_up(
            {
                "email": email,
                "password": payload.password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": "patient",
                    }
                },
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Création du compte impossible : {exc}",
        ) from exc

    if signup_response.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Création du compte impossible : utilisateur non créé.",
        )

    # Link the auth user back to the pre-provisioned profile row.
    try:
        supabase_client.table(PROFILES_TABLE).update(
            {"auth_user_id": str(signup_response.user.id)}
        ).eq("id", profile_id).execute()
    except Exception:
        # Profile link failure is non-blocking for the patient — they can
        # still log in, but they'll have no profile until the link is
        # repaired manually. Logged here for the doctor to see (TODO).
        pass

    # Burn the token (idempotent).
    try:
        supabase_client.table(ACCOUNT_SETUP_TOKENS_TABLE).update(
            {"used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("token", payload.token).execute()
    except Exception:
        pass

    if signup_response.session is None:
        # Supabase email-confirmation mode: account exists but no session
        # until the user clicks the confirmation email.
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Compte créé. Confirmation par email requise avant connexion.",
        )

    return _session_to_schema(signup_response.session, signup_response.user, full_name)


def _fetch_setup_token_or_404(token: str) -> dict:
    response = (
        supabase_client.table(ACCOUNT_SETUP_TOKENS_TABLE)
        .select("*")
        .eq("token", token)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lien d'invitation introuvable.",
        )
    return response.data[0]


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
    specialty = metadata.get("specialty") if isinstance(metadata, dict) else None
    facility = metadata.get("facility") if isinstance(metadata, dict) else None
    return AuthUser(
        id=str(user.id),
        email=getattr(user, "email", None),
        full_name=full_name or full_name_fallback,
        specialty=specialty,
        facility=facility,
    )
