from fastapi import APIRouter, Depends, status

from src.core.security import get_current_user
from src.modules.challenges.schemas import (
    Challenge,
    ChallengeCategory,
    ChallengeCreate,
    ChallengeDifficulty,
    ChallengeStatus,
    ChallengeUpdate,
    PatientChallenge,
    PatientChallengeAssign,
    PatientChallengeProgressUpdate,
)
from src.modules.challenges.service import (
    assign_to_patient,
    create_challenge,
    delete_challenge,
    get_challenge,
    list_challenges,
    list_patient_challenges,
    update_challenge,
    update_patient_challenge,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[Challenge])
def read_challenges(
    category: ChallengeCategory | None = None,
    difficulty: ChallengeDifficulty | None = None,
    templates_only: bool = False,
):
    return list_challenges(
        category=category, difficulty=difficulty, templates_only=templates_only
    )


@router.get("/{challenge_id}", response_model=Challenge)
def read_challenge(challenge_id: int):
    return get_challenge(challenge_id)


@router.post("/", response_model=Challenge, status_code=status.HTTP_201_CREATED)
def add_challenge(payload: ChallengeCreate):
    return create_challenge(payload)


@router.patch("/{challenge_id}", response_model=Challenge)
def patch_challenge(challenge_id: int, payload: ChallengeUpdate):
    return update_challenge(challenge_id, payload)


@router.delete("/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_challenge(challenge_id: int):
    delete_challenge(challenge_id)


@router.post(
    "/assignments",
    response_model=PatientChallenge,
    status_code=status.HTTP_201_CREATED,
)
def assign_challenge(payload: PatientChallengeAssign):
    return assign_to_patient(payload)


@router.get("/assignments/patient/{patient_id}", response_model=list[PatientChallenge])
def read_patient_challenges(
    patient_id: int, status_filter: ChallengeStatus | None = None
):
    return list_patient_challenges(patient_id, status_filter=status_filter)


@router.patch("/assignments/{assignment_id}", response_model=PatientChallenge)
def patch_patient_challenge(
    assignment_id: int, payload: PatientChallengeProgressUpdate
):
    return update_patient_challenge(assignment_id, payload)
