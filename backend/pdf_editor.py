import re
from dataclasses import dataclass
from io import BytesIO

import fitz


@dataclass
class AdaptationSections:
    original_summary: str
    adapted_summary: str
    original_skills: str
    adapted_skills: str


SUMMARY_HEADERS = [
    "professional summary",
    "summary",
    "executive summary",
    "profile",
    "professional profile",
    "about me",
    "about",
    "resumen profesional",
    "resumen",
    "perfil profesional",
    "perfil",
    "sobre mi",
    "sobre mí",
    "objetivo profesional",
    "objetivo",
]

SKILLS_HEADERS = [
    "skills",
    "technical skills",
    "core competencies",
    "competencies",
    "key skills",
    "habilidades",
    "habilidades tecnicas",
    "habilidades técnicas",
    "competencias",
    "conocimientos",
    "stack",
    "technologies",
    "tecnologias",
    "tecnologías",
]

NEXT_SECTION_HEADERS = SUMMARY_HEADERS + SKILLS_HEADERS + [
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "work history",
    "experiencia",
    "experiencia profesional",
    "experiencia laboral",
    "historial laboral",
    "empleo",
    "education",
    "academic background",
    "educación",
    "educacion",
    "formación",
    "formacion",
    "formation",
    "projects",
    "proyectos",
    "certifications",
    "certificaciones",
    "languages",
    "idiomas",
    "references",
    "referencias",
    "contact",
    "contacto",
    "awards",
    "premios",
]


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    return re.sub(r"\s+", " ", lowered)


def _is_header(text: str, keywords: list[str]) -> bool:
    normalized = _normalize(text)
    if len(normalized) > 80:
        return False
    return any(keyword in normalized for keyword in keywords)


def _is_next_section_header(text: str) -> bool:
    return _is_header(text, NEXT_SECTION_HEADERS)


@dataclass
class TextLine:
    text: str
    bbox: fitz.Rect
    size: float


def _collect_lines(page: fitz.Page) -> list[TextLine]:
    lines: list[TextLine] = []
    page_dict = page.get_text("dict")

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(span.get("text", "") for span in spans).strip()
            if not text:
                continue
            sizes = [span.get("size", 11) for span in spans]
            lines.append(
                TextLine(
                    text=text,
                    bbox=fitz.Rect(line["bbox"]),
                    size=sum(sizes) / len(sizes),
                )
            )

    lines.sort(key=lambda item: (round(item.bbox.y0, 1), item.bbox.x0))
    return lines


def _find_section_region(
    lines: list[TextLine],
    header_keywords: list[str],
    page_rect: fitz.Rect,
) -> tuple[fitz.Rect, float] | None:
    header_index = None
    for index, line in enumerate(lines):
        if _is_header(line.text, header_keywords):
            header_index = index
            break

    if header_index is None:
        return None

    header_line = lines[header_index]
    start_y = header_line.bbox.y1 + 2
    end_y = page_rect.y1 - 20

    for line in lines[header_index + 1 :]:
        if line.bbox.y0 >= start_y and _is_next_section_header(line.text):
            if not _is_header(line.text, header_keywords):
                end_y = line.bbox.y0 - 2
                break

    content_lines = [
        line
        for line in lines[header_index + 1 :]
        if line.bbox.y0 >= start_y and line.bbox.y1 <= end_y + 1
    ]

    if content_lines:
        x0 = min(line.bbox.x0 for line in content_lines)
        x1 = max(line.bbox.x1 for line in content_lines)
        y0 = start_y
        y1 = max(line.bbox.y1 for line in content_lines) + 4
        font_size = sum(line.size for line in content_lines) / len(content_lines)
    else:
        x0 = header_line.bbox.x0
        x1 = page_rect.x1 - 40
        y0 = start_y
        y1 = min(start_y + 110, end_y)
        font_size = header_line.size

    return fitz.Rect(x0, y0, x1, y1), font_size


def _replace_region(page: fitz.Page, rect: fitz.Rect, new_text: str, font_size: float) -> bool:
    if rect.is_empty or not new_text.strip():
        return False

    padded = fitz.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 2)
    page.add_redact_annot(padded, fill=(1, 1, 1))
    page.apply_redactions()

    for size in [font_size, font_size - 0.5, font_size - 1, 9.5, 9, 8.5, 8, 7.5, 7]:
        if size < 7:
            break
        remaining = page.insert_textbox(
            padded,
            new_text.strip(),
            fontsize=size,
            fontname="helv",
            color=(0, 0, 0),
            align=fitz.TEXT_ALIGN_LEFT,
        )
        if remaining >= 0:
            return True

    page.insert_textbox(
        padded,
        new_text.strip(),
        fontsize=7,
        fontname="helv",
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_LEFT,
    )
    return True


def _search_queries(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []

    queries = [cleaned]
    if len(cleaned) > 160:
        queries.append(cleaned[:160])
    if len(cleaned) > 100:
        queries.append(cleaned[:100])
    if len(cleaned) > 60:
        queries.append(cleaned[:60])

    unique: list[str] = []
    for query in queries:
        if query not in unique:
            unique.append(query)
    return unique


def _replace_by_search(
    doc: fitz.Document,
    original_text: str,
    adapted_text: str,
) -> bool:
    for query in _search_queries(original_text):
        for page in doc:
            rects = page.search_for(query)
            if not rects:
                continue

            rect = rects[0]
            for extra in rects[1:]:
                rect |= extra

            font_size = max(8.0, min(11.0, rect.height / max(1, query.count(" ") + 1)))
            if _replace_region(page, rect, adapted_text, font_size):
                return True

    return False


def _replace_by_headers(
    doc: fitz.Document,
    header_keywords: list[str],
    adapted_text: str,
) -> bool:
    for page in doc:
        lines = _collect_lines(page)
        region = _find_section_region(lines, header_keywords, page.rect)
        if region is None:
            continue

        rect, font_size = region
        if _replace_region(page, rect, adapted_text, font_size):
            return True

    return False


def apply_adaptations_to_pdf(pdf_bytes: bytes, sections: AdaptationSections) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    replaced_summary = False
    replaced_skills = False

    if sections.adapted_summary.strip():
        replaced_summary = _replace_by_headers(doc, SUMMARY_HEADERS, sections.adapted_summary)
        if not replaced_summary:
            replaced_summary = _replace_by_search(
                doc,
                sections.original_summary,
                sections.adapted_summary,
            )

    if sections.adapted_skills.strip():
        replaced_skills = _replace_by_headers(doc, SKILLS_HEADERS, sections.adapted_skills)
        if not replaced_skills:
            replaced_skills = _replace_by_search(
                doc,
                sections.original_skills,
                sections.adapted_skills,
            )

    if not replaced_summary and not replaced_skills:
        doc.close()
        raise ValueError(
            "Could not locate the summary or skills sections in the PDF layout. "
            "Make sure your CV has clearly labeled sections."
        )

    output = doc.tobytes()
    doc.close()
    return output
