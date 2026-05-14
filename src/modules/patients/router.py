from fastapi import APIRouter, Depends

from src.core.security import get_current_user
from src.modules.patients.schemas import (
    Conversation,
    FeedPost,
    FeedPostCreate,
    PatientProfile,
    PatientSettings,
    PrivacySettingsUpdate,
    Progression,
    RestaurantRecommendation,
    SupportSession,
    SupportSessionCreate,
)
from src.modules.patients.service import (
    create_post,
    create_session,
    get_profile,
    get_progression,
    get_settings,
    list_conversations,
    list_feed,
    list_restaurants,
    list_sessions,
    update_privacy,
)

# Secure router endpoints via global dependency evaluation
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{patient_id}/profile", response_model=PatientProfile)
def read_profile(patient_id: int):
    return get_profile(patient_id)


@router.get("/{patient_id}/feed", response_model=list[FeedPost])
def read_feed(patient_id: int, limit: int = 20, offset: int = 0):
    return list_feed(patient_id, limit=limit, offset=offset)



@router.post("/{patient_id}/feed", response_model=FeedPost)
def add_feed_post(patient_id: int, payload: FeedPostCreate):
    return create_post(patient_id, payload)


@router.get("/{patient_id}/progression", response_model=Progression)
def read_progression(patient_id: int):
    return get_progression(patient_id)


@router.get("/{patient_id}/restaurants", response_model=list[RestaurantRecommendation])
def read_restaurants(patient_id: int):
    return list_restaurants(patient_id)


@router.get("/{patient_id}/messages", response_model=list[Conversation])
def read_messages(patient_id: int):
    return list_conversations(patient_id)


@router.get("/{patient_id}/settings", response_model=PatientSettings)
def read_settings(patient_id: int):
    return get_settings(patient_id)


@router.patch("/{patient_id}/settings/privacy", response_model=PatientSettings)
def change_privacy(patient_id: int, payload: PrivacySettingsUpdate):
    return update_privacy(patient_id, payload)


@router.get("/{patient_id}/sessions", response_model=list[SupportSession])
def read_sessions(patient_id: int):
    return list_sessions(patient_id)


@router.post("/{patient_id}/sessions", response_model=SupportSession)
def add_session(patient_id: int, payload: SupportSessionCreate):
    return create_session(patient_id, payload)
