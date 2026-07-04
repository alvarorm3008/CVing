from pathlib import Path
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cv_pdf_prep import prepare_cv_for_pdf
from cv_schema import StructuredCV
from link_utils import (
    build_contact_links,
    enrich_cv_links,
    linkify_text,
    parse_skill_groups,
)
from language_utils import get_section_labels, resolve_output_language
from pdf_layout_engine import LayoutResult, fit_cv_layout

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
HTML_TEMPLATE_IDS = frozenset({"modern-pro"})
DEFAULT_TEMPLATE = "modern-pro"
_playwright_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright-pdf")

_browser_lock = threading.Lock()
_playwright = None
_browser = None

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)
_env.filters["linkify"] = lambda text: linkify_text(text)


def check_playwright_available() -> dict:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return {"available": True, "message": "Chromium listo"}
    except Exception as exc:
        return {
            "available": False,
            "message": f"Playwright/Chromium no disponible: {exc}. Ejecuta: playwright install chromium",
        }


def check_playwright_installed() -> dict:
    """Lightweight probe for /health — does not launch Chromium (Render pings this often)."""
    try:
        import playwright  # noqa: F401

        return {"available": True, "message": "Playwright instalado"}
    except ImportError:
        return {"available": False, "message": "Playwright no instalado"}


def _split_experience(cv: StructuredCV) -> list[dict]:
    jobs: list[dict] = []

    for item in cv.experience:
        jobs.append(
            {
                "role": item.role.strip(),
                "company": item.company.strip(),
                "location": item.location.strip(),
                "dates": item.period.strip(),
                "bullets": [linkify_text(b.strip()) for b in item.bullets if b.strip()],
            }
        )

    return jobs


def _cv_context(cv: StructuredCV, *, compact: bool = False) -> dict:
    contact = cv.contact
    skill_groups, flat_skills = parse_skill_groups(cv.skills)
    jobs = _split_experience(cv)

    education = [
        {
            "degree": item.degree.strip(),
            "institution": item.school.strip(),
            "dates": item.period.strip(),
        }
        for item in cv.education
    ]

    headline = (contact.headline or "").strip()
    if not headline and cv.summary:
        first_line = cv.summary.strip().split("\n")[0]
        if len(first_line) < 80:
            headline = first_line

    fonts_base = (STATIC_DIR / "fonts").as_uri() if (STATIC_DIR / "fonts").exists() else ""

    return {
        "contact": {
            "name": contact.full_name.strip() or "Curriculum Vitae",
            "headline": headline,
            "location": contact.location.strip(),
        },
        "contact_links": build_contact_links(contact),
        "summary": cv.summary.strip(),
        "skill_groups": skill_groups,
        "flat_skills": flat_skills,
        "jobs": jobs,
        "education": education,
        "languages": [lang.strip() for lang in cv.languages if lang.strip()],
        "certifications": [linkify_text(c.strip()) for c in cv.certifications if c.strip()],
        "section_labels": get_section_labels(
            resolve_output_language(cv.document_language or "auto", cv=cv)
        ),
        "document_lang": resolve_output_language(cv.document_language or "auto", cv=cv),
        "compact": compact,
        "fonts_base": fonts_base,
    }


def render_html_cv(cv: StructuredCV, template_id: str = DEFAULT_TEMPLATE, *, compact: bool = False) -> str:
    template_name = "cv_modern_pro.html"
    template = _env.get_template(template_name)
    return template.render(**_cv_context(cv, compact=compact))


def _get_browser(playwright):
    global _browser
    with _browser_lock:
        if _browser is not None:
            return _browser
        for launch_kwargs in (
            {"headless": True, "args": ["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]},
            {"headless": True, "channel": "chrome", "args": ["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]},
            {"headless": True, "channel": "msedge", "args": ["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"]},
        ):
            try:
                _browser = playwright.chromium.launch(**launch_kwargs)
                return _browser
            except Exception:
                continue
        raise RuntimeError(
            "No se pudo iniciar Chromium. Ejecuta: playwright install chromium"
        )


def _ensure_playwright():
    global _playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright no está instalado. Ejecuta: pip install playwright && playwright install chromium"
        ) from exc
    if _playwright is None:
        _playwright = sync_playwright().start()
    return _playwright


def _render_html_to_pdf_sync(html: str) -> bytes:
    playwright = _ensure_playwright()
    browser = _get_browser(playwright)
    page = browser.new_page()
    try:
        page.emulate_media(media="print")
        page.set_content(html, wait_until="load")
        page.wait_for_timeout(200)
        return page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
    finally:
        page.close()


def _render_cv_with_layout_sync(cv: StructuredCV, template_id: str) -> tuple[bytes, LayoutResult]:
    playwright = _ensure_playwright()
    browser = _get_browser(playwright)
    page = browser.new_page()
    try:
        page.emulate_media(media="print")

        def render_fn(prepared: StructuredCV, *, compact: bool) -> str:
            return render_html_cv(prepared, template_id, compact=compact)

        layout = fit_cv_layout(cv, render_fn, _render_html_to_pdf_sync, page=page)
        page.set_content(layout.html, wait_until="load")
        page.wait_for_timeout(200)
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        return pdf_bytes, layout
    finally:
        page.close()


def render_html_to_pdf(html: str) -> bytes:
    future = _playwright_executor.submit(_render_html_to_pdf_sync, html)
    return future.result(timeout=90)


def render_cv_pdf_html(
    cv: StructuredCV,
    template_id: str = DEFAULT_TEMPLATE,
    *,
    truncate: bool = False,
) -> tuple[bytes, dict]:
    enriched = enrich_cv_links(cv.model_copy(deep=True))
    prepared = prepare_cv_for_pdf(enriched, truncate=truncate)

    future = _playwright_executor.submit(_render_cv_with_layout_sync, prepared, template_id)
    pdf_bytes, layout = future.result(timeout=90)
    meta = {
        "page_count": layout.page_count,
        "layout_tier": layout.layout_tier,
        "compact": layout.compact,
    }
    return pdf_bytes, meta


def render_cv_preview_html(cv: StructuredCV, template_id: str = DEFAULT_TEMPLATE) -> str:
    enriched = enrich_cv_links(cv.model_copy(deep=True))
    prepared = prepare_cv_for_pdf(enriched, truncate=False)
    return render_html_cv(prepared, template_id, compact=False)
