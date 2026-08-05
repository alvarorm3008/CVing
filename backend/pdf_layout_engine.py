"""Auto layout: fit CV on ONE page by compacting / summarizing, not by spilling to page 2."""

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
    Try full content first, then progressive compression until it fits 1 page.
    Prefer summarizing/dropping weaker bullets over a 2-page PDF.
    """
    # (tier_name, compact, compress_level)
    tiers = [
        ("standard", False, 0),
        ("compact", True, 0),
        ("summary", True, 1),
        ("bullets3", True, 2),
        ("bullets2", True, 3),
        ("tight", True, 4),
        ("minimal", True, 5),
    ]

    best_one_page: LayoutResult | None = None
    last_result: LayoutResult | None = None

    for tier_name, compact, compress_level in tiers:
        prepared = prepare_cv_for_pdf(
            cv.model_copy(deep=True),
            compress_level=compress_level,
        )
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
        last_result = result

        if pages <= 1:
            return result

        # Keep most-compressed overflow as fallback if nothing fits
        best_one_page = result

    # Last resort: most compressed layout (still usually closer to 1 page than full text)
    return best_one_page or last_result or LayoutResult(
        html="", compact=True, page_count=1, layout_tier="minimal"
    )
