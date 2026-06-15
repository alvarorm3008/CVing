from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("#")
        or (stripped.startswith("**") and stripped.endswith("**"))
        or (stripped.endswith(":") and len(stripped) < 80)
    )


def _clean_heading(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("#"):
        return stripped.lstrip("# ").strip()
    if stripped.startswith("**") and stripped.endswith("**"):
        return stripped.strip("*").strip()
    return stripped.rstrip(":")


def generate_cv_pdf(content: str, title: str = "Adapted CV Sections") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PdfTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#111827"),
        spaceAfter=16,
        alignment=TA_LEFT,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#4f46e5"),
        spaceBefore=14,
        spaceAfter=8,
        alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6,
        alignment=TA_LEFT,
    )

    story = [Paragraph(escape(title), title_style), Spacer(1, 8)]

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue

        if _is_heading(line):
            story.append(Paragraph(escape(_clean_heading(line)), heading_style))
        else:
            story.append(Paragraph(escape(line), body_style))

    doc.build(story)
    return buffer.getvalue()
