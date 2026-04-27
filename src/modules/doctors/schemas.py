from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    DOCTOR = "doctor"
    EXPERT_PATIENT = "expert_patient"
    PATIENT = "patient"


class AccessUpdate(BaseModel):
    has_app_access: bool


class ExpertRoleUpdate(BaseModel):
    is_expert_patient: bool


class DoctorNoteCreate(BaseModel):
    content: str = Field(min_length=2, max_length=500)


class HealthMetric(BaseModel):
    label: str
    value: str
    trend: str = Field(description="Short trend label shown in the doctor dashboard.")


class PatientEvolutionPoint(BaseModel):
    recorded_on: date
    hba1c: float = Field(gt=0)
    weekly_activity_minutes: int = Field(ge=0)
    challenge_completion_rate: int = Field(ge=0, le=100)


class PatientProgress(BaseModel):
    activity_completion_rate: int = Field(ge=0, le=100)
    challenge_completion_rate: int = Field(ge=0, le=100)
    weekly_activity_minutes: int = Field(ge=0)
    last_check_in: date
    status: str


class PatientSummary(BaseModel):
    id: int
    full_name: str
    age: int
    primary_goal: str
    has_app_access: bool
    is_expert_patient: bool
    privacy_level: str
    progress: PatientProgress


class PatientDetail(PatientSummary):
    health_metrics: list[HealthMetric]
    evolution: list[PatientEvolutionPoint]
    active_challenges: list[str]
    care_notes: list[str]
    doctor_notes: list[str]


class DoctorProfile(BaseModel):
    id: int
    full_name: str
    specialty: str
    facility: str
    role: UserRole = UserRole.DOCTOR


class DoctorDashboard(BaseModel):
    doctor: DoctorProfile
    total_patients: int
    patients_with_access: int
    expert_patients: int
    patients_to_review: int
    patients: list[PatientSummary]
