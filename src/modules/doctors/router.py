from fastapi import APIRouter, Depends

from src.core.security import get_current_user
from src.modules.doctors.schemas import (
    AccessUpdate,
    DoctorDashboard,
    DoctorNoteCreate,
    ExpertRoleUpdate,
    PatientDetail,
    PatientSummary,
)
from src.modules.doctors.service import (
    add_doctor_note,
    delete_doctor_note,
    get_doctor_dashboard,
    get_patient,
    list_patients,
    update_expert_role,
    update_patient_access,
)

# Secure router endpoints via global dependency evaluation
router = APIRouter(dependencies=[Depends(get_current_user)])



@router.get("/{doctor_id}/dashboard", response_model=DoctorDashboard)
def read_dashboard(doctor_id: int):
    return get_doctor_dashboard(doctor_id)


@router.get("/{doctor_id}/patients", response_model=list[PatientSummary])
def read_patients(doctor_id: int):
    return list_patients(doctor_id)


@router.get("/{doctor_id}/patients/{patient_id}", response_model=PatientDetail)
def read_patient(doctor_id: int, patient_id: int):
    return get_patient(doctor_id, patient_id)


@router.patch("/{doctor_id}/patients/{patient_id}/access", response_model=PatientDetail)
def change_patient_access(doctor_id: int, patient_id: int, payload: AccessUpdate):
    return update_patient_access(doctor_id, patient_id, payload.has_app_access)


@router.patch("/{doctor_id}/patients/{patient_id}/expert-role", response_model=PatientDetail)
def change_expert_role(doctor_id: int, patient_id: int, payload: ExpertRoleUpdate):
    return update_expert_role(doctor_id, patient_id, payload.is_expert_patient)


@router.post("/{doctor_id}/patients/{patient_id}/notes", response_model=PatientDetail)
def create_doctor_note(doctor_id: int, patient_id: int, payload: DoctorNoteCreate):
    return add_doctor_note(doctor_id, patient_id, payload.content)


@router.delete("/{doctor_id}/patients/{patient_id}/notes/{note_index}", response_model=PatientDetail)
def remove_doctor_note(doctor_id: int, patient_id: int, note_index: int):
    return delete_doctor_note(doctor_id, patient_id, note_index)
