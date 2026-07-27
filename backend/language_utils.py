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
    # Distinctive phrases only — avoid shared particles (de/el/the/and) that confuse es/en/pt/ca
    "es": (
        "experiencia profesional",
        "formación",
        "habilidades",
        "requisitos",
        "responsabilidades",
        "buscamos",
        "desarrollador",
        "ingeniero",
        "contratación",
        "jornada",
        "años de experiencia",
        "puesto",
        "empresa",
        "currículum",
        "objetivo profesional",
        "conocimientos",
        "se valorará",
        "indispensable",
    ),
    "en": (
        "professional experience",
        "responsibilities",
        "requirements",
        "we are looking",
        "software engineer",
        "full-time",
        "part-time",
        "years of experience",
        "bachelor",
        "job description",
        "about the role",
        "what you'll do",
        "what we offer",
        "must have",
        "nice to have",
        "curriculum vitae",
        "resume",
    ),
    "fr": (
        "expérience professionnelle",
        "compétences",
        "formation",
        "poste",
        "nous recherchons",
        "années d'expérience",
        "cahier des charges",
        "curriculum vitae",
        "missions",
        "profil recherché",
    ),
    "de": (
        "berufserfahrung",
        "anforderungen",
        "aufgaben",
        "wir suchen",
        "lebenslauf",
        "vollzeit",
        "kenntnisse",
        "abschluss",
        "stellenbeschreibung",
    ),
    "pt": (
        "experiência profissional",
        "requisitos",
        "responsabilidades",
        "procuramos",
        "anos de experiência",
        "currículo",
        "formação académica",
        "habilidades técnicas",
    ),
    "it": (
        "esperienza professionale",
        "requisiti",
        "responsabilità",
        "cerchiamo",
        "anni di esperienza",
        "curriculum",
        "competenze",
        "laurea",
    ),
    "ca": (
        "experiència professional",
        "requisits",
        "responsabilitats",
        "busquem",
        "anys d'experiència",
        "currículum",
        "formació",
        "habilitats",
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

    sample = text[:10000].lower()
    scores: dict[str, float] = {}

    for lang, markers in LANGUAGE_MARKERS.items():
        score = 0.0
        for marker in markers:
            if marker in sample:
                # Longer markers are more distinctive
                weight = 2.0 if len(marker) >= 12 else 1.0
                score += sample.count(marker) * weight
        if score:
            scores[lang] = score

    if not scores:
        return ""

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_lang, best_score = ranked[0]
    if len(ranked) > 1 and ranked[1][1] >= best_score * 0.85:
        # Near-tie: prefer job-offer-ish English/Spanish markers already weighted
        return best_lang
    return best_lang


def resolve_cv_language(cv: StructuredCV | None) -> str:
    if cv is None:
        return ""

    cv_blob = " ".join(
        filter(
            None,
            [
                cv.summary,
                " ".join(cv.skills),
                " ".join(item.role + " " + " ".join(item.bullets) for item in cv.experience),
                " ".join(item.degree for item in cv.education),
            ],
        )
    )
    detected = detect_language_hint(cv_blob)
    declared = normalize_language_code(cv.document_language) if (cv.document_language or "").strip() else ""

    # Prefer content detection when it conflicts with a stale/wrong document_language
    if detected and declared and declared != "auto" and detected != declared:
        return detected
    if declared and declared != "auto":
        return declared
    return detected


def should_translate_cv(cv_lang: str, target_lang: str) -> bool:
    if not target_lang or target_lang == "auto":
        return False
    if not cv_lang:
        return True
    return cv_lang != target_lang


_BILINGUAL_SPLIT_RE = re.compile(
    r"\s+(?:/|–|—|\||·)\s+(?=[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÄÖß])"
)


def strip_bilingual_line(text: str) -> str:
    """Keep the first clause when a line looks like 'ES / EN' duplicates."""
    raw = (text or "").strip()
    if not raw:
        return ""
    parts = _BILINGUAL_SPLIT_RE.split(raw, maxsplit=1)
    if len(parts) == 2 and len(parts[0].split()) >= 1 and len(parts[1].split()) >= 1:
        # Only strip when both sides look like full phrases (not "CI/CD")
        left, right = parts[0].strip(), parts[1].strip()
        if len(left) >= 8 and len(right) >= 8:
            return left
    return raw


def sanitize_cv_language_fields(cv: "StructuredCV") -> "StructuredCV":
    """Remove bilingual duplicate phrases from user-facing fields."""
    from cv_schema import StructuredCV

    if not isinstance(cv, StructuredCV):
        return cv

    updated = cv.model_copy(deep=True)
    updated.summary = strip_bilingual_line(updated.summary)
    if updated.contact.headline:
        updated.contact.headline = strip_bilingual_line(updated.contact.headline)
    updated.skills = [strip_bilingual_line(s) for s in updated.skills if strip_bilingual_line(s)]
    updated.certifications = [
        strip_bilingual_line(c) for c in updated.certifications if strip_bilingual_line(c)
    ]
    updated.languages = [strip_bilingual_line(lang) for lang in updated.languages if strip_bilingual_line(lang)]
    for item in updated.experience:
        item.role = strip_bilingual_line(item.role)
        item.bullets = [strip_bilingual_line(b) for b in item.bullets if strip_bilingual_line(b)]
    for item in updated.education:
        item.degree = strip_bilingual_line(item.degree)
    return updated


def resolve_adaptation_settings(
    output_language: str = "auto",
    *,
    cv: StructuredCV | None = None,
    job_description: str = "",
) -> tuple[str, bool]:
    """Job offer language wins. Translate full CV when it differs from the source."""
    requested = normalize_language_code(output_language)
    job_lang = detect_language_hint(job_description)
    cv_lang = resolve_cv_language(cv)

    if requested != "auto":
        target = requested
    elif job_lang:
        target = job_lang
    elif cv_lang:
        target = cv_lang
    else:
        target = "es"

    translate = should_translate_cv(cv_lang, target)
    return target, translate


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
    if job_lang:
        return job_lang

    if cv and (cv.document_language or "").strip():
        return normalize_language_code(cv.document_language)

    cv_lang = resolve_cv_language(cv)
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
            "LANGUAGE: CV and offer are already in the same language. "
            "Keep each field in that single language. "
            "Do NOT output bilingual duplicates (e.g. Spanish line + English translation)."
        )
    code = normalize_language_code(target_language)
    if code == "auto":
        code = "en"
    name = language_name(code)
    return (
        f"TRANSLATION MODE: Rewrite ALL user-facing CV content into {name} ({code}) ONLY.\n"
        "- Translate summary, role titles, bullet narratives, skill labels and education lines.\n"
        "- Section-equivalent content in JSON must read naturally in the target language.\n"
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
