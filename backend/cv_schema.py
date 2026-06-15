import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError


def _sanitize_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, dict):
        return {key: _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _sanitize_payload(payload: Any) -> Any:
    return _sanitize_value(payload)


class ContactInfo(BaseModel):
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""


class ProjectItem(BaseModel):
    title: str = ""
    url: str = ""
    description: str = ""


class ExperienceItem(BaseModel):
    role: str
    company: str
    location: str = ""
    period: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str
    school: str = ""
    period: str = ""


class StructuredCV(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    document_language: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str


class SkillMatch(BaseModel):
    requirement: str
    evidence: str = ""
    match_level: str = "covered"


class LearningRecommendation(BaseModel):
    skill: str
    priority: str = "medium"
    why_needed: str = ""
    how_to_learn: str = ""


class ATSMatchInfo(BaseModel):
    score: int
    honest_score: int = 0
    potential_score: int = 0
    adaptation_mode: str = "honest"
    target_role: str = ""
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    partial_keywords: list[str] = Field(default_factory=list)
    total_keywords: int = 0
    skills_you_have: list[SkillMatch] = Field(default_factory=list)
    skills_to_learn: list[LearningRecommendation] = Field(default_factory=list)
    optimization_notes: str = ""
    apply_recommendation: str = ""
    apply_recommendation_reason: str = ""
    cv_improvements: list[str] = Field(default_factory=list)
    page_count: int = 1


class WebSource(BaseModel):
    title: str = ""
    url: str = ""


class OfferResearch(BaseModel):
    company_name: str = ""
    job_title: str = ""
    location: str = ""
    company_description: str = ""
    industry: str = ""
    company_size: str = ""
    headquarters: str = ""
    culture_and_values: str = ""
    employee_reviews_summary: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    salary_estimate: str = ""
    salary_company_estimate: str = ""
    salary_location_market: str = ""
    salary_comparison: str = ""
    salary_notes: str = ""
    career_path: str = ""
    career_path_steps: list[str] = Field(default_factory=list)
    recent_news: str = ""
    application_tips: str = ""
    company_rating_summary: str = ""
    research_confidence: str = "medium"
    disclaimers: str = ""
    sources: list[WebSource] = Field(default_factory=list)


class CoverLetter(BaseModel):
    subject_line: str = ""
    greeting: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    full_text: str = ""
    tone: str = "profesional"
    personalization_hooks: list[str] = Field(default_factory=list)
    language: str = "es"


class FullApplicationResponse(BaseModel):
    cv: StructuredCV
    original_cv: StructuredCV
    template_id: str
    provider: str
    adaptation_mode: str
    pdf_base64: str
    pdf_filename: str
    ats_match: ATSMatchInfo
    boosted: bool = False
    research: OfferResearch
    cover_letter: CoverLetter
    personal_interests: str = ""


class ApplicationPackageResponse(BaseModel):
    research: OfferResearch
    cover_letter: CoverLetter
    provider: str = ""


AVAILABLE_TEMPLATES = [
    TemplateInfo(
        id="modern-pro",
        name="Modern Pro",
        description="Diseño visual minimalista con enlaces clicables.",
    ),
    TemplateInfo(
        id="ats-plain",
        name="ATS Plain",
        description="PDF plano ATS: una columna, texto seleccionable, sin gráficos.",
    ),
]


def _normalize_research_confidence(value: Any) -> str:
    if value is None or value == "":
        return "medium"
    if isinstance(value, (int, float)):
        score = int(value)
        if score <= 2:
            return "low"
        if score <= 3:
            return "medium"
        return "high"
    text = str(value).strip().lower()
    if text in ("low", "medium", "high", "bajo", "medio", "alto"):
        mapping = {"bajo": "low", "medio": "medium", "alto": "high"}
        return mapping.get(text, text)
    return "medium"


def _title_from_url(url: str) -> str:
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        return "Fuente"
    try:
        from urllib.parse import urlparse

        path = urlparse(cleaned).path.strip("/")
        if path:
            segment = path.split("/")[-1].replace("-", " ").replace("_", " ")
            if segment:
                return segment[:80]
    except Exception:
        pass
    return cleaned[:80]


def _normalize_web_sources(value: Any) -> list[dict[str, str]]:
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]

    sources: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str):
            url = item.strip()
            if url:
                sources.append({"title": _title_from_url(url), "url": url})
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("href") or item.get("link") or "").strip()
            title = str(item.get("title") or item.get("name") or "").strip()
            if url:
                sources.append({"title": title or _title_from_url(url), "url": url})
            elif title:
                sources.append({"title": title, "url": ""})
    return sources


