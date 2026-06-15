from pydantic import BaseModel, Field

from ai_client import call_ai
from cv_schema import ExperienceItem, StructuredCV, parse_json_model
from link_utils import enrich_cv_links
from cv_pdf_prep import (
    PDF_CV_RULES,
    merge_experience,
    prepare_cv_for_pdf,
    preserve_contact,
    sync_headline,
)
from language_utils import (
    output_language_instruction,
    resolve_output_language,
    translation_instruction,
)

HONEST_PROMPT = """You are an honest career coach. Help the candidate decide IF they should apply to this job and WHAT to learn first.

The CV is the ONLY source of truth. Never invent experience.

STEP 1 — Inventory all evidence in the CV.
STEP 2 — Extract must-have and nice-to-have from the job.
STEP 3 — Map each requirement: COVERED | PARTIAL | MISSING.
STEP 4 — Adapt summary, skills, bullets using ONLY COVERED and PARTIAL (honest CV, not optimized to fool ATS).

PRESERVE all contact fields (linkedin, github, website, headline, email, phone) and URLs in bullets exactly — never remove GitHub/LinkedIn links.
""" + PDF_CV_RULES + """
APPLY RECOMMENDATION (critical):
- apply_now: ≥70% must-haves COVERED, no critical MISSING blockers
- apply_after_learning: 50-69% or fixable gaps — candidate should learn skills_to_learn FIRST, then apply
- not_recommended: <50% or multiple critical must-haves MISSING with no evidence

skills_to_learn: detailed learning plan for every important MISSING requirement.

Return ONLY valid JSON:
{
  "target_role": "",
  "summary": "",
  "skills": ["only evidenced skills, job-relevant order"],
  "experience": [{"role": "", "company": "", "location": "", "period": "", "bullets": []}],
  "honest_ats_score": 65,
  "potential_ats_score": 88,
  "apply_recommendation": "apply_now|apply_after_learning|not_recommended",
  "apply_recommendation_reason": "2-3 sentences: should they apply now or learn first?",
  "skills_you_have": [{"requirement": "", "evidence": "", "match_level": "covered|partial"}],
  "skills_to_learn": [{"skill": "", "priority": "high|medium|low", "why_needed": "", "how_to_learn": ""}],
  "must_have_matched": [],
  "must_have_missing": [],
  "optimization_notes": ""
}

Use empty strings "" not null. Write apply_recommendation_reason in the output language.
"""

ATS_PERFECT_PROMPT = """You are an ATS optimization specialist. The candidate already decided to APPLY — your job is the CV to SEND.

GOAL: CV that passes ATS filters (85-95% keyword match) so a human recruiter sees it.

Factual base = structured CV. Do NOT invent companies, dates, degrees, or roles.

PRESERVE all URLs in experience bullets (GitHub, LinkedIn, portfolio). Never strip links from contact.linkedin, contact.github or contact.website.
""" + PDF_CV_RULES + """

Maximize ATS aggressively:
- Mirror exact job title in summary
- Pack skills with job keywords first (defensible links only)
- Rewrite bullets with maximum job keywords
- Target honest_ats_score 85-95

ALWAYS fill must_have_missing with job requirements still not evidenced in the CV.
ALWAYS fill cv_improvements with 3-6 actionable edits the candidate can still make (e.g. "Add keyword X to skills", "Rephrase bullet at Company Y with metric Z").
optimization_notes: 1-2 sentence summary of CV readiness after your edits.

Return skills_to_learn as empty array [].
apply_recommendation: always "send_cv".

Return ONLY valid JSON:
{
  "target_role": "",
  "summary": "",
  "skills": ["job keywords first, 18-30 items"],
  "experience": [{"role": "", "company": "", "location": "", "period": "", "bullets": []}],
  "honest_ats_score": 88,
  "potential_ats_score": 92,
  "apply_recommendation": "send_cv",
  "apply_recommendation_reason": "",
  "skills_you_have": [{"requirement": "", "evidence": "", "match_level": "covered|partial"}],
  "skills_to_learn": [],
  "must_have_matched": [],
  "must_have_missing": [],
  "cv_improvements": ["actionable improvement 1", "actionable improvement 2"],
  "optimization_notes": "Short status summary."
}

Use empty strings "" not null.
"""

ATS_BOOST_PROMPT = """You are an ATS re-optimization specialist. The first pass scored below target.

The candidate already decided to APPLY. Run a SECOND PASS to push honest_ats_score to 88-95.

Rules:
- Structured CV + first-pass result are the ONLY truth. Never invent employers, dates, or degrees.
- Add every missing must-have keyword that can be honestly linked to existing experience.
- Expand skills list (22-35 items) with exact job terminology.
- Rewrite every bullet with stronger keyword density.
- Return skills_to_learn as [].
""" + PDF_CV_RULES + """

Return ONLY valid JSON (same schema as ATS perfect mode):
{
  "target_role": "",
  "summary": "",
  "skills": [],
  "experience": [{"role": "", "company": "", "location": "", "period": "", "bullets": []}],
  "honest_ats_score": 90,
  "potential_ats_score": 93,
  "apply_recommendation": "send_cv",
  "apply_recommendation_reason": "",
  "skills_you_have": [{"requirement": "", "evidence": "", "match_level": "covered|partial"}],
  "skills_to_learn": [],
  "must_have_matched": [],
  "must_have_missing": [],
  "cv_improvements": [],
  "optimization_notes": "Second ATS pass completed."
}

Use empty strings "" not null.
"""

