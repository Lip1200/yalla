from typing import Callable

from fastapi import Depends, HTTPException, status

from src.core.security import AuthIdentity, get_current_user
from src.modules.consents.schemas import ConsentScope
from src.modules.consents.service import is_consent_granted


def require_consent(scope: ConsentScope) -> Callable[[AuthIdentity], AuthIdentity]:
    """Build a FastAPI dependency that rejects callers who have not
    granted the given scope.

    Usage:
        @router.post(
            "/api/health/observations",
            dependencies=[Depends(require_consent(ConsentScope.HEALTH_STEPS))],
        )
        def post_observation(...): ...

    Service tokens bypass (CI/admin/dev). Real users that haven't granted
    `scope` (or revoked it) get a 403 with a clear FR message.
    """

    def dependency(identity: AuthIdentity = Depends(get_current_user)) -> AuthIdentity:
        if identity.is_service:
            return identity
        if not is_consent_granted(identity, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Consentement requis : '{scope.value}'. "
                    "Activez ce consentement dans vos réglages Yalla avant d'utiliser cette fonctionnalité."
                ),
            )
        return identity

    return dependency
