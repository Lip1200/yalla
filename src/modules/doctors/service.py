from datetime import date

from fastapi import HTTPException, status

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

patients: dict[int, PatientDetail] = {
    101: PatientDetail(
        id=101,
        full_name="Karim El Mansouri",
        age=54,
        primary_goal="Stabiliser la glycémie avec une marche quotidienne",
        has_app_access=True,
        is_expert_patient=False,
        privacy_level="Partage médical complet",
        progress=PatientProgress(
            activity_completion_rate=78,
            challenge_completion_rate=64,
            weekly_activity_minutes=145,
            last_check_in=date(2026, 4, 26),
            status="En progrès",
        ),
        health_metrics=[
            HealthMetric(label="HbA1c", value="7.1%", trend="-0.4 depuis 3 mois"),
            HealthMetric(label="IMC", value="29.8", trend="stable"),
            HealthMetric(label="Glycémie moyenne", value="1.42 g/L", trend="amélioration"),
        ],
        evolution=[
            PatientEvolutionPoint(recorded_on=date(2026, 1, 20), hba1c=7.6, weekly_activity_minutes=70, challenge_completion_rate=35),
            PatientEvolutionPoint(recorded_on=date(2026, 2, 20), hba1c=7.4, weekly_activity_minutes=95, challenge_completion_rate=46),
            PatientEvolutionPoint(recorded_on=date(2026, 3, 20), hba1c=7.2, weekly_activity_minutes=125, challenge_completion_rate=58),
            PatientEvolutionPoint(recorded_on=date(2026, 4, 20), hba1c=7.1, weekly_activity_minutes=145, challenge_completion_rate=64),
        ],
        active_challenges=[
            "20 minutes de marche, 5 jours sur 7",
            "Petit-déjeuner à indice glycémique bas",
        ],
        care_notes=[
            "Bonne régularité sur les défis d'activité physique.",
            "À encourager sur la planification des repas du soir.",
        ],
        doctor_notes=[],
    ),
    102: PatientDetail(
        id=102,
        full_name="Amina Saidi",
        age=47,
        primary_goal="Reprendre une activité physique progressive",
        has_app_access=True,
        is_expert_patient=True,
        privacy_level="Partage sélectif",
        progress=PatientProgress(
            activity_completion_rate=92,
            challenge_completion_rate=88,
            weekly_activity_minutes=210,
            last_check_in=date(2026, 4, 27),
            status="Très engagée",
        ),
        health_metrics=[
            HealthMetric(label="HbA1c", value="6.6%", trend="-0.6 depuis 3 mois"),
            HealthMetric(label="IMC", value="27.4", trend="baisse légère"),
            HealthMetric(label="Glycémie moyenne", value="1.18 g/L", trend="stable"),
        ],
        evolution=[
            PatientEvolutionPoint(recorded_on=date(2026, 1, 20), hba1c=7.2, weekly_activity_minutes=120, challenge_completion_rate=56),
            PatientEvolutionPoint(recorded_on=date(2026, 2, 20), hba1c=6.9, weekly_activity_minutes=155, challenge_completion_rate=68),
            PatientEvolutionPoint(recorded_on=date(2026, 3, 20), hba1c=6.7, weekly_activity_minutes=190, challenge_completion_rate=80),
            PatientEvolutionPoint(recorded_on=date(2026, 4, 20), hba1c=6.6, weekly_activity_minutes=210, challenge_completion_rate=88),
        ],
        active_challenges=[
            "Accompagner le groupe marche du samedi",
            "Partager 2 conseils repas équilibrés",
        ],
        care_notes=[
            "Profil pertinent pour accompagner de nouveaux patients.",
            "Très bonne capacité à motiver le groupe.",
        ],
        doctor_notes=[],
    ),
    103: PatientDetail(
        id=103,
        full_name="Youssef Haddad",
        age=61,
        primary_goal="Réduire la sédentarité après le déjeuner",
        has_app_access=False,
        is_expert_patient=False,
        privacy_level="Données privées",
        progress=PatientProgress(
            activity_completion_rate=24,
            challenge_completion_rate=18,
            weekly_activity_minutes=35,
            last_check_in=date(2026, 4, 19),
            status="À revoir",
        ),
        health_metrics=[
            HealthMetric(label="HbA1c", value="8.2%", trend="+0.2 depuis 3 mois"),
            HealthMetric(label="IMC", value="31.1", trend="stable"),
            HealthMetric(label="Glycémie moyenne", value="1.68 g/L", trend="à surveiller"),
        ],
        evolution=[
            PatientEvolutionPoint(recorded_on=date(2026, 1, 20), hba1c=8.0, weekly_activity_minutes=55, challenge_completion_rate=28),
            PatientEvolutionPoint(recorded_on=date(2026, 2, 20), hba1c=8.1, weekly_activity_minutes=40, challenge_completion_rate=22),
            PatientEvolutionPoint(recorded_on=date(2026, 3, 20), hba1c=8.1, weekly_activity_minutes=30, challenge_completion_rate=20),
            PatientEvolutionPoint(recorded_on=date(2026, 4, 20), hba1c=8.2, weekly_activity_minutes=35, challenge_completion_rate=18),
        ],
        active_challenges=[
            "10 minutes de marche après le déjeuner",
        ],
        care_notes=[
            "Accès application désactivé pour l'instant.",
            "Prévoir une relance lors du prochain rendez-vous.",
        ],
        doctor_notes=[],
    ),
}


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
    return [_to_summary(patient) for patient in patients.values()]


def get_patient(doctor_id: int, patient_id: int) -> PatientDetail:
    _get_doctor(doctor_id)
    if patient_id not in patients:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    return _apply_privacy_rules(patients[patient_id])


def update_patient_access(doctor_id: int, patient_id: int, has_app_access: bool) -> PatientDetail:
    _get_doctor(doctor_id)
    patient = patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    updated_patient = patient.model_copy(update={"has_app_access": has_app_access})
    patients[patient_id] = updated_patient
    return _apply_privacy_rules(updated_patient)


def update_expert_role(doctor_id: int, patient_id: int, is_expert_patient: bool) -> PatientDetail:
    _get_doctor(doctor_id)
    patient = patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    if is_expert_patient and not patient.has_app_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un patient doit avoir accès à l'application avant de devenir patient expert.",
        )

    updated_patient = patient.model_copy(update={"is_expert_patient": is_expert_patient})
    patients[patient_id] = updated_patient
    return _apply_privacy_rules(updated_patient)


def add_doctor_note(doctor_id: int, patient_id: int, content: str) -> PatientDetail:
    _get_doctor(doctor_id)
    patient = patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    updated_notes = [content.strip(), *patient.doctor_notes]
    updated_patient = patient.model_copy(update={"doctor_notes": updated_notes})
    patients[patient_id] = updated_patient
    return _apply_privacy_rules(updated_patient)


def delete_doctor_note(doctor_id: int, patient_id: int, note_index: int) -> PatientDetail:
    _get_doctor(doctor_id)
    patient = patients.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable.")

    if note_index < 0 or note_index >= len(patient.doctor_notes):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note introuvable.")

    updated_notes = [note for index, note in enumerate(patient.doctor_notes) if index != note_index]
    updated_patient = patient.model_copy(update={"doctor_notes": updated_notes})
    patients[patient_id] = updated_patient
    return _apply_privacy_rules(updated_patient)


def _get_doctor(doctor_id: int) -> DoctorProfile:
    if doctor_id != doctor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médecin introuvable.")

    return doctor


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
