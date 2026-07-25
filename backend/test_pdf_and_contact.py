"""Tests for PDF extraction and deterministic contact fill."""

from io import BytesIO

from contact_fill import (
    extract_email,
    extract_github,
    extract_linkedin,
    extract_phone,
    extract_website,
    fill_missing_contact,
)
from cv_schema import ContactInfo, StructuredCV
from pdf_extractor import extract_text_from_pdf


def _make_pdf_with_link() -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Alvaro Rodriguez\nSoftware Developer\nMadrid")
    # Visible text without full URL + clickable link (common CV pattern)
    page.insert_text((72, 120), "LinkedIn  GitHub")
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(72, 110, 140, 130),
            "uri": "https://linkedin.com/in/alvaro-test",
        }
    )
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(150, 110, 220, 130),
            "uri": "https://github.com/alvaro-test",
        }
    )
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(72, 140, 220, 160),
            "uri": "mailto:alvaro@example.com",
        }
    )
    buf = BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_extract_email_phone_links():
    text = (
        "Alvaro Rodriguez\n"
        "alvaro@example.com | +34 612 345 678\n"
        "https://linkedin.com/in/alvaro-test\n"
        "https://github.com/alvaro-test\n"
        "https://alvaro.dev\n"
    )
    assert extract_email(text) == "alvaro@example.com"
    assert "612" in extract_phone(text)
    assert "linkedin.com/in/alvaro-test" in extract_linkedin(text)
    assert "github.com/alvaro-test" in extract_github(text)
    assert "alvaro.dev" in extract_website(text)


def test_fill_missing_contact_only_empty_fields():
    cv = StructuredCV(
        contact=ContactInfo(
            full_name="Alvaro",
            email="",
            phone="",
            linkedin="",
            github="",
            website="",
        )
    )
    text = "alvaro@example.com +34 600111222 https://linkedin.com/in/foo https://github.com/foo"
    filled = fill_missing_contact(cv, text)
    assert filled.contact.email == "alvaro@example.com"
    assert "600" in filled.contact.phone
    assert "linkedin.com/in/foo" in filled.contact.linkedin
    assert "github.com/foo" in filled.contact.github

    # Does not overwrite existing
    cv2 = StructuredCV(contact=ContactInfo(email="keep@me.com", phone="111"))
    filled2 = fill_missing_contact(cv2, "other@x.com +34 999888777")
    assert filled2.contact.email == "keep@me.com"
    assert filled2.contact.phone == "111"


def test_pymupdf_extracts_annotation_links():
    pdf_bytes = _make_pdf_with_link()
    text = extract_text_from_pdf(pdf_bytes)
    assert "Alvaro Rodriguez" in text
    assert "linkedin.com/in/alvaro-test" in text.lower()
    assert "github.com/alvaro-test" in text.lower()
    assert "alvaro@example.com" in text.lower() or "mailto:alvaro@example.com" in text.lower()
