from ai_client import call_ai
from cv_schema import ATSMatchInfo, CoverLetter, OfferResearch, StructuredCV, parse_json_model
from language_utils import output_language_instruction, resolve_adaptation_settings, translation_instruction

COVER_LETTER_PROMPT = """You write compelling, honest cover letters for job applications.

Inputs: adapted candidate CV (truth), ATS keyword alignment, company research, job offer.

Rules:
- NEVER invent experience, degrees, or achievements not in the CV.
- Use hard skills from the adapted CV skills section and soft skills evidenced in summary/experience bullets.
- Reference specific company facts from research (culture, news, values, mission, recent_news).
- Connect candidate's real experience to matched job requirements from ATS analysis.
- MOTIVATION (critical): Do NOT ask the candidate anything. Infer why this company and role fit them by crossing CV evidence with company research (mission, culture, products, news). Write authentic motivation grounded in facts from both sources — never generic filler.
- Professional but warm tone — not generic template spam.
- 3-4 paragraphs, ~250-380 words total.
- Address hiring manager generically if name unknown.

Return ONLY valid JSON:
{
  "subject_line": "",
  "greeting": "",
  "paragraphs": ["paragraph 1", "paragraph 2", "paragraph 3"],
  "closing": "",
  "full_text": "",
  "tone": "professional|warm|technical",
  "personalization_hooks": ["hook 1", "hook 2", "hook 3"],
  "language": "es"
}

Use empty strings "" not null. Leave full_text as "" — the server assembles the final letter from greeting, paragraphs and closing.
Set language to the ISO 639-1 code used. paragraphs must be a JSON array of strings, each one full paragraph.
"""

COVER_LETTER_PROMPT_FAST = """Write a concise cover letter JSON. 2-3 short paragraphs, ~180 words max.
Use adapted CV skills, soft skills from bullets, company research facts, and ATS matched keywords.
Infer motivation (why this company/role) from CV + company research — do not use generic phrases.
Same honesty rules: only CV facts. Return same JSON schema. Leave full_text as "".
paragraphs must be a JSON array. Be direct and fast.
"""

_JSON_RETRY_PREFIX = (
    "IMPORTANTE: Tu respuesta anterior no era JSON válido. "
    "Responde ÚNICAMENTE con el objeto JSON solicitado, sin markdown, "
    "sin explicaciones y sin texto adicional. full_text debe ser \"\".\n\n"
)


def _compact_research_summary(research: OfferResearch) -> str:
    lines = [
        f"Empresa: {research.company_name or '—'}",
        f"Puesto: {research.job_title or '—'}",
        f"Ubicación: {research.location or '—'}",
    ]
    for label, value in (
        ("Descripción", research.company_description),
        ("Cultura", research.culture_and_values),
        ("Noticias", research.recent_news),
        ("Consejo aplicar", research.application_tips),
        ("Salario empresa", research.salary_company_estimate or research.salary_estimate),
        ("Mercado local", research.salary_location_market),
    ):
        text = (value or "").strip()
        if text:
            lines.append(f"{label}: {text[:400]}")
    if research.pros:
        lines.append(f"Pros: {'; '.join(research.pros[:4])}")
    if research.cons:
        lines.append(f"Contras: {'; '.join(research.cons[:3])}")
    return "\n".join(lines)


def _compact_cv_summary(cv: StructuredCV) -> str:
    lines = [
        f"Nombre: {cv.contact.full_name}",
        f"Headline: {cv.contact.headline}",
        f"Resumen: {(cv.summary or '')[:700]}",
        f"Skills: {', '.join((cv.skills or [])[:28])}",
    ]
    for exp in (cv.experience or [])[:5]:
        bullets = " | ".join((exp.bullets or [])[:4])
        lines.append(f"• {exp.role} @ {exp.company} ({exp.period}): {bullets[:280]}")
    for edu in (cv.education or [])[:2]:
        lines.append(f"• Formación: {edu.degree} — {edu.school}")
    return "\n".join(lines)


