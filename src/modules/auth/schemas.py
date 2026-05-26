from pydantic import BaseModel, EmailStr, Field


class PatientSignupRequest(BaseModel):
    """Public patient signup. The server hardcodes role='patient' — there
    is no `role` field on this schema so a client cannot escalate to
    doctor by tampering with the payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)


class DoctorSignupRequest(BaseModel):
    """Doctor signup. Same anti-escalation rule: the server hardcodes
    role='doctor', the client cannot pass it. Specialty + facility are
    accepted because they are profile data, not authorization fields."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    specialty: str = Field(default="", max_length=120)
    facility: str = Field(default="", max_length=160)


# Backward-compatibility alias for the legacy /api/auth/signup endpoint —
# which historically created doctor accounts only. New callers should use
# the explicit DoctorSignupRequest / PatientSignupRequest types instead.
SignupRequest = DoctorSignupRequest


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class SetupPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=72)


class AuthUser(BaseModel):
    id: str
    email: EmailStr | None = None
    full_name: str | None = None
    specialty: str | None = None
    facility: str | None = None


class AuthSession(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    user: AuthUser
