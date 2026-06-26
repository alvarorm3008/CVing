import base64
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

from ai_client import (
    AI_PROVIDER as ENV_AI_PROVIDER,
    ai_provider_scope,
    get_provider,
    get_provider_info,
    list_provider_options,
    validate_ai_provider,
)
from ats_analyzer import build_ats_match_info
from cv_adapter import AdaptedCVSections, adapt_cv_sections, apply_adaptations, boost_ats_sections, sections_from_cv
from cv_parser import parse_cv_text
from cover_letter import generate_cover_letter
from cv_schema import (
    ATSMatchInfo,
    AVAILABLE_TEMPLATES,
    ApplicationPackageResponse,
    CoverLetter,
    FullApplicationResponse,
    OfferResearch,
    StructuredCV,
    TemplateInfo,
    parse_json_model,
)
from docx_extractor import extract_text_from_docx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from application_pipeline import run_full_application_parallel
from offer_research import research_job_offer
from ats_cv_generator import generate_cv_pdf as generate_ats_cv_pdf
from ats_cv_generator import generate_cv_txt
from pdf_renderer import render_cv_pdf
from language_utils import SUPPORTED_LANGUAGES, validate_output_language
from pydantic import BaseModel, Field
from pypdf import PdfReader

load_dotenv()

_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app = FastAPI(title="CV Adapter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
DEFAULT_TEMPLATE = "modern-pro"

DOCX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


class AdaptCVResponse(BaseModel):
    cv: StructuredCV
    original_cv: StructuredCV
    template_id: str
    provider: str
    adaptation_mode: str
    pdf_base64: str
    pdf_filename: str
    ats_match: ATSMatchInfo
    boosted: bool = False


class ParseCVResponse(BaseModel):
    cv: StructuredCV
    filename: str


class RenderPDFRequest(BaseModel):
    cv: StructuredCV
    template_id: str = DEFAULT_TEMPLATE
    filename: str = "cv-adaptado.pdf"


class ATSPersonalInfo(BaseModel):
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    city: str = ""


class ATSExperienceItem(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    bullets: list[str] = Field(default_factory=list)


class ATSEducationItem(BaseModel):
    degree: str = ""
    university: str = ""
    start_date: str = ""
    end_date: str = ""


class ATSProjectItem(BaseModel):
    name: str = ""
    github_url: str = ""
    bullets: list[str] = Field(default_factory=list)


class ATSSkillsGrouped(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    data_ai: list[str] = Field(default_factory=list)


class GenerateATS_CVRequest(BaseModel):
    personal: ATSPersonalInfo = Field(default_factory=ATSPersonalInfo)
    summary: str = ""
    experience: list[ATSExperienceItem] = Field(default_factory=list)
    education: list[ATSEducationItem] = Field(default_factory=list)
    projects: list[ATSProjectItem] = Field(default_factory=list)
    skills: ATSSkillsGrouped = Field(default_factory=ATSSkillsGrouped)
    language: str = ""
    filename: str = "cv-ats.pdf"


class GenerateATS_TXTRequest(GenerateATS_CVRequest):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read the PDF file.") from exc

    if len(reader.pages) == 0:
        raise HTTPException(status_code=400, detail="The PDF file has no pages.")

    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text.strip())

    extracted = "\n\n".join(parts).strip()
    if not extracted:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract text from the PDF. "
                "Make sure it is a text-based PDF, not a scanned image."
            ),
        )

    return extracted


def _is_docx(filename: str, content_type: str | None) -> bool:
    lowered = (filename or "").lower()
    if lowered.endswith(".docx"):
        return True
    return (content_type or "") in DOCX_CONTENT_TYPES


async def read_cv_file(cv_file: UploadFile) -> str:
    filename = (cv_file.filename or "").lower()
    content_type = cv_file.content_type

    if not _is_docx(filename, content_type):
        if content_type not in ("application/pdf", "application/x-pdf") and not filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Solo se aceptan archivos PDF o DOCX para el CV.",
            )

    file_bytes = await cv_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Archivo demasiado grande. Máximo 10 MB.")

    if _is_docx(filename, content_type):
        return extract_text_from_docx(file_bytes)

    return extract_text_from_pdf(file_bytes)


def _build_pdf_filename(original_filename: Optional[str]) -> str:
    if original_filename:
        stem = original_filename.rsplit(".", 1)[0]
        return f"{stem}-adaptado.pdf"
    return "cv-adaptado.pdf"


