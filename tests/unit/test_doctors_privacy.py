"""Unit tests for the privacy filter applied on the doctor-facing
patient detail view.

The function is pure — it takes a `PatientDetail` Pydantic model and
returns a possibly-masked copy. No DB, no FastAPI. Tests cover the
two code paths (privacy_level == 'Données privées' vs other) and the
specific fields masked / preserved per #53.
"""

from datetime import date

import pytest

from src.modules.doctors.service import _apply_privacy_rules
from src.modules.doctors.schemas import (
    HealthMetric,
    PatientDetail,
    PatientEvolutionPoint,
    PatientProgress,
)


def _build_patient(privacy_level: str) -> PatientDetail:
    return PatientDetail(
        id=42,
        full_name="Test Patient",
        age=45,
        primary_goal="Marcher 30 min/jour",
        has_app_access=True,
        is_expert_patient=False,
        privacy_level=privacy_level,
        progress=PatientProgress(
            activity_completion_rate=78,
            challenge_completion_rate=64,
            weekly_activity_minutes=145,
            last_check_in=date(2026, 5, 1),
            status="En progrès",
        ),
        health_metrics=[
            HealthMetric(label="HbA1c", value="8.2%", trend="+0.2"),
            HealthMetric(label="IMC", value="31.1", trend="stable"),
        ],
        evolution=[
            PatientEvolutionPoint(
                recorded_on=date(2026, 4, 20),
                hba1c=8.2,
                weekly_activity_minutes=35,
                challenge_completion_rate=18,
            ),
        ],
        active_challenges=["10 min de marche", "Petit-déj équilibré"],
        care_notes=["Patient a partagé son journal alimentaire."],
        doctor_notes=["Reprendre dans 2 semaines."],
    )


class TestApplyPrivacyRules:
    """Covers the two branches of _apply_privacy_rules + the fields it
    leaves alone for clinical visibility."""

    def test_partage_selectif_passes_through_untouched(self) -> None:
        patient = _build_patient(privacy_level="Partage sélectif")
        result = _apply_privacy_rules(patient)
        # No masking — every field must equal the input.
        assert result.model_dump() == patient.model_dump()

    def test_donnees_privees_masks_self_tracked_progress(self) -> None:
        patient = _build_patient(privacy_level="Données privées")
        result = _apply_privacy_rules(patient)
        assert result.progress.activity_completion_rate == 0
        assert result.progress.challenge_completion_rate == 0
        assert result.progress.weekly_activity_minutes == 0
        assert result.progress.status == "Mode privé"

    def test_donnees_privees_clears_active_challenges(self) -> None:
        patient = _build_patient(privacy_level="Données privées")
        result = _apply_privacy_rules(patient)
        assert result.active_challenges == []

    def test_donnees_privees_keeps_health_metrics_visible(self) -> None:
        """Clinical data — HbA1c, IMC, glycémie — stays visible per the
        product spec; only self-tracked lifestyle data is masked."""
        patient = _build_patient(privacy_level="Données privées")
        result = _apply_privacy_rules(patient)
        assert len(result.health_metrics) == 2
        assert result.health_metrics[0].label == "HbA1c"

    def test_donnees_privees_masks_self_tracking_in_evolution_points(self) -> None:
        patient = _build_patient(privacy_level="Données privées")
        result = _apply_privacy_rules(patient)
        assert len(result.evolution) == 1
        point = result.evolution[0]
        assert point.weekly_activity_minutes == 0
        assert point.challenge_completion_rate == 0
        # hba1c is clinical → preserved
        assert point.hba1c == 8.2

    def test_donnees_privees_replaces_care_notes_with_explainer(self) -> None:
        patient = _build_patient(privacy_level="Données privées")
        result = _apply_privacy_rules(patient)
        assert len(result.care_notes) == 2
        assert "Les données de suivi" in result.care_notes[1]

    def test_donnees_privees_keeps_doctor_notes_intact(self) -> None:
        """Doctor's own notes survive — they're the doctor's record, not
        patient-controlled content."""
        patient = _build_patient(privacy_level="Données privées")
        result = _apply_privacy_rules(patient)
        assert result.doctor_notes == ["Reprendre dans 2 semaines."]

    def test_donnees_privees_returns_a_copy_not_mutated_input(self) -> None:
        patient = _build_patient(privacy_level="Données privées")
        original_progress = patient.progress.model_dump()
        _apply_privacy_rules(patient)
        # Input is unchanged.
        assert patient.progress.model_dump() == original_progress

    @pytest.mark.parametrize(
        "privacy_level",
        [
            "",
            "Partage complet",
            "Données limitées",
            "Partage sélectif",
        ],
    )
    def test_non_private_levels_are_pass_through(self, privacy_level: str) -> None:
        patient = _build_patient(privacy_level=privacy_level)
        result = _apply_privacy_rules(patient)
        assert result.progress.activity_completion_rate == 78
        assert result.active_challenges == ["10 min de marche", "Petit-déj équilibré"]
