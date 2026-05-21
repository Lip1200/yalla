from fastapi import APIRouter, Depends, status

from src.core.security import get_current_user
from src.modules.users.schemas import (
    Profile,
    ProfileCreate,
    ProfileReplace,
    ProfileUpdate,
)
from src.modules.users.service import (
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
