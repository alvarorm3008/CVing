"""
ATS-optimized CV generator (plain layout, selectable text, no graphics).

Uses ReportLab — no browser dependency, reliable for production PDF bytes.
Helvetica is used as the standard ATS-safe sans-serif (metric equivalent to Arial).
"""

from __future__ import annotations

import os
import re
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from cv_schema import StructuredCV

INCH = inch
MARGIN = 0.75 * INCH
FONT_BODY = 11
FONT_NAME = 16
FONT_SECTION = 12
LEADING = FONT_BODY * 1.15
BULLET = "\u2022"  # •

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "ene": "01", "abr": "04", "ago": "08", "dic": "12",
}

SECTIONS = {
    "en": {
        "summary": "Professional Summary",
        "experience": "Work Experience",
        "projects": "Projects",
        "education": "Education",
        "skills": "Technical Skills",
        "skill_labels": {
            "languages": "Languages",
            "frameworks": "Frameworks",
            "tools": "Tools",
            "cloud": "Cloud",
            "data_ai": "Data & AI",
        },
        "present": "Present",
    },
    "es": {
        "summary": "Resumen Profesional",
        "experience": "Experiencia Laboral",
        "projects": "Proyectos",
        "education": "Educación",
        "skills": "Habilidades Técnicas",
        "skill_labels": {
            "languages": "Lenguajes",
            "frameworks": "Frameworks",
            "tools": "Herramientas",
            "cloud": "Cloud",
            "data_ai": "Datos e IA",
        },
        "present": "Actualidad",
    },
}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [_safe_str(item) for item in value if _safe_str(item)]
    return []


def _detect_language(cv_data: dict) -> str:
    lang = _safe_str(cv_data.get("language") or cv_data.get("document_language")).lower()
    if lang.startswith("es"):
        return "es"
    if lang.startswith("en"):
        return "en"
    blob = " ".join(
        [
            _safe_str(cv_data.get("summary")),
            _safe_str((cv_data.get("personal") or {}).get("title")),
        ]
    ).lower()
    spanish_markers = ("experiencia", "formación", "habilidades", "desarrollador", "ingeniero")
    if any(marker in blob for marker in spanish_markers):
        return "es"
    return "en"


def _normalize_date_token(token: str, *, present_label: str) -> str:
    raw = _safe_str(token)
    if not raw:
        return ""
    lower = raw.lower()
    if lower in {"present", "actualidad", "actual", "current", "now", "hoy"}:
        return present_label

    mm_yyyy = re.match(r"^(\d{1,2})[/.-](\d{4})$", raw)
    if mm_yyyy:
        month = int(mm_yyyy.group(1))
        if 1 <= month <= 12:
            return f"{month:02d}/{mm_yyyy.group(2)}"

    yyyy_mm = re.match(r"^(\d{4})[/.-](\d{1,2})$", raw)
    if yyyy_mm:
        month = int(yyyy_mm.group(2))
        if 1 <= month <= 12:
            return f"{month:02d}/{yyyy_mm.group(1)}"

    if re.fullmatch(r"\d{4}", raw):
        return f"01/{raw}"

    month_year = re.match(
        r"^([A-Za-zÁÉÍÓÚáéíóú]{3,9})[.\s/-]+(\d{4})$",
        raw,
        re.IGNORECASE,
    )
    if month_year:
        month_key = month_year.group(1).lower()[:3]
        month = MONTH_MAP.get(month_key)
        if month:
            return f"{month}/{month_year.group(2)}"

    return raw


def format_date_range(start: str, end: str, *, language: str = "en") -> str:
    labels = SECTIONS[language if language in SECTIONS else "en"]
    start_fmt = _normalize_date_token(start, present_label=labels["present"])
    end_fmt = _normalize_date_token(end, present_label=labels["present"])
    if start_fmt and end_fmt:
        return f"{start_fmt} - {end_fmt}"
    return start_fmt or end_fmt


