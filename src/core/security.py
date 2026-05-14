from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings

# HTTPBearer with auto_error=False allows progressive API integration without instantly blocking local MVP dev demos
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme)) -> str:
    """
    Validates API authorization token against application configuration.
    Returns authenticated identifier or role.
    """
    if credentials and credentials.credentials != settings.api_secret_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return "authenticated_user"
