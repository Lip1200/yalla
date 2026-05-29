"""Unit tests for the row → schema mappers in `doctors/service.py`.

`_row_to_detail` builds a `PatientDetail` from a profiles row plus a
seeded set of health/evolution/challenge data that differs per
patient_id (101, 102 → bespoke; everything else → 'other' fallback).
`_to_summary` flattens it and routes through `_apply_privacy_rules`
along the way.
"""

from datetime import date

import pytest

from src.modules.doctors.service import _row_to_detail, _to_summary


def _row(**overrides):
    row = {
        "id": 200,
        "full_name": "Test Patient",
        "age": 45,
        "primary_goal": "Marcher 30 min/jour",
        "has_app_access": True,
        "role": "patient",
        "privacy_level": "Partage sélectif",
        "activity_completion_rate": 78,
        "challenge_completion_rate": 64,
        "weekly_activity_minutes": 145,
        "last_check_in": "2026-05-01",
        "status": "En progrès",
        "care_notes": [],
        "doctor_notes": [],
    }
    row.update(overrides)
    return row


class TestRowToDetail:
    def test_patient_101_gets_seeded_data(self) -> None:
        detail = _row_to_detail(_row(id=101))
        assert detail.id == 101
        assert len(detail.health_metrics) == 3
        labels = {m.label for m in detail.health_metrics}
        assert {"HbA1c", "IMC", "Glycémie moyenne"} == labels
        assert len(detail.evolution) == 4
        assert detail.active_challenges == [
            "20 minutes de marche, 5 jours sur 7",
            "Petit-déjeuner à indice glycémique bas",
        ]

    def test_patient_102_seed_differs_from_101(self) -> None:
        a = _row_to_detail(_row(id=101))
        b = _row_to_detail(_row(id=102, role="expert_patient"))
        # Demo seed differs per patient — 102 is the expert with the
        # better HbA1c trend.
        a_hba1c = next(m.value for m in a.health_metrics if m.label == "HbA1c")
        b_hba1c = next(m.value for m in b.health_metrics if m.label == "HbA1c")
        assert a_hba1c != b_hba1c

    def test_other_patient_id_uses_fallback_seed(self) -> None:
        detail = _row_to_detail(_row(id=999))
        # The 'else' branch — generic seeded values used when no
        # bespoke profile exists.
        labels = [m.label for m in detail.health_metrics]
        assert "HbA1c" in labels
        assert len(detail.active_challenges) == 1

    def test_is_expert_patient_derived_from_role(self) -> None:
        patient = _row_to_detail(_row(role="patient"))
        expert = _row_to_detail(_row(role="expert_patient"))
        assert patient.is_expert_patient is False
        assert expert.is_expert_patient is True

    def test_last_check_in_iso_parsed(self) -> None:
        detail = _row_to_detail(_row(last_check_in="2026-04-15"))
        assert detail.progress.last_check_in == date(2026, 4, 15)

    def test_last_check_in_defaults_to_today_when_missing(self) -> None:
        detail = _row_to_detail(_row(last_check_in=None))
        assert detail.progress.last_check_in == date.today()

    def test_status_defaults_to_en_progres_when_empty(self) -> None:
        detail = _row_to_detail(_row(status=""))
        assert detail.progress.status == "En progrès"

    def test_doctor_notes_pass_through(self) -> None:
        notes = ["Note A", "Note B"]
        detail = _row_to_detail(_row(doctor_notes=notes))
        assert detail.doctor_notes == notes

    def test_care_notes_pass_through(self) -> None:
        notes = ["Soin A"]
        detail = _row_to_detail(_row(care_notes=notes))
        assert detail.care_notes == notes


class TestToSummary:
    def test_summary_drops_detail_fields(self) -> None:
        detail = _row_to_detail(_row())
        summary = _to_summary(detail)
        # PatientSummary doesn't have health_metrics, evolution, etc.
        assert not hasattr(summary, "health_metrics")
        assert summary.id == detail.id
        assert summary.full_name == detail.full_name
        assert summary.age == detail.age
        assert summary.primary_goal == detail.primary_goal

    def test_summary_applies_privacy_rules(self) -> None:
        # Verify _to_summary routes through _apply_privacy_rules — when
        # privacy_level is 'Données privées' the progress numbers are
        # zeroed even on the summary surface.
        detail = _row_to_detail(_row(privacy_level="Données privées"))
        summary = _to_summary(detail)
        assert summary.progress.activity_completion_rate == 0
        assert summary.progress.weekly_activity_minutes == 0
        assert summary.progress.status == "Mode privé"

    def test_summary_passes_through_when_privacy_open(self) -> None:
        detail = _row_to_detail(_row(privacy_level="Partage complet"))
        summary = _to_summary(detail)
        assert summary.progress.activity_completion_rate == 78
        assert summary.progress.weekly_activity_minutes == 145
