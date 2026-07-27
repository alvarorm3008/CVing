"""Tests for language detection and adaptation settings."""

from cv_schema import ContactInfo, EducationItem, ExperienceItem, StructuredCV
from language_utils import (
    detect_language_hint,
    resolve_adaptation_settings,
    strip_bilingual_line,
)


def test_detect_english_job():
    text = """
    Software Engineer — Requirements
    We are looking for experience with Python, React and AWS.
    Responsibilities include building APIs and collaborating with the team.
    Bachelor's degree preferred. Full-time remote position.
    """
    assert detect_language_hint(text) == "en"


def test_detect_spanish_job():
    text = """
    Desarrollador Backend — Requisitos
    Buscamos experiencia con Python y bases de datos.
    Responsabilidades: desarrollar APIs y colaborar con el equipo.
    Se valora formación universitaria. Contrato indefinido.
    """
    assert detect_language_hint(text) == "es"


def test_offer_forces_translation_when_cv_differs():
    cv = StructuredCV(
        contact=ContactInfo(full_name="Ana"),
        document_language="es",
        summary="Ingeniera de software con experiencia en Python.",
        experience=[
            ExperienceItem(role="Desarrolladora", company="Acme", bullets=["Desarrollé APIs"])
        ],
        education=[EducationItem(degree="Grado en Informática", school="UPM")],
    )
    job = (
        "Backend Engineer role. Requirements: Python, FastAPI, AWS. "
        "Experience building APIs and working with the engineering team."
    )
    target, translate = resolve_adaptation_settings("auto", cv=cv, job_description=job)
    assert target == "en"
    assert translate is True


def test_same_language_no_translate():
    cv = StructuredCV(
        document_language="en",
        summary="Software engineer with Python experience.",
    )
    job = "Software Engineer. Requirements: Python and React experience with the team."
    target, translate = resolve_adaptation_settings("auto", cv=cv, job_description=job)
    assert target == "en"
    assert translate is False


def test_strip_bilingual_line():
    assert strip_bilingual_line("Ingeniero / Software Engineer") == "Ingeniero"
    assert strip_bilingual_line("Software Engineer") == "Software Engineer"
