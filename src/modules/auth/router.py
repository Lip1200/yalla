from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
from src.modules.auth.service import (
    get_user,
    login,
    logout,
    refresh,
    setup_account_password,
    signup,
    signup_doctor,
    signup_patient,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=True)


@router.post(
    "/signup/patient",
    response_model=AuthSession,
    status_code=status.HTTP_201_CREATED,
)
def post_signup_patient(payload: PatientSignupRequest):
    """Public patient signup. Server-side role is always 'patient' —
    cannot be elevated by the client (the payload has no role field)."""
    return signup_patient(payload)


@router.post(
    "/signup/doctor",
    response_model=AuthSession,
    status_code=status.HTTP_201_CREATED,
)
def post_signup_doctor(payload: DoctorSignupRequest):
    """Doctor signup. Server-side role is always 'doctor'."""
    return signup_doctor(payload)


@router.post(
    "/signup",
    response_model=AuthSession,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
def post_signup(payload: SignupRequest):
    """DEPRECATED — kept for backward compatibility with the doctor-web
    LoginScreen that still posts here. Forwards to /signup/doctor.

    New callers must target /signup/doctor or /signup/patient
    explicitly so the intent (and the resulting profile.role) is
    unambiguous."""
    return signup(payload)


@router.post("/login", response_model=AuthSession)
def post_login(payload: LoginRequest):
    return login(payload)


@router.post("/refresh", response_model=AuthSession)
def post_refresh(payload: RefreshRequest):
    return refresh(payload)


@router.post("/setup-password", response_model=AuthSession)
def post_setup_password(payload: SetupPasswordRequest):
    return setup_account_password(payload)


@router.get("/me", response_model=AuthUser)
def read_me(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_user(credentials.credentials)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def post_logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logout(credentials.credentials)
