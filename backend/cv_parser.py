from cv_schema import StructuredCV, parse_json_model
from ai_client import call_ai
from language_utils import detect_language_hint, parse_language_instruction
from link_utils import enrich_cv_links

PARSE_SYSTEM_PROMPT = """You are a CV parsing expert. Extract information from raw CV text into structured JSON.

Rules:
- Do NOT invent or infer information that is not present in the CV.
- Preserve factual content for experience, education, and contact details.
- ALWAYS preserve full URLs for LinkedIn, GitHub, portfolio and project links exactly as written.
- If you see linkedin.com/in/... anywhere in the CV text, put the full URL in contact.linkedin.
- If you see github.com/... put the full profile URL in contact.github (not a separate projects block).
- Put professional title/tagline in contact.headline (e.g. "Software Developer & Data Analyst").
- Do NOT add a separate "Projects" section — project work belongs in experience bullets if relevant.
- Group skills as "Category: skill1, skill2, skill3" (Languages, Frameworks, Cloud, etc.).
- Keep bullets concise (under 130 characters), action-led, with metrics when present.
- Use empty strings "" for missing fields, never null.

""" + parse_language_instruction() + """

Return ONLY valid JSON with this exact schema:
{
  "contact": {
    "full_name": "",
    "headline": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "website": ""
  },
  "document_language": "es",
  "summary": "",
  "skills": ["skill1", "skill2"],
  "experience": [
    {
      "role": "",
      "company": "",
      "location": "",
      "period": "",
      "bullets": ["achievement"]
    }
  ],
  "education": [
    {
      "degree": "",
      "school": "",
      "period": ""
    }
  ],
  "languages": ["English: Advanced"],
  "certifications": ["cert name"]
}
"""


def parse_cv_text(cv_text: str) -> StructuredCV:
    user_message = f"CV text to parse:\n\n{cv_text}"
    raw = call_ai(PARSE_SYSTEM_PROMPT, user_message, task="parse")

    try:
        result = parse_json_model(raw, StructuredCV)  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Failed to parse CV structure: {exc}") from exc

    if not (result.document_language or "").strip():
        result.document_language = detect_language_hint(cv_text) or "es"

    return enrich_cv_links(result, cv_text)