def _parse_period_to_dates(period: str, *, language: str = "en") -> str:
    period = _safe_str(period)
    if not period:
        return ""
    labels = SECTIONS[language if language in SECTIONS else "en"]
    parts = re.split(r"\s*[-–—to/a]+\s*", period, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return format_date_range(parts[0], parts[1], language=language)
    return _normalize_date_token(period, present_label=labels["present"])


def _estimate_years_experience(experience: list[dict]) -> float:
    total_months = 0
    for item in experience:
        start = _safe_str(item.get("start_date"))
        end = _safe_str(item.get("end_date"))
        for token, is_end in ((start, False), (end, True)):
            if not token:
                continue
            lower = token.lower()
            if lower in {"present", "actualidad", "current"}:
                if is_end:
                    total_months += 12
                continue
            year_match = re.search(r"(\d{4})", token)
            if year_match:
                total_months += 6
    return total_months / 12.0


def _paragraph_styles(*, compact: bool = False) -> dict[str, ParagraphStyle]:
    body_size = 10 if compact else FONT_BODY
    leading = body_size * 1.15
    return {
        "name": ParagraphStyle(
            "ATSName",
            fontName="Helvetica-Bold",
            fontSize=FONT_NAME if not compact else 14,
            textColor=colors.black,
            spaceAfter=4,
            alignment=TA_LEFT,
            leading=FONT_NAME * 1.1,
        ),
        "title": ParagraphStyle(
            "ATSTitle",
            fontName="Helvetica",
            fontSize=body_size,
            textColor=colors.black,
            spaceAfter=4,
            alignment=TA_LEFT,
            leading=leading,
        ),
        "contact": ParagraphStyle(
            "ATSContact",
            fontName="Helvetica",
            fontSize=body_size,
            textColor=colors.black,
            spaceAfter=10,
            alignment=TA_LEFT,
            leading=leading,
        ),
        "section": ParagraphStyle(
            "ATSSection",
            fontName="Helvetica-Bold",
            fontSize=FONT_SECTION if not compact else 11,
            textColor=colors.black,
            spaceBefore=6,
            spaceAfter=2,
            alignment=TA_LEFT,
            leading=FONT_SECTION * 1.1,
        ),
        "body": ParagraphStyle(
            "ATSBody",
            fontName="Helvetica",
            fontSize=body_size,
            textColor=colors.black,
            spaceAfter=4,
            alignment=TA_LEFT,
            leading=leading,
        ),
        "role": ParagraphStyle(
            "ATSRole",
            fontName="Helvetica-Bold",
            fontSize=body_size,
            textColor=colors.black,
            spaceAfter=2,
            alignment=TA_LEFT,
            leading=leading,
        ),
        "meta": ParagraphStyle(
            "ATSMeta",
            fontName="Helvetica",
            fontSize=body_size,
            textColor=colors.black,
            spaceAfter=3,
            alignment=TA_LEFT,
            leading=leading,
        ),
        "bullet": ParagraphStyle(
            "ATSBullet",
            fontName="Helvetica",
            fontSize=body_size,
            textColor=colors.black,
            leftIndent=12,
            spaceAfter=2,
            alignment=TA_LEFT,
            leading=leading,
        ),
    }


def _section_block(styles: dict[str, ParagraphStyle], title: str) -> list:
    return [
        Spacer(1, 4),
        Paragraph(escape(title), styles["section"]),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")),
        Spacer(1, 4),
    ]


def _contact_parts(personal: dict) -> list[str]:
    ordered = [
        ("email", personal.get("email")),
        ("phone", personal.get("phone")),
        ("linkedin", personal.get("linkedin")),
        ("github", personal.get("github")),
        ("city", personal.get("city")),
    ]
    return [_safe_str(value) for _, value in ordered if _safe_str(value)]


def _skills_lines(skills: dict, labels: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for key in ("languages", "frameworks", "tools", "cloud", "data_ai"):
        items = _safe_list((skills or {}).get(key))
        if items:
            label = labels.get(key, key.replace("_", " ").title())
            lines.append(f"{label}: {', '.join(items)}")
    return lines


def _normalize_cv_data(cv_data: dict) -> dict:
    personal = dict(cv_data.get("personal") or {})
    experience = []
    for item in cv_data.get("experience") or []:
        if not isinstance(item, dict):
            continue
        experience.append(
            {
                "company": _safe_str(item.get("company")),
                "title": _safe_str(item.get("title")),
                "start_date": _safe_str(item.get("start_date")),
                "end_date": _safe_str(item.get("end_date")),
                "location": _safe_str(item.get("location")),
                "bullets": _safe_list(item.get("bullets")),
            }
        )
    education = []
    for item in cv_data.get("education") or []:
        if not isinstance(item, dict):
            continue
        education.append(
            {
                "degree": _safe_str(item.get("degree")),
                "university": _safe_str(item.get("university")),
                "start_date": _safe_str(item.get("start_date")),
                "end_date": _safe_str(item.get("end_date")),
            }
        )
    projects = []
    for item in cv_data.get("projects") or []:
        if not isinstance(item, dict):
            continue
        projects.append(
            {
                "name": _safe_str(item.get("name")),
                "github_url": _safe_str(item.get("github_url")),
                "bullets": _safe_list(item.get("bullets")),
            }
        )
    skills_raw = cv_data.get("skills") or {}
    if isinstance(skills_raw, list):
        skills = {"tools": _safe_list(skills_raw)}
    else:
        skills = {
            key: _safe_list(skills_raw.get(key))
            for key in ("languages", "frameworks", "tools", "cloud", "data_ai")
        }
    return {
        "personal": {
            "name": _safe_str(personal.get("name")),
            "title": _safe_str(personal.get("title")),
            "email": _safe_str(personal.get("email")),
            "phone": _safe_str(personal.get("phone")),
            "linkedin": _safe_str(personal.get("linkedin")),
            "github": _safe_str(personal.get("github")),
            "city": _safe_str(personal.get("city")),
        },
        "summary": _safe_str(cv_data.get("summary")),
        "experience": experience,
        "education": education,
        "projects": projects,
        "skills": skills,
        "language": _detect_language(cv_data),
    }


def generate_cv_txt(cv_data: dict) -> str:
    """Plain-text ATS verification export."""
    data = _normalize_cv_data(cv_data)
    lang = data["language"]
    labels = SECTIONS[lang]
    lines: list[str] = []

    personal = data["personal"]
    if personal["name"]:
        lines.append(personal["name"])
    if personal["title"]:
        lines.append(personal["title"])
    contact = " | ".join(_contact_parts(personal))
    if contact:
        lines.append(contact)
    lines.append("")

    if data["summary"]:
        lines.append(labels["summary"].upper())
        lines.append(data["summary"])
        lines.append("")

    if data["experience"]:
        lines.append(labels["experience"].upper())
        for item in data["experience"]:
            header = " — ".join(
                part for part in [item["title"], item["company"]] if part
            )
            if header:
                lines.append(header)
            dates = format_date_range(item["start_date"], item["end_date"], language=lang)
            meta = " | ".join(part for part in [dates, item["location"]] if part)
            if meta:
                lines.append(meta)
            for bullet in item["bullets"]:
                lines.append(f"{BULLET} {bullet}")
            lines.append("")

    if data["projects"]:
        lines.append(labels["projects"].upper())
        for item in data["projects"]:
            project_line = item["name"]
            if item["github_url"]:
                project_line = f"{project_line} ({item['github_url']})" if project_line else item["github_url"]
            if project_line:
                lines.append(project_line)
            for bullet in item["bullets"]:
                lines.append(f"{BULLET} {bullet}")
            lines.append("")

    if data["education"]:
        lines.append(labels["education"].upper())
        for item in data["education"]:
            line = " — ".join(part for part in [item["degree"], item["university"]] if part)
            if line:
                lines.append(line)
            dates = format_date_range(item["start_date"], item["end_date"], language=lang)
            if dates:
                lines.append(dates)
            lines.append("")

    skill_lines = _skills_lines(data["skills"], labels["skill_labels"])
    if skill_lines:
        lines.append(labels["skills"].upper())
        lines.extend(skill_lines)

    return "\n".join(lines).strip() + "\n"


def generate_cv_pdf(cv_data: dict) -> bytes:
    """Generate ATS-optimized PDF bytes (single column, selectable text)."""
    data = _normalize_cv_data(cv_data)
    lang = data["language"]
    labels = SECTIONS[lang]
    years = _estimate_years_experience(data["experience"])
    compact = years < 3

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=data["personal"]["name"] or "CV",
        author=data["personal"]["name"] or "",
    )

    styles = _paragraph_styles(compact=compact)
    story: list = []

    personal = data["personal"]
    if personal["name"]:
        story.append(Paragraph(escape(personal["name"]), styles["name"]))
    if personal["title"]:
        story.append(Paragraph(escape(personal["title"]), styles["title"]))
    contact = " | ".join(_contact_parts(personal))
    if contact:
        story.append(Paragraph(escape(contact), styles["contact"]))

    if data["summary"]:
        story.extend(_section_block(styles, labels["summary"]))
        story.append(Paragraph(escape(data["summary"]), styles["body"]))

    if data["experience"]:
        story.extend(_section_block(styles, labels["experience"]))
        for item in data["experience"]:
            header = " — ".join(part for part in [item["title"], item["company"]] if part)
            if header:
                story.append(Paragraph(escape(header), styles["role"]))
            dates = format_date_range(item["start_date"], item["end_date"], language=lang)
            meta = " | ".join(part for part in [dates, item["location"]] if part)
            if meta:
                story.append(Paragraph(escape(meta), styles["meta"]))
            for bullet in item["bullets"]:
                story.append(Paragraph(escape(f"{BULLET} {bullet}"), styles["bullet"]))
            story.append(Spacer(1, 3))

    if data["projects"]:
        story.extend(_section_block(styles, labels["projects"]))
        for item in data["projects"]:
            name = item["name"]
            if item["github_url"]:
                line = f"{name} — {item['github_url']}" if name else item["github_url"]
            else:
                line = name
            if line:
                story.append(Paragraph(escape(line), styles["role"]))
            for bullet in item["bullets"]:
                story.append(Paragraph(escape(f"{BULLET} {bullet}"), styles["bullet"]))
            story.append(Spacer(1, 3))

    if data["education"]:
        story.extend(_section_block(styles, labels["education"]))
        for item in data["education"]:
            line = " — ".join(part for part in [item["degree"], item["university"]] if part)
            if line:
                story.append(Paragraph(escape(line), styles["role"]))
            dates = format_date_range(item["start_date"], item["end_date"], language=lang)
            if dates:
                story.append(Paragraph(escape(dates), styles["meta"]))
            story.append(Spacer(1, 2))

    skill_lines = _skills_lines(data["skills"], labels["skill_labels"])
    if skill_lines:
        story.extend(_section_block(styles, labels["skills"]))
        for line in skill_lines:
            story.append(Paragraph(escape(line), styles["body"]))

    if not story:
        story.append(Paragraph(escape("Curriculum Vitae"), styles["name"]))

    doc.build(story)
    return buffer.getvalue()


def cv_data_from_structured(cv: StructuredCV) -> dict:
    """Bridge StructuredCV (app pipeline) → ATS generator JSON schema."""
    lang = "es" if (cv.document_language or "").lower().startswith("es") else "en"
    github = _safe_str(getattr(cv.contact, "github", "") or "")
    if not github and _safe_str(cv.contact.website) and "github.com" in cv.contact.website.lower():
        github = _safe_str(cv.contact.website)
    if not github:
        default_user = os.getenv("DEFAULT_GITHUB_USERNAME", "").strip()
        if default_user:
            github = f"https://github.com/{default_user.lstrip('@')}"

    linkedin = _safe_str(cv.contact.linkedin)

    experience = []
    for item in cv.experience:
        period = _safe_str(item.period)
        start, end = "", ""
        if period:
            parts = re.split(r"\s*[-–—]\s*", period, maxsplit=1)
            start = parts[0] if parts else ""
            end = parts[1] if len(parts) > 1 else ""
        experience.append(
            {
                "company": _safe_str(item.company),
                "title": _safe_str(item.role),
                "start_date": start,
                "end_date": end,
                "location": _safe_str(item.location),
                "bullets": _safe_list(item.bullets),
            }
        )

    education = []
    for item in cv.education:
        period = _safe_str(item.period)
        start, end = "", ""
        if period:
            parts = re.split(r"\s*[-–—]\s*", period, maxsplit=1)
            start = parts[0] if parts else ""
            end = parts[1] if len(parts) > 1 else ""
        education.append(
            {
                "degree": _safe_str(item.degree),
                "university": _safe_str(item.school),
                "start_date": start,
                "end_date": end,
            }
        )

    projects = []

    skills_flat = _safe_list(cv.skills)
    skills = {
        "languages": [],
        "frameworks": [],
        "tools": skills_flat,
        "cloud": [],
        "data_ai": [],
    }

    return {
        "personal": {
            "name": _safe_str(cv.contact.full_name),
            "title": _safe_str(cv.contact.headline),
            "email": _safe_str(cv.contact.email),
            "phone": _safe_str(cv.contact.phone),
            "linkedin": linkedin,
            "github": github,
            "city": _safe_str(cv.contact.location),
        },
        "summary": _safe_str(cv.summary),
        "experience": experience,
        "education": education,
        "projects": projects,
        "skills": skills,
        "language": lang,
    }
