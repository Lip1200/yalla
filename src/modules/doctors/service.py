from datetime import date

from fastapi import HTTPException, status

from src.core.database import supabase_client
from src.modules.doctors.schemas import (
    DoctorDashboard,
    DoctorProfile,
    HealthMetric,
    PatientDetail,
    PatientEvolutionPoint,
    PatientProgress,
    PatientSummary,
)

doctor = DoctorProfile(
    id=1,
    full_name="Dr. Nadia Benali",
    specialty="Endocrinologie et diabétologie",
    facility="Clinique Atlas Santé",
)


def get_doctor_dashboard(doctor_id: int) -> DoctorDashboard:
    current_doctor = _get_doctor(doctor_id)
    patient_summaries = list_patients(doctor_id)

    return DoctorDashboard(
        doctor=current_doctor,
        total_patients=len(patient_summaries),
        patients_with_access=sum(patient.has_app_access for patient in patient_summaries),
        expert_patients=sum(patient.is_expert_patient for patient in patient_summaries),
        patients_to_review=sum(patient.progress.status == "À revoir" for patient in patient_summaries),
        patients=patient_summaries,
    )


def list_patients(doctor_id: int) -> list[PatientSummary]:
    _get_doctor(doctor_id)
    response = supabase_client.table("profiles").select("*").order("id", desc=False).execute()
    return [_to_summary(_row_to_detail(row)) for row in response.data]


