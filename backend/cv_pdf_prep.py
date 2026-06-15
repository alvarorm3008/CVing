"""Normalize structured CV data for professional PDF output."""

from __future__ import annotations

import re

from cv_schema import ContactInfo, ExperienceItem, StructuredCV
from link_utils import (
    enrich_cv_links,
    is_project_entry,
    merge_bullets_preserving_urls,
    _first_repo_url,
)

_MAX_SUMMARY_CHARS = 400
_MAX_BULLET_CHARS = 130
_MAX_BULLETS_PER_ROLE = 3
_MAX_SKILL_ITEMS = 24

_BULLET_PREFIX_RE = re.compile(r"^[\-•●▪]\s*")


def _trim_text(text: str, max_len: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[: max_len - 1].rsplit(" ", 1)[0]
    return f"{cut}…" if cut else cleaned[: max_len - 1] + "…"


def _clean_bullet(bullet: str) -> str:
    cleaned = _BULLET_PREFIX_RE.sub("", bullet.strip())
    if _first_repo_url(cleaned)[0]:
        return cleaned
    return _trim_text(cleaned, _MAX_BULLET_CHARS)


def _entry_key(item: ExperienceItem, *, translated: bool = False) -> tuple[str, str]:
    company = item.company.strip().lower()
    period = item.period.strip().lower()
    if translated and (company or period):
        return (company, period)
    return (item.role.strip().lower(), company)


def _merge_single_entry(
    original: ExperienceItem | None,
    adapted: ExperienceItem,
) -> ExperienceItem:
    base = original
    bullets_source = adapted.bullets if adapted.bullets else (base.bullets if base else [])
    if base and is_project_entry(base) and bullets_source:
        bullets_source = merge_bullets_preserving_urls(base.bullets, bullets_source)
    bullets = [_clean_bullet(b) for b in bullets_source if b.strip()][:_MAX_BULLETS_PER_ROLE]

    role = adapted.role.strip() or (base.role.strip() if base else "")
    company = adapted.company.strip() or (base.company.strip() if base else "")

    return ExperienceItem(
        role=role,
        company=company,
        location=adapted.location.strip() or (base.location.strip() if base else ""),
        period=adapted.period.strip() or (base.period.strip() if base else ""),
        bullets=bullets,
    )


def _merge_entry_lists(
    original: list[ExperienceItem],
    adapted: list[ExperienceItem],
    *,
    translated: bool = False,
) -> list[ExperienceItem]:
    if translated:
        merged: list[ExperienceItem] = []
        for i, item in enumerate(adapted):
            orig_ref = original[i] if i < len(original) else None
            merged.append(_merge_single_entry(orig_ref, item))
        return merged

    index = {
        _entry_key(item, translated=False): item
        for item in original
        if _entry_key(item, translated=False)[0] or _entry_key(item, translated=False)[1]
    }

    merged: list[ExperienceItem] = []
    seen: set[tuple[str, str]] = set()

    for item in adapted:
        key = _entry_key(item, translated=False)
        merged.append(_merge_single_entry(index.get(key), item))
        seen.add(key)

    for item in original:
        key = _entry_key(item, translated=False)
        if key in seen:
            continue
        if not (key[0] or key[1] or item.bullets):
            continue
        merged.append(_merge_single_entry(item, item))

    return merged


def merge_experience(
    original: list[ExperienceItem],
    adapted: list[ExperienceItem],
    *,
    translated: bool = False,
) -> list[ExperienceItem]:
    """Fusiona adaptación con original; nunca pierde proyectos ni puestos."""
    orig_jobs = [e for e in original if not is_project_entry(e)]
    orig_projects = [e for e in original if is_project_entry(e)]
    adapted_jobs = [e for e in adapted if not is_project_entry(e)]
    adapted_projects = [e for e in adapted if is_project_entry(e)]

    if translated:
        merged_jobs = (
            _merge_entry_lists(orig_jobs, adapted_jobs, translated=True)
            if adapted_jobs
            else []
        )
        merged_projects = (
            _merge_entry_lists(orig_projects, adapted_projects, translated=True)
            if adapted_projects
            else []
        )
        return merged_jobs + merged_projects

    merged_jobs = _merge_entry_lists(orig_jobs, adapted_jobs) if adapted_jobs else orig_jobs

    if adapted_projects:
        merged_projects = _merge_entry_lists(orig_projects, adapted_projects)
    else:
        merged_projects = [
            _merge_single_entry(p, p) for p in orig_projects if p.bullets or p.role.strip()
        ]

    return merged_jobs + merged_projects


def preserve_contact(original: ContactInfo, updated: ContactInfo) -> None:
    """Nunca borrar datos de contacto del CV original."""
    for field in ("full_name", "email", "phone", "location", "linkedin", "github", "website"):
        new_val = (getattr(updated, field) or "").strip()
        old_val = (getattr(original, field) or "").strip()
        if not new_val and old_val:
            setattr(updated, field, old_val)


def normalize_skills(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for skill in skills:
        text = (skill or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)

    if len(cleaned) <= _MAX_SKILL_ITEMS:
        return cleaned

    grouped: list[str] = []
    flat: list[str] = []
    for skill in cleaned:
        if ":" in skill:
            grouped.append(skill)
        else:
            flat.append(skill)

    if flat:
        grouped.append(f"Other: {', '.join(flat[:10])}")
    return grouped[:_MAX_SKILL_ITEMS]


def sync_headline(cv: StructuredCV, target_role: str = "") -> None:
    role = (target_role or "").strip()
    if role:
        cv.contact.headline = role
        return
    if (cv.contact.headline or "").strip():
        return
    if cv.summary:
        first = cv.summary.strip().split("\n")[0].strip()
        if len(first) < 90:
            cv.contact.headline = first


def prepare_cv_for_pdf(
    cv: StructuredCV,
    *,
    target_role: str = "",
    extra_text: str = "",
    truncate: bool = True,
) -> StructuredCV:
    """Last-mile cleanup before HTML/PDF render."""
    prepared = cv.model_copy(deep=True)
    enrich_cv_links(prepared, extra_text)
    prepared.projects = []
    prepared.experience = [e for e in prepared.experience if not is_project_entry(e)]

    sync_headline(prepared, target_role)
    if truncate:
        prepared.summary = _trim_text(prepared.summary, _MAX_SUMMARY_CHARS)
        prepared.skills = normalize_skills(prepared.skills)

        prepared.experience = [
            ExperienceItem(
                role=item.role.strip(),
                company=item.company.strip(),
                location=item.location.strip(),
                period=item.period.strip(),
                bullets=[_clean_bullet(b) for b in item.bullets if b.strip()][:_MAX_BULLETS_PER_ROLE],
            )
            for item in prepared.experience
            if item.role.strip() or item.company.strip() or item.bullets
        ]
    else:
        prepared.experience = [
            ExperienceItem(
                role=item.role.strip(),
                company=item.company.strip(),
                location=item.location.strip(),
                period=item.period.strip(),
                bullets=[_BULLET_PREFIX_RE.sub("", b.strip()) for b in item.bullets if b.strip()],
            )
            for item in prepared.experience
            if item.role.strip() or item.company.strip() or item.bullets
        ]

    return prepared


PDF_CV_RULES = """
PDF / CV LAYOUT RULES (critical — output must fit ONE page when possible):
- summary: 2–3 sentences, max 380 characters
- contact.headline: professional title matching the target job
- skills: 3–5 lines "Category: skill1, skill2, skill3"
- experience: preserve EVERY role, company, period and location from source CV — never drop employers
- bullets: max 3 per role, max 120 characters each, action verb + metric
- contact.github: profile URL (e.g. https://github.com/username) — no separate projects section in PDF
- NEVER remove contact.linkedin, contact.github or URLs in bullets
- do not invent employers, dates or degrees
"""
