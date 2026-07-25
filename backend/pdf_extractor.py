"""PDF text + hyperlink extraction via PyMuPDF, with pypdf fallback."""

from __future__ import annotations

from io import BytesIO

from fastapi import HTTPException


def _extract_with_pymupdf(file_bytes: bytes) -> str:
    import fitz

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if doc.page_count == 0:
            raise HTTPException(status_code=400, detail="The PDF file has no pages.")

        page_parts: list[str] = []
        link_uris: list[str] = []

        for page in doc:
            blocks = page.get_text("blocks") or []
            # Sort top-to-bottom, then left-to-right (helps multi-column CVs)
            blocks = sorted(blocks, key=lambda b: (round(float(b[1]), 1), round(float(b[0]), 1)))
            for block in blocks:
                if len(block) < 5:
                    continue
                text = str(block[4]).strip()
                if text:
                    page_parts.append(text)

            for link in page.get_links() or []:
                uri = (link.get("uri") or "").strip()
                if not uri:
                    continue
                if uri.lower().startswith(("http://", "https://", "mailto:", "tel:")):
                    link_uris.append(uri)

        body = "\n".join(page_parts).strip()
        # Append annotation URLs missing from body text (common in designed PDFs)
        extras: list[str] = []
        body_lower = body.lower()
        seen: set[str] = set()
        for uri in link_uris:
            key = uri.lower().rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            needle = uri
            if uri.lower().startswith("mailto:"):
                needle = uri.split(":", 1)[1]
            elif uri.lower().startswith("tel:"):
                needle = uri.split(":", 1)[1]
            if needle.lower() not in body_lower and uri.lower() not in body_lower:
                extras.append(uri)

        if extras:
            body = f"{body}\n\n" + "\n".join(extras) if body else "\n".join(extras)

        return body.strip()
    finally:
        doc.close()


def _extract_with_pypdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read the PDF file.") from exc

    if len(reader.pages) == 0:
        raise HTTPException(status_code=400, detail="The PDF file has no pages.")

    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    extracted = ""
    try:
        extracted = _extract_with_pymupdf(file_bytes)
    except HTTPException:
        raise
    except Exception:
        extracted = ""

    if not extracted:
        try:
            extracted = _extract_with_pypdf(file_bytes)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not read the PDF file.") from exc

    if not extracted:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract text from the PDF. "
                "Make sure it is a text-based PDF, not a scanned image."
            ),
        )

    return extracted