def get_patient(doctor_id: int, patient_id: int) -> PatientDetail:
    _get_doctor(doctor_id)
    response = supabase_client.table("profiles").select("*").eq("id", patient_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    return _apply_privacy_rules(_row_to_detail(response.data[0]))


def update_patient_access(doctor_id: int, patient_id: int, has_app_access: bool) -> PatientDetail:
    _get_doctor(doctor_id)
    response = supabase_client.table("profiles").select("*").eq("id", patient_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    update_resp = (
        supabase_client.table("profiles")
        .update({"has_app_access": has_app_access})
        .eq("id", patient_id)
        .execute()
    )
    return _apply_privacy_rules(_row_to_detail(update_resp.data[0]))


def update_expert_role(doctor_id: int, patient_id: int, is_expert_patient: bool) -> PatientDetail:
    _get_doctor(doctor_id)
    response = supabase_client.table("profiles").select("*").eq("id", patient_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    row = response.data[0]
    if is_expert_patient and not row["has_app_access"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un patient doit avoir accès à l'application avant de devenir patient expert.",
        )

    new_role = "expert_patient" if is_expert_patient else "patient"
    update_resp = (
        supabase_client.table("profiles")
        .update({"role": new_role})
        .eq("id", patient_id)
        .execute()
    )
    return _apply_privacy_rules(_row_to_detail(update_resp.data[0]))


def add_doctor_note(doctor_id: int, patient_id: int, content: str) -> PatientDetail:
    _get_doctor(doctor_id)
    response = supabase_client.table("profiles").select("*").eq("id", patient_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    row = response.data[0]
    current_notes = row.get("doctor_notes") or []
    updated_notes = [content.strip(), *current_notes]

    update_resp = (
        supabase_client.table("profiles")
        .update({"doctor_notes": updated_notes})
        .eq("id", patient_id)
        .execute()
    )
    return _apply_privacy_rules(_row_to_detail(update_resp.data[0]))


def delete_doctor_note(doctor_id: int, patient_id: int, note_index: int) -> PatientDetail:
    _get_doctor(doctor_id)
    response = supabase_client.table("profiles").select("*").eq("id", patient_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    row = response.data[0]
    current_notes = row.get("doctor_notes") or []
    if note_index < 0 or note_index >= len(current_notes):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note introuvable.")

    updated_notes = [note for index, note in enumerate(current_notes) if index != note_index]
    update_resp = (
        supabase_client.table("profiles")
        .update({"doctor_notes": updated_notes})
        .eq("id", patient_id)
        .execute()
    )
    return _apply_privacy_rules(_row_to_detail(update_resp.data[0]))


def _get_doctor(doctor_id: int) -> DoctorProfile:
    if doctor_id != doctor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médecin introuvable.")

    return doctor


def _row_to_detail(row: dict) -> PatientDetail:
    patient_id = row["id"]
    last_check_in_str = row.get("last_check_in")
    last_check_in_date = date.fromisoformat(last_check_in_str) if last_check_in_str else date.today()

    if patient_id == 101:
        health_metrics = [
            HealthMetric(label="HbA1c", value="7.1%", trend="-0.4 depuis 3 mois"),
            HealthMetric(label="IMC", value="29.8", trend="stable"),
            HealthMetric(label="Glycémie moyenne", value="1.42 g/L", trend="amélioration"),
        ]
        evolution = [
            PatientEvolutionPoint(recorded_on=date(2026, 1, 20), hba1c=7.6, weekly_activity_minutes=70, challenge_completion_rate=35),
            PatientEvolutionPoint(recorded_on=date(2026, 2, 20), hba1c=7.4, weekly_activity_minutes=95, challenge_completion_rate=46),
            PatientEvolutionPoint(recorded_on=date(2026, 3, 20), hba1c=7.2, weekly_activity_minutes=125, challenge_completion_rate=58),
            PatientEvolutionPoint(recorded_on=date(2026, 4, 20), hba1c=7.1, weekly_activity_minutes=145, challenge_completion_rate=64),
        ]
        active_challenges = [
            "20 minutes de marche, 5 jours sur 7",
            "Petit-déjeuner à indice glycémique bas",
        ]
    elif patient_id == 102:
        health_metrics = [
            HealthMetric(label="HbA1c", value="6.6%", trend="-0.6 depuis 3 mois"),
            HealthMetric(label="IMC", value="27.4", trend="baisse légère"),
            HealthMetric(label="Glycémie moyenne", value="1.18 g/L", trend="stable"),
        ]
        evolution = [
            PatientEvolutionPoint(recorded_on=date(2026, 1, 20), hba1c=7.2, weekly_activity_minutes=120, challenge_completion_rate=56),
            PatientEvolutionPoint(recorded_on=date(2026, 2, 20), hba1c=6.9, weekly_activity_minutes=155, challenge_completion_rate=68),
            PatientEvolutionPoint(recorded_on=date(2026, 3, 20), hba1c=6.7, weekly_activity_minutes=190, challenge_completion_rate=80),
            PatientEvolutionPoint(recorded_on=date(2026, 4, 20), hba1c=6.6, weekly_activity_minutes=210, challenge_completion_rate=88),
        ]
        active_challenges = [
            "Accompagner le groupe marche du samedi",
            "Partager 2 conseils repas équilibrés",
        ]
    else:
        health_metrics = [
            HealthMetric(label="HbA1c", value="8.2%", trend="+0.2 depuis 3 mois"),
            HealthMetric(label="IMC", value="31.1", trend="stable"),
            HealthMetric(label="Glycémie moyenne", value="1.68 g/L", trend="à surveiller"),
        ]
        evolution = [
            PatientEvolutionPoint(recorded_on=date(2026, 1, 20), hba1c=8.0, weekly_activity_minutes=55, challenge_completion_rate=28),
            PatientEvolutionPoint(recorded_on=date(2026, 2, 20), hba1c=8.1, weekly_activity_minutes=40, challenge_completion_rate=22),
            PatientEvolutionPoint(recorded_on=date(2026, 3, 20), hba1c=8.1, weekly_activity_minutes=30, challenge_completion_rate=20),
            PatientEvolutionPoint(recorded_on=date(2026, 4, 20), hba1c=8.2, weekly_activity_minutes=35, challenge_completion_rate=18),
        ]
        active_challenges = [
            "10 minutes de marche après le déjeuner",
        ]

    return PatientDetail(
        id=patient_id,
        full_name=row["full_name"],
        age=row["age"],
        primary_goal=row["primary_goal"],
        has_app_access=row["has_app_access"],
        is_expert_patient=row["role"] == "expert_patient",
        privacy_level=row["privacy_level"],
        progress=PatientProgress(
            activity_completion_rate=row["activity_completion_rate"],
            challenge_completion_rate=row["challenge_completion_rate"],
            weekly_activity_minutes=row["weekly_activity_minutes"],
            last_check_in=last_check_in_date,
            status=row["status"] or "En progrès",
        ),
        health_metrics=health_metrics,
        evolution=evolution,
        active_challenges=active_challenges,
        care_notes=row.get("care_notes") or [],
        doctor_notes=row.get("doctor_notes") or [],
    )


def _to_summary(patient: PatientDetail) -> PatientSummary:
    patient = _apply_privacy_rules(patient)
    return PatientSummary(
        id=patient.id,
        full_name=patient.full_name,
        age=patient.age,
        primary_goal=patient.primary_goal,
        has_app_access=patient.has_app_access,
        is_expert_patient=patient.is_expert_patient,
        privacy_level=patient.privacy_level,
        progress=patient.progress,
    )


def _apply_privacy_rules(patient: PatientDetail) -> PatientDetail:
    if patient.privacy_level != "Données privées":
        return patient

    return patient.model_copy(
        update={
            "progress": patient.progress.model_copy(
                update={
                    "activity_completion_rate": 0,
                    "challenge_completion_rate": 0,
                    "weekly_activity_minutes": 0,
                },
            ),
            "evolution": [],
            "active_challenges": [],
            "care_notes": [
                "Le patient a activé le mode données privées.",
                "Seules les données issues de la dernière consultation sont visibles.",
            ],
        },
    )
