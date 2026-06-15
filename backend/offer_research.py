from salary_research import enrich_salary_research, extract_offer_hints

import hashlib

from ai_client import call_ai_with_web_search
from cv_schema import OfferResearch, WebSource, parse_json_model
from language_utils import output_language_instruction, resolve_output_language

RESEARCH_PROMPT = """You are a career intelligence analyst. Use web search to research a job offer.

Search for:
- Company: what they do, size, industry, HQ, culture, values, recent news
- Employee reviews: Glassdoor, Indeed, LinkedIn opinions (summarize honestly)
- Salary: dedicated pass will run after — still extract salary from job text if present into salary_estimate
- Career path: typical progression for this role at this company/industry
- Red flags or positives from reviews
- Tips for applying to this company

Rules:
- Use ONLY information found via search. If unknown, say "No encontrado" in that field.
- If the job posting states a salary, copy it exactly to salary_estimate and salary_company_estimate.
- Write user-facing text in the requested output language.
- Be honest about uncertainty. reviews_summary should mention source type (e.g. Glassdoor).
- Include 3-8 sources with real URLs from search.

Return ONLY valid JSON:
{
  "company_name": "",
  "job_title": "",
  "location": "",
  "company_description": "",
  "industry": "",
  "company_size": "",
  "headquarters": "",
  "culture_and_values": "",
  "employee_reviews_summary": "",
  "pros": ["", ""],
  "cons": ["", ""],
  "salary_estimate": "",
  "salary_company_estimate": "",
  "salary_location_market": "",
  "salary_comparison": "",
  "salary_notes": "",
  "career_path": "",
  "career_path_steps": ["", ""],
  "recent_news": "",
  "application_tips": "",
  "company_rating_summary": "",
  "research_confidence": "low|medium|high",
  "disclaimers": "",
  "sources": [{"title": "", "url": ""}]
}

Use empty strings "" and empty arrays [] instead of null.
"""

RESEARCH_PROMPT_FAST = """Career analyst. Use 2-3 quick web searches only.

Return concise JSON with essentials in the requested output language:
company_name, job_title, location, company_description (2 sentences),
salary_estimate (from job text if present), career_path (2 sentences),
employee_reviews_summary (3 sentences), pros (max 3), cons (max 3),
application_tips (1 sentence), research_confidence ("low", "medium" or "high"),
sources: [{"title": "page name", "url": "https://..."}] max 4 items. NOT a plain URL array.

A dedicated salary pass runs after — focus on company/reviews. Leave salary_location_market and salary_comparison empty.

Skip empty fields with "". Be fast and factual.

JSON schema same as full research but shorter text in each field.
"""

_research_cache: dict[str, OfferResearch] = {}
_CACHE_MAX = 24

_JSON_RETRY_PREFIX = (
    "IMPORTANTE: Tu respuesta anterior no era JSON válido. "
    "Responde ÚNICAMENTE con el objeto JSON solicitado, sin markdown, "
    "sin explicaciones y sin texto adicional antes o después.\n\n"
)


def _parse_research_response(raw: str) -> OfferResearch:
    return parse_json_model(raw, OfferResearch)  # type: ignore[return-value]


def _is_empty_research(result: OfferResearch) -> bool:
    return not any(
        [
            result.company_name.strip(),
            result.job_title.strip(),
            result.company_description.strip(),
            result.salary_estimate.strip(),
            result.employee_reviews_summary.strip(),
            result.application_tips.strip(),
        ]
    )


def _merge_grounding_sources(
    result: OfferResearch, grounding_sources: list[dict[str, str]], *, fast: bool
) -> None:
    if not grounding_sources:
        return
    existing_urls = {s.url for s in result.sources if s.url}
    limit = 4 if fast else 8
    for item in grounding_sources[:limit]:
        url = (item.get("url") or "").strip()
        if url and url not in existing_urls:
            result.sources.append(WebSource(title=item.get("title") or url, url=url))
            existing_urls.add(url)


def _cache_key(job_description: str, fast: bool) -> str:
    normalized = job_description.strip().lower()
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"{digest}:{'fast' if fast else 'full'}:salary-v2"


def research_job_offer(
    job_description: str,
    *,
    fast: bool = False,
    output_language: str = "auto",
) -> OfferResearch:
    key = _cache_key(job_description, fast)
    if key in _research_cache:
        return _research_cache[key].model_copy(deep=True)

    prompt = RESEARCH_PROMPT_FAST if fast else RESEARCH_PROMPT
    resolved_lang = resolve_output_language(output_language, job_description=job_description)
    lang_instruction = output_language_instruction(resolved_lang)
    user_prefix = (
        "Investigación rápida de esta oferta:\n\n"
        if fast
        else "Investiga esta oferta de empleo en internet. "
        "Busca empresa, salario aproximado, opiniones de empleados y ruta profesional.\n\n"
    )
    user_message = (
        f"{lang_instruction}\n\n{user_prefix}OFERTA:\n{job_description.strip()}"
    )

    max_tokens = 3072 if fast else 4096
    raw, grounding_sources = call_ai_with_web_search(
        prompt, user_message, max_output_tokens=max_tokens
    )

    try:
        result = _parse_research_response(raw)
    except ValueError:
        retry_message = f"{_JSON_RETRY_PREFIX}{user_message}"
        raw, grounding_sources = call_ai_with_web_search(
            prompt,
            retry_message,
            max_output_tokens=max_tokens,
        )
        try:
            result = _parse_research_response(raw)
        except ValueError as exc:
            raise ValueError(f"No se pudo estructurar la investigación: {exc}") from exc

    if _is_empty_research(result):
        retry_message = (
            f"{_JSON_RETRY_PREFIX}"
            "Completa TODOS los campos del JSON con información real de la oferta. "
            "No devuelvas un objeto vacío.\n\n"
            f"{user_message}"
        )
        raw, grounding_sources = call_ai_with_web_search(
            prompt,
            retry_message,
            max_output_tokens=max_tokens,
        )
        try:
            retry_result = _parse_research_response(raw)
            if not _is_empty_research(retry_result):
                result = retry_result
        except ValueError:
            pass

    if _is_empty_research(result):
        raise ValueError(
            "No se pudo estructurar la investigación: la IA no devolvió datos útiles. "
            "Inténtalo de nuevo en unos segundos."
        )

    _merge_grounding_sources(result, grounding_sources, fast=fast)

    hints = extract_offer_hints(job_description, result)
    if not result.company_name.strip() and hints["company"]:
        result.company_name = hints["company"]
    if not result.job_title.strip() and hints["role"]:
        result.job_title = hints["role"]
    if not result.location.strip() and hints["location"]:
        result.location = hints["location"]
    if hints["salary_in_offer"] and not result.salary_company_estimate.strip():
        result.salary_company_estimate = hints["salary_in_offer"]
        if not result.salary_estimate.strip():
            result.salary_estimate = hints["salary_in_offer"]

    result = enrich_salary_research(
        job_description,
        result,
        output_language=output_language,
    )

    if not result.disclaimers:
        result.disclaimers = (
            "Información orientativa obtenida de fuentes públicas en internet. "
            "Los salarios y opiniones son estimaciones — verifica antes de negociar."
        )

    if len(_research_cache) >= _CACHE_MAX:
        _research_cache.pop(next(iter(_research_cache)))
    _research_cache[key] = result.model_copy(deep=True)

    return result
