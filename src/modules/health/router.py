from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from src.core.security import AuthIdentity, get_current_user
from src.modules.health.schemas import (
    HealthObservation,
    HealthObservationBatch,
    HealthObservationBatchResult,
    HealthObservationCreate,
    ObservationKind,
)
from src.modules.health.service import (
    latest_per_kind,
    list_observations,
    record_observation,
    record_observations_batch,
)

router = APIRouter()


@router.post(
    "/observations",
    response_model=HealthObservation,
    status_code=status.HTTP_201_CREATED,
)
def post_observation(
    payload: HealthObservationCreate,
    patient_id: int | None = Query(default=None, description="Optional; defaults to caller's profile. Required for service token."),
    identity: AuthIdentity = Depends(get_current_user),
):
    return record_observation(identity, payload, explicit_patient_id=patient_id)


@router.post(
    "/observations/batch",
    response_model=HealthObservationBatchResult,
    status_code=status.HTTP_201_CREATED,
)
def post_observations_batch(
    payload: HealthObservationBatch,
    patient_id: int | None = Query(default=None),
    identity: AuthIdentity = Depends(get_current_user),
):
    return record_observations_batch(identity, payload, explicit_patient_id=patient_id)


@router.get(
    "/observations/patient/{patient_id}",
    response_model=list[HealthObservation],
)
def read_observations(
    patient_id: int,
    kind: ObservationKind | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    identity: AuthIdentity = Depends(get_current_user),
):
    return list_observations(identity, patient_id, kind=kind, since=since, until=until, limit=limit)


@router.get(
    "/observations/patient/{patient_id}/latest",
    response_model=dict[str, HealthObservation],
)
def read_latest_observations(
    patient_id: int,
    identity: AuthIdentity = Depends(get_current_user),
):
    return latest_per_kind(identity, patient_id)
