import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ai_client import get_provider
from ats_analyzer import build_ats_match_info
from cover_letter import assemble_cover_letter_text, generate_cover_letter
from cv_adapter import AdaptedCVSections, adapt_cv_sections, apply_adaptations, boost_ats_sections
from cv_schema import ATSMatchInfo, FullApplicationResponse, OfferResearch, StructuredCV
from offer_research import research_job_offer
from pdf_renderer import render_cv_pdf


@dataclass
class AdaptCoreResult:
    adapted_cv: StructuredCV
    original_cv: StructuredCV
    adapted_sections: AdaptedCVSections
    boosted: bool
    adaptation_mode: str


def adapt_cv_core(
    structured_cv: StructuredCV,
    job_description: str,
    adaptation_mode: str = "ats-perfect",
    *,
    skip_boost: bool = False,
    output_language: str = "auto",
    translate_content: bool = False,
) -> AdaptCoreResult:
    original_cv = structured_cv.model_copy(deep=True)
    boosted = False

    adapted_sections = adapt_cv_sections(
        structured_cv,
        job_description,
        mode=adaptation_mode,
        output_language=output_language,
        translate_content=translate_content,
    )

    if (
        not skip_boost
        and adaptation_mode == "ats-perfect"
        and adapted_sections.honest_ats_score < 80
    ):
        adapted_sections = boost_ats_sections(
            structured_cv,
            job_description,
            adapted_sections,
            output_language=output_language,
            translate_content=translate_content,
        )
        boosted = True

    adapted_cv = apply_adaptations(
        structured_cv,
        adapted_sections,
        output_language=output_language,
        job_description=job_description,
        translate_content=translate_content,
    )

    return AdaptCoreResult(
        adapted_cv=adapted_cv,
        original_cv=original_cv,
        adapted_sections=adapted_sections,
        boosted=boosted,
        adaptation_mode=adaptation_mode,
    )


def build_ats_match(adapted_sections: AdaptedCVSections, adaptation_mode: str, boosted: bool) -> ATSMatchInfo:
    mode = (
        "ats-perfect"
        if boosted and adaptation_mode == "ats-perfect"
        else adaptation_mode
    )
    payload = build_ats_match_info(adapted_sections, mode=mode)
    if boosted:
        payload["optimization_notes"] = (
            (payload.get("optimization_notes") or "")
            + " Segunda pasada ATS aplicada para subir el score."
        ).strip()
    return ATSMatchInfo(**payload)


def run_full_application_parallel(
    structured_cv: StructuredCV,
    job_description: str,
    template_id: str,
    pdf_filename: str,
    adaptation_mode: str,
    personal_interests: str = "",
    *,
    fast_mode: bool = False,
    output_language: str = "auto",
    translate_content: bool = False,
) -> FullApplicationResponse:
    skip_boost = fast_mode
    template_id = "modern-pro"

    with ThreadPoolExecutor(max_workers=2) as pool:
        adapt_future = pool.submit(
            adapt_cv_core,
            structured_cv,
            job_description,
            adaptation_mode,
            skip_boost=skip_boost,
            output_language=output_language,
            translate_content=translate_content,
        )
        research_future = pool.submit(
            research_job_offer,
            job_description,
            fast=fast_mode,
            output_language=output_language,
        )
        adapt_core = adapt_future.result()
        research = research_future.result()

    ats_match = build_ats_match(
        adapt_core.adapted_sections,
        adapt_core.adaptation_mode,
        adapt_core.boosted,
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        letter_future = pool.submit(
            generate_cover_letter,
            adapt_core.adapted_cv,
            job_description,
            research,
            personal_interests,
            ats_match=ats_match,
            fast=fast_mode,
            output_language=output_language,
            translate_content=translate_content,
        )
        pdf_future = pool.submit(
            render_cv_pdf,
            adapt_core.adapted_cv,
            template_id,
        )
        cover_letter = letter_future.result()
        if not (cover_letter.full_text or "").strip():
            cover_letter.full_text = assemble_cover_letter_text(cover_letter)
        pdf_bytes = pdf_future.result()

    return FullApplicationResponse(
        cv=adapt_core.adapted_cv,
        original_cv=adapt_core.original_cv,
        template_id=template_id,
        provider=get_provider(),
        adaptation_mode=adapt_core.adaptation_mode,
        pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
        pdf_filename=pdf_filename,
        ats_match=ats_match,
        boosted=adapt_core.boosted,
        research=research,
        cover_letter=cover_letter,
        personal_interests=personal_interests.strip(),
    )
