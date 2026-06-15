import json
import re
from dataclasses import dataclass

from pdf_editor import AdaptationSections


SYSTEM_PROMPT = (
    "You are a CV optimization expert. Given a job description and CV text, adapt ONLY:\n"
    "1) The professional objective/summary\n"
    "2) The skills section\n\n"
    "Rules:\n"
    "- Match job keywords and ATS requirements.\n"
    "- Do NOT invent experience or skills the candidate does not have.\n"
    "- Keep adapted text roughly similar length to the original so it fits the same PDF layout.\n"
    "- Copy original_summary and original_skills EXACTLY as they appear in the CV text.\n"
    "- Return ONLY valid JSON, no markdown, with this exact schema:\n"
    "{\n"
    '  "original_summary": "exact current summary/objective text from the CV",\n'
    '  "adapted_summary": "optimized summary/objective",\n'
    '  "original_skills": "exact current skills text from the CV",\n'
    '  "adapted_skills": "optimized skills text"\n'
    "}"
)


@dataclass
class ParsedAdaptation:
    sections: AdaptationSections
    display_text: str


def _extract_json_object(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


def parse_adaptation_response(raw: str) -> ParsedAdaptation:
    try:
        payload = json.loads(_extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("The AI response was not valid JSON.") from exc

    required_fields = [
        "original_summary",
        "adapted_summary",
        "original_skills",
        "adapted_skills",
    ]
    missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing:
        raise ValueError(f"The AI response is missing fields: {', '.join(missing)}")

    sections = AdaptationSections(
        original_summary=str(payload["original_summary"]).strip(),
        adapted_summary=str(payload["adapted_summary"]).strip(),
        original_skills=str(payload["original_skills"]).strip(),
        adapted_skills=str(payload["adapted_skills"]).strip(),
    )
    display_text = (
        f"**Professional Summary**\n\n{sections.adapted_summary}\n\n"
        f"**Skills**\n\n{sections.adapted_skills}"
    )
    return ParsedAdaptation(sections=sections, display_text=display_text)
