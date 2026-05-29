from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic import EmailStr


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
    age: int | None = None
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


class PatientAccountCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    # Both age and primary_goal are intentionally optional. When the
    # doctor leaves them blank, the patient fills them in via the
    # onboarding form on first launch (patient-app OnboardingScreen +
    # the `isFreshProfile` gate in App.js). A non-empty primary_goal
    # here suppresses that onboarding.
    age: int | None = Field(default=None, ge=0, le=120)
    primary_goal: str = Field(default="", max_length=180)


class PatientAccountCreated(BaseModel):
    patient: PatientSummary
    email: EmailStr
    invitation_url: str = Field(
        description=(
            "One-shot URL to send to the patient. They open it, choose their "
            "password, and only then a Supabase Auth user is created and "
            "linked to the pre-provisioned profile row. Replaces the old "
            "temporary_password field for security (cf. issue #33)."
        )
    )
    expires_at: datetime
    setup_status: str = Field(
        default="Lien d'invitation à transmettre au patient.",
        description="Human-readable status for the doctor UI.",
    )