PROMPTS = {
    "honest": HONEST_PROMPT,
    "ats-perfect": ATS_PERFECT_PROMPT,
    "ats-boost": ATS_BOOST_PROMPT,
}

VALID_MODES = frozenset(PROMPTS.keys())


class SkillMatch(BaseModel):
    requirement: str
    evidence: str = ""
    match_level: str = "covered"


class LearningRecommendation(BaseModel):
    skill: str
    priority: str = "medium"
    why_needed: str = ""
    how_to_learn: str = ""


class AdaptedCVSections(BaseModel):
    target_role: str = ""
    summary: str
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    honest_ats_score: int = 0
    potential_ats_score: int = 0
    apply_recommendation: str = ""
    apply_recommendation_reason: str = ""
    skills_you_have: list[SkillMatch] = Field(default_factory=list)
    skills_to_learn: list[LearningRecommendation] = Field(default_factory=list)
    must_have_matched: list[str] = Field(default_factory=list)
    must_have_missing: list[str] = Field(default_factory=list)
    cv_improvements: list[str] = Field(default_factory=list)
    optimization_notes: str = ""


def adapt_cv_sections(
    cv: StructuredCV,
    job_description: str,
    mode: str = "ats-perfect",
    *,
    previous_adaptation: AdaptedCVSections | None = None,
    output_language: str = "auto",
    translate_content: bool = False,
) -> AdaptedCVSections:
    if mode not in VALID_MODES:
        mode = "honest"

    resolved_lang = resolve_output_language(
        output_language,
        cv=cv,
        job_description=job_description,
        translate_content=translate_content,
    )
    lang_instruction = output_language_instruction(resolved_lang, translate_content=translate_content)
    translate_block = translation_instruction(translate_content, resolved_lang)

    user_message = (
        f"{lang_instruction}\n{translate_block}\n\n"
        f"Adaptation mode: {mode}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Structured CV JSON (source of truth):\n{cv.model_dump_json()}"
    )
    if previous_adaptation is not None:
        user_message += (
            f"\n\nFirst-pass adaptation (improve this):\n"
            f"{previous_adaptation.model_dump_json()}"
        )

    raw = call_ai(PROMPTS[mode], user_message, max_output_tokens=8192, json_mode=True, task="adapt")

    try:
        result = parse_json_model(raw, AdaptedCVSections)  # type: ignore[assignment]
    except ValueError:
        # Reintento: refuerza la instrucción JSON en caso de respuesta malformada
        retry_message = (
            "IMPORTANT: Your previous response was not valid JSON. "
            "Respond with ONLY the JSON object, no markdown, no explanation, no extra text.\n\n"
            + user_message
        )
        raw2 = call_ai(PROMPTS[mode], retry_message, max_output_tokens=8192, json_mode=True, task="adapt")
        try:
            result = parse_json_model(raw2, AdaptedCVSections)  # type: ignore[assignment]
        except ValueError as exc2:
            raise ValueError(f"Failed to adapt CV for ATS: {exc2}") from exc2

    result.honest_ats_score = max(0, min(100, result.honest_ats_score))
    result.potential_ats_score = max(
        result.honest_ats_score, min(100, result.potential_ats_score)
    )

    if mode == "ats-perfect":
        result.skills_to_learn = []
        if result.honest_ats_score < 80:
            result.potential_ats_score = max(result.potential_ats_score, 88)

    return result


def sections_from_cv(cv: StructuredCV) -> AdaptedCVSections:
    return AdaptedCVSections(
        summary=cv.summary,
        skills=cv.skills,
        experience=cv.experience,
    )


def boost_ats_sections(
    cv: StructuredCV,
    job_description: str,
    previous: AdaptedCVSections,
    *,
    output_language: str = "auto",
    translate_content: bool = False,
) -> AdaptedCVSections:
    return adapt_cv_sections(
        cv,
        job_description,
        mode="ats-boost",
        previous_adaptation=previous,
        output_language=output_language,
        translate_content=translate_content,
    )


def apply_adaptations(
    cv: StructuredCV,
    adapted: AdaptedCVSections,
    *,
    output_language: str = "auto",
    job_description: str = "",
    translate_content: bool = False,
) -> StructuredCV:
    updated = cv.model_copy(deep=True)
    preserve_contact(cv.contact, updated.contact)
    updated.summary = adapted.summary.strip()
    updated.skills = [skill.strip() for skill in adapted.skills if skill.strip()]

    if adapted.target_role.strip():
        updated.contact.headline = adapted.target_role.strip()
    else:
        sync_headline(updated, adapted.target_role)

    if adapted.experience:
        updated.experience = merge_experience(
            cv.experience,
            adapted.experience,
            translated=translate_content,
        )
    else:
        updated.experience = list(cv.experience)

    updated.document_language = resolve_output_language(
        output_language,
        cv=cv,
        job_description=job_description,
        translate_content=translate_content,
    )

    enrich_cv_links(updated)
    return prepare_cv_for_pdf(updated, target_role=adapted.target_role, truncate=True)
