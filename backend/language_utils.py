"""Language detection, resolution and localized labels."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cv_schema import StructuredCV

SUPPORTED_LANGUAGES: dict[str, str] = {
    "auto": "Auto (detectar)",
    "es": "Español",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "it": "Italiano",
    "ca": "Català",
}

UI_LANGUAGES: dict[str, str] = {
    "es": "Español",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "it": "Italiano",
    "ca": "Català",
}

LANGUAGE_MARKERS: dict[str, tuple[str, ...]] = {
    "es": (
        "experiencia",
        "educación",
        "formación",
        "habilidades",
        "idiomas",
        "objetivo profesional",
        "presentación",
        " currículum",
        "el ",
        " de ",
        " para ",
        " con ",
    ),
    "en": (
        "experience",
        "education",
        "skills",
        "summary",
        "languages",
        "professional objective",
        "resume",
        "curriculum vitae",
        " the ",
        " and ",
        " with ",
    ),
    "fr": (
        "expérience",
        "formation",
        "compétences",
        "langues",
        "objectif professionnel",
        "curriculum vitae",
        " le ",
        " des ",
        " et ",
    ),
    "de": (
        "erfahrung",
        "ausbildung",
        "fähigkeiten",
        "sprachen",
        "berufserfahrung",
        "lebenslauf",
        " und ",
        " der ",
        " die ",
    ),
    "pt": (
        "experiência",
        "formação",
        "habilidades",
        "idiomas",
        "objetivo profissional",
        "currículo",
        " para ",
        " com ",
    ),
    "it": (
        "esperienza",
        "formazione",
        "competenze",
        "lingue",
        "obiettivo professionale",
        "curriculum",
        " il ",
        " della ",
    ),
    "ca": (
        "experiència",
        "formació",
        "habilitats",
        "idiomes",
        "objectiu professional",
        "currículum",
        " el ",
        " de ",
    ),
}

SECTION_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "objective": "Objetivo profesional",
        "experience": "Experiencia profesional y proyectos personales",
        "projects": "Proyectos relevantes",
        "education": "Formación",
        "skills": "Habilidades técnicas",
        "languages": "Idiomas",
        "certifications": "Certificaciones",
    },
    "en": {
        "objective": "Professional Objective",
        "experience": "Professional Experience and Personal Projects",
        "projects": "Relevant Projects",
        "education": "Education",
        "skills": "Technical Skills",
        "languages": "Languages",
        "certifications": "Certifications",
    },
    "fr": {
        "objective": "Objectif professionnel",
        "experience": "Expérience professionnelle et projets personnels",
        "projects": "Projets pertinents",
        "education": "Formation",
        "skills": "Compétences techniques",
        "languages": "Langues",
        "certifications": "Certifications",
    },
    "de": {
        "objective": "Berufliches Ziel",
        "experience": "Berufserfahrung und persönliche Projekte",
        "projects": "Relevante Projekte",
        "education": "Ausbildung",
        "skills": "Technische Fähigkeiten",
        "languages": "Sprachen",
        "certifications": "Zertifizierungen",
    },
    "pt": {
        "objective": "Objetivo profissional",
        "experience": "Experiência profissional e projetos pessoais",
        "projects": "Projetos relevantes",
        "education": "Formação",
        "skills": "Competências técnicas",
        "languages": "Idiomas",
        "certifications": "Certificações",
    },
    "it": {
        "objective": "Obiettivo professionale",
        "experience": "Esperienza professionale e progetti personali",
        "projects": "Progetti rilevanti",
        "education": "Formazione",
        "skills": "Competenze tecniche",
        "languages": "Lingue",
        "certifications": "Certificazioni",
    },
    "ca": {
        "objective": "Objectiu professional",
        "experience": "Experiència professional i projectes personals",
        "projects": "Projectes rellevants",
        "education": "Formació",
        "skills": "Habilitats tècniques",
        "languages": "Idiomes",
        "certifications": "Certificacions",
    },
}


def normalize_language_code(value: str) -> str:
    code = (value or "").strip().lower()
    if code in ("auto", ""):
        return "auto"
    if code.startswith("es"):
        return "es"
    if code.startswith("en"):
        return "en"
    if code.startswith("fr"):
        return "fr"
    if code.startswith("de"):
        return "de"
    if code.startswith("pt"):
        return "pt"
    if code.startswith("it"):
        return "it"
    if code.startswith("ca"):
        return "ca"
    return code if code in SUPPORTED_LANGUAGES else "es"


def detect_language_hint(text: str) -> str:
    if not text or not text.strip():
        return ""

    sample = text[:8000].lower()
    scores: dict[str, int] = {}

    for lang, markers in LANGUAGE_MARKERS.items():
        score = 0
        for marker in markers:
            if marker in sample:
                score += sample.count(marker)
        if score:
            scores[lang] = score

    if not scores:
        return ""

    return max(scores, key=scores.get)


def resolve_output_language(
    output_language: str,
    *,
    cv: StructuredCV | None = None,
    job_description: str = "",
    translate_content: bool = False,
) -> str:
    requested = normalize_language_code(output_language)
    if requested != "auto":
        return requested

    job_lang = detect_language_hint(job_description)

    if translate_content and job_lang:
        return job_lang

    if cv and (cv.document_language or "").strip():
        return normalize_language_code(cv.document_language)

    if job_lang:
        return job_lang

    if cv:
        cv_blob = " ".join(
            filter(
                None,
                [
                    cv.summary,
                    " ".join(cv.skills),
                    " ".join(cv.languages),
                ],
            )
        )
        cv_lang = detect_language_hint(cv_blob)
        if cv_lang:
            return cv_lang

    return "es"


def get_section_labels(language: str) -> dict[str, str]:
    code = normalize_language_code(language)
    if code == "auto":
        code = "es"
    return SECTION_LABELS.get(code, SECTION_LABELS["en"])


def language_name(code: str) -> str:
    normalized = normalize_language_code(code)
    if normalized == "auto":
        return SUPPORTED_LANGUAGES["auto"]
    return SUPPORTED_LANGUAGES.get(normalized, normalized)


def parse_language_instruction() -> str:
    return (
        "MULTI-LANGUAGE CV PARSING:\n"
        "- The CV may be in Spanish, English, French, German, Portuguese, Italian, Catalan, or mixed.\n"
        "- Detect the primary language and set document_language to ISO 639-1 (es, en, fr, de, pt, it, ca).\n"
        "- PRESERVE all CV text in the ORIGINAL language. Do NOT translate while parsing.\n"
        "- Section headers in the source CV may be in any language — map content correctly.\n"
    )


def translation_instruction(translate_content: bool, target_language: str) -> str:
    if not translate_content:
        return (
            "LANGUAGE: Keep each field in a single language (the CV's original language). "
            "Do NOT output bilingual duplicates (e.g. Spanish line + English translation)."
        )
    code = normalize_language_code(target_language)
    if code == "auto":
        code = "en"
    name = language_name(code)
    return (
        f"TRANSLATION MODE: Rewrite ALL user-facing CV content into {name} ({code}) ONLY.\n"
        "- One language throughout — NEVER keep original text alongside translation.\n"
        "- NEVER duplicate bullets or skills in two languages.\n"
        "- Preserve facts, dates, company names, URLs, GitHub/LinkedIn links and technical terms.\n"
        f"- The final CV must read as if originally written in {name}."
    )


def output_language_instruction(language: str, *, translate_content: bool = False) -> str:
    code = normalize_language_code(language)
    if code == "auto":
        code = "es"
    name = language_name(code)
    if translate_content:
        return (
            f"OUTPUT LANGUAGE: {name} ({code}) only. "
            "Translated output — no bilingual duplicates."
        )
    return (
        f"OUTPUT LANGUAGE: Write all user-facing text fields in {name} ({code}). "
        "Keep proper nouns, company names, URLs and technical terms unchanged."
    )


def validate_output_language(value: str) -> str:
    code = normalize_language_code(value or "auto")
    if code != "auto" and code not in SUPPORTED_LANGUAGES:
        return "auto"
    return code


def validate_ui_language(value: str) -> str:
    code = normalize_language_code(value)
    if code == "auto":
        return "es"
    return code if code in UI_LANGUAGES else "es"
