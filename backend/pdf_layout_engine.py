"""Auto layout: intenta 1 página, permite 2 si hace falta."""

from __future__ import annotations

from dataclasses import dataclass

from cv_pdf_prep import prepare_cv_for_pdf
from cv_schema import StructuredCV

# Altura útil A4 con márgenes 14mm+17mm ≈ 257mm → ~970px a 96dpi print
_A4_CONTENT_HEIGHT_PX = 970


@dataclass
class LayoutResult:
    html: str
    compact: bool
    page_count: int
    layout_tier: str


def _measure_content_height(page) -> float:
    return page.evaluate(
        """() => {
            const el = document.querySelector('.page') || document.body;
            return el.scrollHeight;
        }"""
    )


def _estimate_page_count(height_px: float, compact: bool) -> int:
    usable = _A4_CONTENT_HEIGHT_PX * (0.92 if compact else 1.0)
    return max(1, int((height_px + usable - 1) // usable))


def fit_cv_layout(
    cv: StructuredCV,
    render_html_fn,
    render_pdf_fn,
    *,
    page,
) -> LayoutResult:
    """
    Prueba niveles de compactación y devuelve HTML + metadata.
    render_html_fn(cv, compact) -> str
    render_pdf_fn(html) -> bytes  (solo usado si hace falta validar)
    """
    tiers = [
        ("standard", False, True),
        ("compact", True, True),
        ("two_page", False, False),
    ]

    best: LayoutResult | None = None

    for tier_name, compact, truncate in tiers:
        prepared = prepare_cv_for_pdf(cv.model_copy(deep=True), truncate=truncate)
        html = render_html_fn(prepared, compact=compact)
        page.set_content(html, wait_until="load")
        page.wait_for_timeout(150)
        height = _measure_content_height(page)
        pages = _estimate_page_count(height, compact)

        result = LayoutResult(
            html=html,
            compact=compact,
            page_count=pages,
            layout_tier=tier_name,
        )

        if pages <= 1:
            return result

        if tier_name == "two_page":
            return LayoutResult(
                html=html,
                compact=False,
                page_count=2,
                layout_tier="two_page",
            )

        best = result

    return best or LayoutResult(html="", compact=True, page_count=1, layout_tier="compact")