def _validate_template(template_id: str) -> str:
    valid_ids = {template.id for template in AVAILABLE_TEMPLATES}
    if template_id not in valid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template '{template_id}'. Use one of: {', '.join(sorted(valid_ids))}.",
        )
    return template_id


def _parse_cv_json(cv_json: str) -> StructuredCV:
    try:
        return parse_json_model(cv_json, StructuredCV)  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid CV JSON payload.") from exc


def _validate_mode(mode: str) -> str:
    valid = {"honest", "ats-perfect"}
    cleaned = (mode or "honest").strip().lower()
    if cleaned not in valid:
        raise HTTPException(
            status_code=400,
            detail="adaptation_mode must be 'honest' or 'ats-perfect'.",
        )
    return cleaned


def _run_reboost(
    base_cv: StructuredCV,
    current_cv: StructuredCV,
    job_description: str,
    template_id: str,
    pdf_filename: str,
    output_language: str = "auto",
    translate_content: bool = False,
) -> AdaptCVResponse:
    original_cv = base_cv.model_copy(deep=True)

    try:
        previous = sections_from_cv(current_cv)
        adapted_sections = boost_ats_sections(
            base_cv,
            job_description,
            previous,
            output_language=output_language,
            translate_content=translate_content,
        )
        adapted_cv = apply_adaptations(
            base_cv,
            adapted_sections,
            output_language=output_language,
            job_description=job_description,
            translate_content=translate_content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ats_payload = build_ats_match_info(adapted_sections, mode="ats-perfect")
    ats_payload["optimization_notes"] = (
        (ats_payload.get("optimization_notes") or "")
        + " Segunda pasada ATS aplicada para subir el score."
    ).strip()
    ats_match = ATSMatchInfo(**ats_payload)

    pdf_bytes = render_cv_pdf(adapted_cv, template_id)

    return AdaptCVResponse(
        cv=adapted_cv,
        original_cv=original_cv,
        template_id=template_id,
        provider=get_provider(),
        adaptation_mode="ats-perfect",
        pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
        pdf_filename=pdf_filename,
        ats_match=ats_match,
        boosted=True,
    )


def _run_adaptation(
    structured_cv: StructuredCV,
    job_description: str,
    template_id: str,
    pdf_filename: str,
    adaptation_mode: str = "ats-perfect",
    output_language: str = "auto",
    translate_content: bool = False,
) -> AdaptCVResponse:
    original_cv = structured_cv.model_copy(deep=True)
    boosted = False

    try:
        adapted_sections = adapt_cv_sections(
            structured_cv,
            job_description,
            mode=adaptation_mode,
            output_language=output_language,
            translate_content=translate_content,
        )

        if (
            adaptation_mode == "ats-perfect"
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ats_payload = build_ats_match_info(
        adapted_sections,
        mode="ats-perfect" if boosted and adaptation_mode == "ats-perfect" else adaptation_mode,
    )
    if boosted:
        ats_payload["optimization_notes"] = (
            (ats_payload.get("optimization_notes") or "")
            + " Segunda pasada ATS aplicada para subir el score."
        ).strip()

    ats_match = ATSMatchInfo(**ats_payload)

    pdf_bytes = render_cv_pdf(adapted_cv, template_id)

    return AdaptCVResponse(
        cv=adapted_cv,
        original_cv=original_cv,
        template_id=template_id,
        provider=get_provider(),
        adaptation_mode=adaptation_mode,
        pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
        pdf_filename=pdf_filename,
        ats_match=ats_match,
        boosted=boosted,
    )


def _run_full_application(
    structured_cv: StructuredCV,
    job_description: str,
    template_id: str,
    pdf_filename: str,
    adaptation_mode: str,
    personal_interests: str = "",
    *,
    fast_mode: bool = True,
    output_language: str = "auto",
    translate_content: bool = False,
) -> FullApplicationResponse:
    return run_full_application_parallel(
        structured_cv,
        job_description,
        template_id,
        pdf_filename,
        adaptation_mode,
        personal_interests,
        fast_mode=fast_mode,
        output_language=output_language,
        translate_content=translate_content,
    )


@app.get("/ai-providers")
def get_ai_providers():
    return {
        "default": validate_ai_provider(ENV_AI_PROVIDER),
        "options": list_provider_options(),
    }


@app.get("/languages")
def list_languages():
    return [
        {"id": code, "name": name}
        for code, name in SUPPORTED_LANGUAGES.items()
    ]


@app.get("/health")
def health_check():
    from html_pdf_renderer import check_playwright_available

    return {
        "status": "ok",
        "provider": get_provider(),
        "ai": get_provider_info(),
        "pdf": check_playwright_available(),
    }


class PreviewHTMLRequest(BaseModel):
    cv: StructuredCV
    template_id: str = DEFAULT_TEMPLATE


@app.post("/preview-html")
def preview_html(request: PreviewHTMLRequest):
    from html_pdf_renderer import render_cv_preview_html

    template_id = _validate_template(request.template_id)
    html = render_cv_preview_html(request.cv, template_id)
    return Response(content=html, media_type="text/html; charset=utf-8")


@app.get("/templates", response_model=list[TemplateInfo])
def list_templates():
    return AVAILABLE_TEMPLATES


@app.post("/parse-cv", response_model=ParseCVResponse)
async def parse_cv(
    cv_file: UploadFile = File(...),
    ai_provider: str = Form("gemini"),
):
    cv_text = await read_cv_file(cv_file)
    provider = validate_ai_provider(ai_provider)

    try:
        with ai_provider_scope(provider):
            structured_cv = parse_cv_text(cv_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ParseCVResponse(cv=structured_cv, filename=cv_file.filename or "cv.pdf")


@app.post("/adapt-cv", response_model=AdaptCVResponse)
async def adapt_cv(
    job_description: str = Form(...),
    template_id: str = Form(DEFAULT_TEMPLATE),
    adaptation_mode: str = Form("ats-perfect"),
    output_language: str = Form("auto"),
    translate_content: bool = Form(False),
    ai_provider: str = Form("gemini"),
    reboost: bool = Form(False),
    base_cv_json: str | None = Form(None),
    cv_file: UploadFile | None = File(None),
    cv_json: str | None = Form(None),
    source_filename: str | None = Form(None),
):
    job_description = job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is required.")

    template_id = _validate_template(template_id.strip() or DEFAULT_TEMPLATE)
    adaptation_mode = _validate_mode(adaptation_mode)
    output_language = validate_output_language(output_language)
    provider = validate_ai_provider(ai_provider)

    with ai_provider_scope(provider):
        if reboost and adaptation_mode != "ats-perfect":
            raise HTTPException(
                status_code=400,
                detail="reboost solo está disponible en modo ats-perfect.",
            )

        if reboost:
            if not cv_json:
                raise HTTPException(
                    status_code=400,
                    detail="reboost requiere cv_json con el CV de la primera pasada.",
                )
            adapted_cv_current = _parse_cv_json(cv_json)
            base_cv = _parse_cv_json(base_cv_json) if base_cv_json else adapted_cv_current
            pdf_filename = _build_pdf_filename(source_filename)
            return _run_reboost(
                base_cv,
                adapted_cv_current,
                job_description,
                template_id,
                pdf_filename,
                output_language=output_language,
                translate_content=translate_content,
            )

        if cv_json:
            structured_cv = _parse_cv_json(cv_json)
            pdf_filename = _build_pdf_filename(source_filename)
        elif cv_file and cv_file.filename:
            cv_text = await read_cv_file(cv_file)
            try:
                structured_cv = parse_cv_text(cv_text)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            pdf_filename = _build_pdf_filename(cv_file.filename)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide a CV file or saved CV data (cv_json).",
            )

        return _run_adaptation(
            structured_cv,
            job_description,
            template_id,
            pdf_filename,
            adaptation_mode=adaptation_mode,
            output_language=output_language,
            translate_content=translate_content,
        )


class ResearchOfferRequest(BaseModel):
    job_description: str
    output_language: str = "auto"
    translate_content: bool = False
    ai_provider: str = "gemini"


class GenerateCoverLetterRequest(BaseModel):
    job_description: str
    cv: StructuredCV
    personal_interests: str = ""
    research: OfferResearch | None = None
    output_language: str = "auto"
    translate_content: bool = False
    ai_provider: str = "gemini"


@app.post("/research-offer", response_model=OfferResearch)
def research_offer(request: ResearchOfferRequest):
    job_description = request.job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="La descripción de la oferta es obligatoria.")

    try:
        provider = validate_ai_provider(request.ai_provider)
        with ai_provider_scope(provider):
            return research_job_offer(
                job_description,
                output_language=validate_output_language(request.output_language),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/generate-cover-letter", response_model=CoverLetter)
def create_cover_letter(request: GenerateCoverLetterRequest):
    job_description = request.job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="La descripción de la oferta es obligatoria.")

    try:
        provider = validate_ai_provider(request.ai_provider)
        with ai_provider_scope(provider):
            research = request.research
            if research is None:
                research = research_job_offer(
                    job_description,
                    output_language=validate_output_language(request.output_language),
                )

            return generate_cover_letter(
                request.cv,
                job_description,
                research,
                personal_interests=request.personal_interests,
                output_language=validate_output_language(request.output_language),
                translate_content=request.translate_content,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/application-package", response_model=ApplicationPackageResponse)
def create_application_package(request: GenerateCoverLetterRequest):
    job_description = request.job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="La descripción de la oferta es obligatoria.")

    try:
        provider = validate_ai_provider(request.ai_provider)
        with ai_provider_scope(provider):
            research = request.research or research_job_offer(
                job_description,
                output_language=validate_output_language(request.output_language),
            )
            letter = generate_cover_letter(
                request.cv,
                job_description,
                research,
                personal_interests=request.personal_interests,
                output_language=validate_output_language(request.output_language),
                translate_content=request.translate_content,
            )
            return ApplicationPackageResponse(
                research=research,
                cover_letter=letter,
                provider=get_provider(),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/full-application", response_model=FullApplicationResponse)
async def full_application(
    job_description: str = Form(...),
    template_id: str = Form(DEFAULT_TEMPLATE),
    adaptation_mode: str = Form("ats-perfect"),
    personal_interests: str = Form(""),
    output_language: str = Form("auto"),
    translate_content: bool = Form(False),
    ai_provider: str = Form("gemini"),
    fast_mode: bool = Form(True),
    cv_file: UploadFile | None = File(None),
    cv_json: str | None = Form(None),
    source_filename: str | None = Form(None),
):
    job_description = job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="La descripción de la oferta es obligatoria.")

    template_id = _validate_template(template_id.strip() or DEFAULT_TEMPLATE)
    adaptation_mode = _validate_mode(adaptation_mode)
    output_language = validate_output_language(output_language)
    provider = validate_ai_provider(ai_provider)

    if cv_json:
        structured_cv = _parse_cv_json(cv_json)
        pdf_filename = _build_pdf_filename(source_filename)
    elif cv_file and cv_file.filename:
        cv_text = await read_cv_file(cv_file)
        pdf_filename = _build_pdf_filename(cv_file.filename)
    else:
        raise HTTPException(
            status_code=400,
            detail="Sube un CV o usa un CV base guardado.",
        )

    try:
        with ai_provider_scope(provider):
            if cv_file and cv_file.filename and not cv_json:
                try:
                    structured_cv = parse_cv_text(cv_text)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc

            return _run_full_application(
                structured_cv,
                job_description,
                template_id,
                pdf_filename,
                adaptation_mode,
                personal_interests=personal_interests.strip(),
                fast_mode=fast_mode,
                output_language=output_language,
                translate_content=translate_content,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/render-txt")
def render_txt(request: RenderPDFRequest):
    """Plain-text ATS CV from StructuredCV (same input as /render-pdf)."""
    from ats_cv_generator import cv_data_from_structured

    try:
        text = generate_cv_txt(cv_data_from_structured(request.cv))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TXT generation failed: {exc}") from exc

    return Response(content=text, media_type="text/plain; charset=utf-8")


@app.post("/generate-pdf")
def generate_pdf(request: GenerateATS_CVRequest):
    """Generate ATS-optimized PDF from structured JSON (plain layout, selectable text)."""
    cv_data = request.model_dump()
    filename = request.filename if request.filename.lower().endswith(".pdf") else f"{request.filename}.pdf"
    try:
        pdf_bytes = generate_ats_cv_pdf(cv_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/generate-txt")
def generate_txt(request: GenerateATS_TXTRequest):
    """Plain-text CV for ATS parsing verification."""
    try:
        text = generate_cv_txt(request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TXT generation failed: {exc}") from exc

    return Response(content=text, media_type="text/plain; charset=utf-8")


@app.post("/render-pdf")
def render_pdf(request: RenderPDFRequest):
    template_id = _validate_template(request.template_id)
    pdf_bytes = render_cv_pdf(request.cv, template_id)
    filename = (
        request.filename
        if request.filename.lower().endswith(".pdf")
        else f"{request.filename}.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _mount_frontend() -> None:
    if os.getenv("SERVE_FRONTEND", "").lower() not in ("1", "true", "yes"):
        return

    static_dir = Path(__file__).parent / "static" / "app"
    if not static_dir.is_dir():
        return

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path:
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(file_path)
        index = static_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Frontend not found")


_mount_frontend()
