from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.modules.auth.schemas import (
    AuthSession,
    AuthUser,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)
from src.modules.auth.service import (
    get_user,
    login,
    logout,
    refresh,
    signup,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=True)


@router.post("/signup", response_model=AuthSession, status_code=status.HTTP_201_CREATED)
def post_signup(payload: SignupRequest):
    return signup(payload)


@router.post("/login", response_model=AuthSession)
def post_login(payload: LoginRequest):
    return login(payload)


@router.post("/refresh", response_model=AuthSession)
def post_refresh(payload: RefreshRequest):
    return refresh(payload)


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