def _normalize_string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _normalize_cover_letter_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    paragraphs = normalized.get("paragraphs")
    if isinstance(paragraphs, str):
        normalized["paragraphs"] = [
            p.strip() for p in re.split(r"\n\s*\n", paragraphs) if p.strip()
        ]
    elif paragraphs is not None:
        normalized["paragraphs"] = _normalize_string_list(paragraphs)

    if "personalization_hooks" in normalized:
        normalized["personalization_hooks"] = _normalize_string_list(
            normalized["personalization_hooks"]
        )

    for field in ("subject_line", "greeting", "closing", "full_text", "tone", "language"):
        if field in normalized and normalized[field] is not None:
            normalized[field] = str(normalized[field]).strip()

    return normalized


def _normalize_offer_research_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "research_confidence" in normalized:
        normalized["research_confidence"] = _normalize_research_confidence(
            normalized["research_confidence"]
        )
    if "sources" in normalized:
        normalized["sources"] = _normalize_web_sources(normalized["sources"])
    for field in ("pros", "cons", "career_path_steps"):
        if field in normalized:
            normalized[field] = _normalize_string_list(normalized[field])
    for field in (
        "company_name",
        "job_title",
        "location",
        "company_description",
        "industry",
        "company_size",
        "headquarters",
        "culture_and_values",
        "employee_reviews_summary",
        "salary_estimate",
        "salary_company_estimate",
        "salary_location_market",
        "salary_comparison",
        "salary_notes",
        "career_path",
        "recent_news",
        "application_tips",
        "company_rating_summary",
        "disclaimers",
    ):
        if field in normalized and normalized[field] is not None:
            normalized[field] = str(normalized[field]).strip()
    return normalized


def extract_json_object(raw: str) -> str:
    text = raw.strip()

    # 1. Bloque de código fenced ```json ... ``` o ``` ... ```
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
        if candidate:
            return candidate

    # 2. Extraer el JSON de mayor tamaño usando un stack de llaves
    best = ""
    i = 0
    while i < len(text):
        if text[i] == "{":
            depth = 0
            in_string = False
            escape_next = False
            for j in range(i, len(text)):
                ch = text[j]
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\" and in_string:
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[i : j + 1]
                        if len(candidate) > len(best):
                            best = candidate
                        break
        i += 1

    if best:
        return best

    return text


def _close_truncated_json(text: str) -> str:
    """Cierra llaves/corchetes abiertos en JSON truncado por límite de tokens."""
    in_string = False
    escape_next = False
    stack: list[str] = []
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]" and stack and stack[-1] == ch:
            stack.pop()
    repaired = text.rstrip()
    if in_string:
        repaired += '"'
    repaired += "".join(reversed(stack))
    return repaired


def _repair_json_text(text: str) -> str:
    repaired = text.strip()
    repaired = re.sub(r",\s*}", "}", repaired)
    repaired = re.sub(r",\s*]", "]", repaired)
    repaired = re.sub(r"\bNone\b", "null", repaired)
    repaired = re.sub(r"\bTrue\b", "true", repaired)
    repaired = re.sub(r"\bFalse\b", "false", repaired)
    return repaired


def _json_candidates(raw: str) -> list[str]:
    text = raw.strip()
    candidates: list[str] = []

    def add(candidate: str) -> None:
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add(extract_json_object(text))
    if "{" in text and "}" in text:
        add(text[text.find("{") : text.rfind("}") + 1])

    expanded: list[str] = []
    for candidate in candidates:
        expanded.append(candidate)
        expanded.append(_repair_json_text(candidate))
        expanded.append(_close_truncated_json(candidate))
        expanded.append(_repair_json_text(_close_truncated_json(candidate)))
    return expanded


def parse_json_model(raw: str, model_cls: type[BaseModel]) -> BaseModel:
    if not raw or not raw.strip():
        raise ValueError("The AI response was empty.")

    last_decode_error: json.JSONDecodeError | None = None
    last_validation_error: ValueError | None = None

    for candidate in _json_candidates(raw):
        try:
            payload: dict[str, Any] = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_decode_error = exc
            continue

        payload = _sanitize_payload(payload)
        if not isinstance(payload, dict):
            continue

        if model_cls is OfferResearch:
            payload = _normalize_offer_research_payload(payload)
        elif model_cls is CoverLetter:
            payload = _normalize_cover_letter_payload(payload)

        try:
            return model_cls.model_validate(payload)
        except ValidationError as exc:
            last_validation_error = ValueError(str(exc))

    if last_validation_error is not None:
        raise last_validation_error
    if last_decode_error is not None:
        raise ValueError("The AI response was not valid JSON.") from last_decode_error
    raise ValueError("The AI response was not valid JSON.")