def _parse_cover_letter_response(raw: str) -> CoverLetter:
    return parse_json_model(raw, CoverLetter)  # type: ignore[return-value]


def _ats_context_block(ats_match: ATSMatchInfo | None) -> str:
    if not ats_match:
        return "ATS alignment: not provided — infer from job offer and CV only."
    lines = [
        f"Target role: {ats_match.target_role}",
        f"ATS score: {ats_match.honest_score or ats_match.score}%",
        f"Matched keywords: {', '.join(ats_match.matched_keywords[:20])}",
    ]
    if ats_match.missing_keywords:
        lines.append(f"Gaps (do not invent to fill): {', '.join(ats_match.missing_keywords[:12])}")
    if ats_match.skills_you_have:
        evidenced = []
        for s in ats_match.skills_you_have[:12]:
            if isinstance(s, dict):
                evidenced.append(f"{s.get('requirement', '')} ({s.get('match_level', '')})")
            else:
                evidenced.append(f"{s.requirement} ({s.match_level})")
        if evidenced:
            lines.append(f"Skills evidenced: {', '.join(evidenced)}")
    return "ATS alignment:\n" + "\n".join(lines)


def assemble_cover_letter_text(letter: CoverLetter) -> str:
    if (letter.full_text or "").strip():
        return letter.full_text.strip()
    parts: list[str] = []
    if letter.greeting.strip():
        parts.append(letter.greeting.strip())
    parts.extend(p.strip() for p in letter.paragraphs if p and p.strip())
    if letter.closing.strip():
        parts.append(letter.closing.strip())
    return "\n\n".join(parts)


def generate_cover_letter(
    cv: StructuredCV,
    job_description: str,
    research: OfferResearch,
    personal_interests: str = "",
    *,
    ats_match: ATSMatchInfo | None = None,
    fast: bool = False,
    output_language: str = "auto",
    translate_content: bool = False,
) -> CoverLetter:
    resolved_lang, translate_content = resolve_adaptation_settings(
        output_language,
        cv=cv,
        job_description=job_description,
    )
    lang_instruction = output_language_instruction(resolved_lang, translate_content=True)
    translate_block = translation_instruction(True, resolved_lang)

    user_message = (
        f"{lang_instruction}\n{translate_block}\n\n"
        f"Job offer:\n{job_description.strip()[:4000]}\n\n"
        f"{_ats_context_block(ats_match)}\n\n"
        f"Company research:\n{_compact_research_summary(research)}\n\n"
        f"Adapted candidate CV (source of truth):\n{_compact_cv_summary(cv)}\n\n"
        "Task: Infer why this candidate fits THIS company and role by combining CV evidence "
        "with company research. Do not rely on user-provided motivation text."
    )

    prompt = COVER_LETTER_PROMPT_FAST if fast else COVER_LETTER_PROMPT
    max_tokens = 3072 if fast else 4096

    raw = call_ai(prompt, user_message, max_output_tokens=max_tokens, task="cover_letter")

    try:
        result = _parse_cover_letter_response(raw)
    except ValueError:
        retry_message = f"{_JSON_RETRY_PREFIX}{user_message}"
        raw = call_ai(
            prompt,
            retry_message,
            max_output_tokens=max_tokens,
            task="cover_letter",
        )
        try:
            result = _parse_cover_letter_response(raw)
        except ValueError as exc:
            raise ValueError(f"No se pudo generar la carta: {exc}") from exc

    if not result.full_text.strip():
        result.full_text = assemble_cover_letter_text(result)

    if not result.paragraphs and result.full_text.strip():
        result.paragraphs = [
            p.strip() for p in result.full_text.split("\n\n") if p.strip()
        ]

    if not result.full_text.strip():
        raise ValueError("La carta generada está vacía. Inténtalo de nuevo.")

    if not (result.language or "").strip():
        result.language = resolved_lang

    return result
