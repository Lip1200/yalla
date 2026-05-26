from fastapi import APIRouter, Depends, HTTPException, status

from src.core.security import AuthIdentity, get_current_user, get_profile_for_identity
from src.modules.users.schemas import (
    Profile,
    ProfileCreate,
    ProfileReplace,
    ProfileUpdate,
)
from src.modules.users.service import (
    _row_to_profile,
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    replace_profile,
    update_profile,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[Profile])
def read_profiles(limit: int = 50, offset: int = 0):
    return list_profiles(limit=limit, offset=offset)


# /me MUST be declared before /{user_id} so FastAPI doesn't try to
# parse "me" as an int. Patient-app (#28) uses this to resolve the
# integer profile.id from the auth bearer token.
@router.get("/me", response_model=Profile)
def read_current_profile(identity: AuthIdentity = Depends(get_current_user)):
    if identity.is_service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'endpoint /me requiert un utilisateur authentifié, pas le service token.",
        )
    profile_row = get_profile_for_identity(identity)
    if not profile_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun profil rattaché à ce compte.",
        )
    return _row_to_profile(profile_row)


@router.get("/{user_id}", response_model=Profile)
def read_profile(user_id: int):
    return get_profile(user_id)


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
def add_profile(payload: ProfileCreate):
    return create_profile(payload)


@router.patch("/{user_id}", response_model=Profile)
def patch_profile(user_id: int, payload: ProfileUpdate):
    return update_profile(user_id, payload)


@router.put("/{user_id}", response_model=Profile)
def put_profile(user_id: int, payload: ProfileReplace):
    return replace_profile(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_profile(user_id: int):
    delete_profile(user_id)
