from io import BytesIO
import logging
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from cv_schema import AVAILABLE_TEMPLATES, StructuredCV

logger = logging.getLogger(__name__)

MARGIN = 1.8 * cm

ATS_SECTION_TITLES = {
    "summary": "PROFESSIONAL SUMMARY",
    "skills": "SKILLS",
    "experience": "WORK EXPERIENCE",
    "education": "EDUCATION",
    "certifications": "CERTIFICATIONS",
    "languages": "LANGUAGES",
}


def _contact_line(cv: StructuredCV) -> str:
    parts = [
        cv.contact.email,
        cv.contact.phone,
        cv.contact.location,
        cv.contact.linkedin,
        cv.contact.website,
    ]
    return " | ".join(part.strip() for part in parts if part and part.strip())


def _styles(template_id: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    is_ats_max = template_id == "ats-max"
    accent = colors.HexColor("#111827")
    if template_id == "modern":
        accent = colors.HexColor("#4f46e5")

    return {
        "name": ParagraphStyle(
            "Name",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18 if is_ats_max else (22 if template_id == "modern" else 20),
            textColor=accent,
            spaceAfter=4 if is_ats_max else 6,
        ),
        "contact": ParagraphStyle(
            "Contact",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10 if is_ats_max else 9,
            textColor=colors.HexColor("#111827" if is_ats_max else "#4b5563"),
            spaceAfter=12 if is_ats_max else 14,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=accent,
            spaceBefore=8 if is_ats_max else 10,
            spaceAfter=4 if is_ats_max else 6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11 if is_ats_max else 10,
            leading=14 if is_ats_max else 14,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "role": ParagraphStyle(
            "Role",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11 if is_ats_max else 10.5,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10 if is_ats_max else 9.5,
            textColor=colors.HexColor("#374151"),
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11 if is_ats_max else 10,
            leading=14,
            leftIndent=10,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
        ),
        "skills": ParagraphStyle(
            "Skills",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11 if is_ats_max else 10,
            leading=14,
            textColor=colors.HexColor("#111827"),
            spaceAfter=6,
        ),
    }


def _section_title(styles: dict[str, ParagraphStyle], title: str, template_id: str) -> list:
    block = [
        Spacer(1, 4),
        Paragraph(escape(title), styles["section"]),
    ]
    if template_id != "ats-max":
        block.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e5e7eb")))
    block.append(Spacer(1, 6))
    return block


def _section_label(key: str, template_id: str) -> str:
    if template_id == "ats-max":
        return ATS_SECTION_TITLES[key]
    labels = {
        "summary": "Professional Summary",
        "skills": "Skills",
        "experience": "Experience",
        "education": "Education",
        "certifications": "Certifications",
        "languages": "Languages",
    }
    title = labels[key]
    return title.upper() if template_id == "ats-classic" else title


def _build_story(cv: StructuredCV, template_id: str) -> list:
    styles = _styles(template_id)
    story = []

    name = cv.contact.full_name.strip() or "Curriculum Vitae"
    story.append(Paragraph(escape(name), styles["name"]))

    contact = _contact_line(cv)
    if contact:
        story.append(Paragraph(escape(contact), styles["contact"]))

    if cv.summary.strip():
        story.extend(_section_title(styles, _section_label("summary", template_id), template_id))
        story.append(Paragraph(escape(cv.summary.strip()), styles["body"]))

    if cv.skills:
        story.extend(_section_title(styles, _section_label("skills", template_id), template_id))
        if template_id == "ats-max":
            skills_text = ", ".join(skill.strip() for skill in cv.skills if skill.strip())
        else:
            skills_text = " · ".join(skill.strip() for skill in cv.skills if skill.strip())
        story.append(Paragraph(escape(skills_text), styles["skills"]))

    if cv.experience:
        story.extend(_section_title(styles, _section_label("experience", template_id), template_id))
        for item in cv.experience:
            role_line = item.role.strip()
            if item.company.strip():
                role_line = f"{role_line}, {item.company.strip()}"
            story.append(Paragraph(escape(role_line), styles["role"]))

            meta_parts = [part for part in [item.period.strip(), item.location.strip()] if part]
            if meta_parts:
                story.append(Paragraph(escape(" | ".join(meta_parts)), styles["meta"]))

            for bullet in item.bullets:
                if bullet.strip():
                    prefix = "- " if template_id == "ats-max" else "• "
                    story.append(Paragraph(escape(f"{prefix}{bullet.strip()}"), styles["bullet"]))

            story.append(Spacer(1, 4))

    if cv.education:
        story.extend(_section_title(styles, _section_label("education", template_id), template_id))
        for item in cv.education:
            line = item.degree.strip()
            if item.school.strip():
                line = f"{line}, {item.school.strip()}"
            story.append(Paragraph(escape(line), styles["role"]))
            if item.period.strip():
                story.append(Paragraph(escape(item.period.strip()), styles["meta"]))
            story.append(Spacer(1, 2))

    if cv.certifications:
        story.extend(_section_title(styles, _section_label("certifications", template_id), template_id))
        for cert in cv.certifications:
            if cert.strip():
                prefix = "- " if template_id == "ats-max" else "• "
                story.append(Paragraph(escape(f"{prefix}{cert.strip()}"), styles["bullet"]))

    if cv.languages:
        story.extend(_section_title(styles, _section_label("languages", template_id), template_id))
        story.append(
            Paragraph(
                escape(", ".join(lang.strip() for lang in cv.languages if lang.strip())),
                styles["body"],
            )
        )

    return story


def render_cv_pdf(cv: StructuredCV, template_id: str = "modern-pro") -> bytes:
    if template_id == "ats-plain":
        from ats_cv_generator import cv_data_from_structured, generate_cv_pdf

        return generate_cv_pdf(cv_data_from_structured(cv))

    template_id = "modern-pro"

    try:
        from html_pdf_renderer import render_cv_pdf_html

        pdf_bytes, _meta = render_cv_pdf_html(cv, template_id, truncate=False)
        return pdf_bytes
    except Exception as exc:
        logger.exception("HTML PDF render failed for template %s", template_id)
        raise RuntimeError(
            f"No se pudo generar el PDF con diseño modern-pro: {exc}. "
            "Asegúrate de tener Playwright instalado (playwright install chromium)."
        ) from exc
