from io import BytesIO

from docx import Document
from fastapi import HTTPException


def extract_text_from_docx(file_bytes: bytes) -> str:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded DOCX file is empty.")

    try:
        document = Document(BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read the DOCX file.") from exc

    parts: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    extracted = "\n".join(parts).strip()
    if not extracted:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the DOCX. Make sure it contains readable content.",
        )

    return extracted
