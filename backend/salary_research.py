"""Investigación de salario: empresa concreta vs mercado local."""

from __future__ import annotations

import re
from typing import TypedDict

from ai_client import call_ai_with_web_search
from cv_schema import OfferResearch, parse_json_model
from language_utils import output_language_instruction, resolve_output_language
from pydantic import BaseModel, Field

_SALARY_IN_OFFER_RE = re.compile(
    r"(?:salario|sueldo|retribuci[oó]n|salary|compensation|pay|package)"
    r"[^\n]{0,80}?(\d[\d.,\s]{2,12}(?:\s*[-–a]\s*\d[\d.,\s]{2,12})?\s*(?:€|EUR|euros?|k\b|K\b|brutos?|gross)?)",
    re.IGNORECASE,
)

_LOCATION_RE = re.compile(
    r"(?:ubicaci[oó]n|location|lugar|sede|based in|remoto en|hybrid in)\s*:\s*(.+)",
    re.IGNORECASE,
)
_COMPANY_RE = re.compile(
    r"(?:empresa|company|organizaci[oó]n|employer)\s*:\s*(.+)",
    re.IGNORECASE,
)
_ROLE_RE = re.compile(
    r"(?:puesto|rol|cargo|position|role|vacante)\s*:\s*(.+)",
    re.IGNORECASE,
)


class OfferHints(TypedDict):
    company: str
    role: str
    location: str
    salary_in_offer: str


class SalaryResearchResult(BaseModel):
    salary_company_estimate: str = ""
    salary_location_market: str = ""
    salary_comparison: str = ""
    salary_estimate: str = ""
    salary_notes: str = ""
    salary_confidence: str = "low"


SALARY_PROMPT = """You are a compensation analyst. Use web search to find REAL salary data.

SEARCH STRATEGY (run multiple searches):
1. "[company]" "[job title]" salary "[city/region]" site:glassdoor.com OR site:indeed.com OR site:linkedin.com OR site:infojobs.net OR site:levels.fyi
2. "salario" "[job title]" "[company]" "[location]"
3. "average salary" OR "salario medio" "[job title]" "[city]" "[country]" 2024 OR 2025
4. If the job posting mentions a salary range, treat it as the primary company figure.

RULES:
- salary_company_estimate: range for THIS role at THIS company (or explicit range from the job ad). Format example: "€32,000 - €38,000 brutos/año (estimado, fuente: Glassdoor)". Never use generic industry averages here.
- salary_location_market: median/average for THIS job title in THIS city/region (not the whole country unless location unknown). Example: "€30,000 - €36,000 brutos/año en Madrid para este rol (mercado local)".
- salary_comparison: 2-3 sentences: is the company above/at/below local market? Quantify % difference if both ranges exist.
- salary_estimate: one-line headline combining the company range (for backward compatibility).
- salary_notes: cite sources (Glassdoor, Indeed, etc.) and what was NOT found. Never invent numbers.
- salary_confidence: low|medium|high based on source quality.
- If nothing reliable found, use "No encontrado" for missing fields and explain in salary_notes.

Return ONLY valid JSON:
{
  "salary_company_estimate": "",
  "salary_location_market": "",
  "salary_comparison": "",
  "salary_estimate": "",
  "salary_notes": "",
  "salary_confidence": "low"
}
"""


def extract_offer_hints(job_description: str, research: OfferResearch | None = None) -> OfferHints:
    blob = job_description.strip()
    company = (research.company_name if research else "") or ""
    role = (research.job_title if research else "") or ""
    location = (research.location if research else "") or ""

    if not company:
        m = _COMPANY_RE.search(blob)
        if m:
            company = m.group(1).strip().split("\n")[0][:80]

    if not role:
        m = _ROLE_RE.search(blob)
        if m:
            role = m.group(1).strip().split("\n")[0][:80]

    if not location:
        m = _LOCATION_RE.search(blob)
        if m:
            location = m.group(1).strip().split("\n")[0][:80]
        else:
            for pattern in (
                r"(?:en|in|@)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s\-]+(?:,\s*[A-Za-z]+)?)",
                r"(Madrid|Barcelona|Valencia|Sevilla|Bilbao|Remote|Remoto|Híbrido|Hybrid)",
            ):
                m = re.search(pattern, blob, re.IGNORECASE)
                if m:
                    location = m.group(1).strip()[:60]
                    break

    salary_in_offer = ""
    m = _SALARY_IN_OFFER_RE.search(blob)
    if m:
        salary_in_offer = m.group(1).strip()

    return {
        "company": company.strip(),
        "role": role.strip(),
        "location": location.strip(),
        "salary_in_offer": salary_in_offer,
    }


def _build_salary_queries(hints: OfferHints) -> str:
    company = hints["company"] or "la empresa"
    role = hints["role"] or "el puesto"
    location = hints["location"] or "la ubicación de la oferta"
    lines = [
        f'1. "{company}" "{role}" salario {location}',
        f'2. salario medio "{role}" {location} España 2024 2025',
        f'3. "{company}" salaries glassdoor indeed linkedin',
    ]
    if hints["salary_in_offer"]:
        lines.append(f'4. La oferta menciona: {hints["salary_in_offer"]} — úsalo como dato de empresa si encaja.')
    return "\n".join(lines)


def _apply_salary_to_research(research: OfferResearch, salary: SalaryResearchResult) -> None:
    research.salary_company_estimate = salary.salary_company_estimate.strip()
    research.salary_location_market = salary.salary_location_market.strip()
    research.salary_comparison = salary.salary_comparison.strip()
    research.salary_notes = salary.salary_notes.strip()

    headline = salary.salary_estimate.strip()
    if not headline:
        headline = research.salary_company_estimate
    research.salary_estimate = headline

    if salary.salary_confidence == "high" and research.research_confidence == "low":
        research.research_confidence = "medium"
    elif salary.salary_confidence == "medium" and research.research_confidence == "low":
        research.research_confidence = "medium"


def enrich_salary_research(
    job_description: str,
    research: OfferResearch,
    *,
    output_language: str = "auto",
) -> OfferResearch:
    """Segunda pasada enfocada en salario empresa vs mercado local."""
    hints = extract_offer_hints(job_description, research)
    resolved_lang = resolve_output_language(output_language, job_description=job_description)
    lang_instruction = output_language_instruction(resolved_lang)

    user_message = (
        f"{lang_instruction}\n\n"
        f"EMPRESA: {hints['company'] or 'extraer de la oferta'}\n"
        f"PUESTO: {hints['role'] or 'extraer de la oferta'}\n"
        f"UBICACIÓN: {hints['location'] or 'extraer de la oferta'}\n"
        f"SALARIO EN LA OFERTA (si aparece): {hints['salary_in_offer'] or 'no indicado'}\n\n"
        f"BÚSQUEDAS SUGERIDAS:\n{_build_salary_queries(hints)}\n\n"
        f"TEXTO COMPLETO DE LA OFERTA:\n{job_description.strip()[:6000]}"
    )

    raw, _sources = call_ai_with_web_search(
        SALARY_PROMPT,
        user_message,
        max_output_tokens=2048,
    )

    try:
        salary = parse_json_model(raw, SalaryResearchResult)  # type: ignore[assignment]
    except ValueError:
        return research

    if isinstance(salary, SalaryResearchResult):
        _apply_salary_to_research(research, salary)

    return research
