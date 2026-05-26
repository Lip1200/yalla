from fastapi import APIRouter, Depends, status

from src.core.security import AuthIdentity, get_current_user
from src.modules.consents.schemas import (
    ConsentGrant,
    ConsentRecord,
    ConsentScope,
    ConsentScopeDescriptor,
    ConsentStatus,
)
from src.modules.consents.service import (
    list_my_consents,
    list_scopes,
    record_consent,
    revoke_consent,
)

router = APIRouter()


@router.get("/scopes", response_model=list[ConsentScopeDescriptor])
def read_scopes():
    """Static catalogue of consent scopes + human labels. No auth needed —
    the frontend uses this before login to render the onboarding form."""
    return list_scopes()


@router.post(
    "/",
    response_model=ConsentRecord,
    status_code=status.HTTP_201_CREATED,
)
def post_consent(
    payload: ConsentGrant,
    identity: AuthIdentity = Depends(get_current_user),
):
    return record_consent(identity, payload)


@router.get("/me", response_model=list[ConsentStatus])
def read_my_consents(identity: AuthIdentity = Depends(get_current_user)):
    return list_my_consents(identity)


@router.delete("/{scope}", response_model=ConsentRecord)
def delete_consent(
    scope: ConsentScope,
    identity: AuthIdentity = Depends(get_current_user),
):
    return revoke_consent(identity, scope)
