"""Normalize structured CV data for professional PDF output.

Prefer full wording; when fitting to one page, compress by dropping
lower-priority bullets / shortening to whole sentences — never mid-word "…".
"""

from __future__ import annotations

import re

from cv_schema import ContactInfo, EducationItem, ExperienceItem, StructuredCV
from link_utils import (
    enrich_cv_links,
    is_project_entry,
    merge_bullets_preserving_urls,
)


_BULLET_PREFIX_RE = re.compile(r"^[\-•●▪]\s*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


def _clean_bullet(bullet: str) -> str:
    """Strip bullet markers only."""
    return _BULLET_PREFIX_RE.sub("", (bullet or "").strip())


def _norm_key(*parts: str) -> str:
    return " ".join(
        re.sub(r"\s+", " ", (p or "").strip().lower())
        for p in parts
        if (p or "").strip()
    )


def dedupe_education(items: list[EducationItem]) -> list[EducationItem]:
    """Drop duplicate education rows (same school/period or same degree+school)."""
    result: list[EducationItem] = []
    seen: set[str] = set()

    for item in items:
        degree = (item.degree or "").strip()
        school = (item.school or "").strip()
        period = (item.period or "").strip()
        if not degree and not school:
            continue

        keys: list[str] = []
        if school and period:
            keys.append(_norm_key(school, period))
        if degree and school:
            keys.append(_norm_key(degree, school))
        if degree and period:
            keys.append(_norm_key(degree, period))
        if not keys:
            keys.append(_norm_key(degree or school))

        if any(k in seen for k in keys):
            continue
        for k in keys:
            seen.add(k)
        result.append(EducationItem(degree=degree, school=school, period=period))
    return result


def merge_education(
    original: list[EducationItem],
    adapted: list[EducationItem],
) -> list[EducationItem]:
    """Prefer adapted wording once per school/period; never concatenate duplicates."""
    if not adapted:
        return dedupe_education(original)

    merged = dedupe_education(adapted)
    seen: set[str] = set()
    for item in merged:
        if item.school and item.period:
            seen.add(_norm_key(item.school, item.period))
        if item.degree and item.school:
            seen.add(_norm_key(item.degree, item.school))

    for item in original:
        degree = (item.degree or "").strip()
        school = (item.school or "").strip()
        period = (item.period or "").strip()
        if not degree and not school:
            continue
        keys: list[str] = []
        if school and period:
            keys.append(_norm_key(school, period))
        if degree and school:
            keys.append(_norm_key(degree, school))
        if any(k in seen for k in keys):
            continue
        for k in keys or [_norm_key(degree or school)]:
            seen.add(k)
        merged.append(EducationItem(degree=degree, school=school, period=period))

    return dedupe_education(merged)


def dedupe_strings(items: list[str]) -> list[str]:
    """Drop exact and near-duplicate strings (case/spacing; keep longer variant)."""
    cleaned: list[str] = []
    for raw in items:
        text = (raw or "").strip()
        if text:
            cleaned.append(text)

    result: list[str] = []
    for text in cleaned:
        key = _norm_key(text)
        if not key:
            continue
        replaced = False
        for i, prev in enumerate(result):
            prev_key = _norm_key(prev)
            # Exact or one contains the other (bilingual / paraphrased duplicate)
            if key == prev_key or key in prev_key or prev_key in key:
                if len(text) > len(prev):
                    result[i] = text
                replaced = True
                break
        if not replaced:
            result.append(text)
    return result


def dedupe_bullets(bullets: list[str]) -> list[str]:
    return dedupe_strings([_clean_bullet(b) for b in bullets if (b or "").strip()])


def dedupe_experience(items: list[ExperienceItem]) -> list[ExperienceItem]:
    """Drop duplicate roles with same company+period (or role+company); dedupe bullets."""
    result: list[ExperienceItem] = []
    seen: set[str] = set()
    for item in items:
        role = (item.role or "").strip()
        company = (item.company or "").strip()
        period = (item.period or "").strip()
        location = (item.location or "").strip()
        bullets = dedupe_bullets(item.bullets or [])
        if not role and not company and not bullets:
            continue
        keys: list[str] = []
        if company and period:
            keys.append(_norm_key(company, period))
        if role and company:
            keys.append(_norm_key(role, company))
        if role and period:
            keys.append(_norm_key(role, period))
        if not keys:
            keys.append(_norm_key(role, company, period))
        if any(k in seen for k in keys):
            for prev in result:
                prev_keys: list[str] = []
                if prev.company.strip() and prev.period.strip():
                    prev_keys.append(_norm_key(prev.company, prev.period))
                if prev.role.strip() and prev.company.strip():
                    prev_keys.append(_norm_key(prev.role, prev.company))
                if prev.role.strip() and prev.period.strip():
                    prev_keys.append(_norm_key(prev.role, prev.period))
                if any(k in prev_keys for k in keys):
                    prev.bullets = dedupe_bullets(list(prev.bullets) + bullets)
                    if not prev.role.strip() and role:
                        prev.role = role
                    if not prev.location.strip() and location:
                        prev.location = location
                    break
            continue
        for k in keys:
            seen.add(k)
        result.append(
            ExperienceItem(
                role=role,
                company=company,
                location=location,
                period=period,
                bullets=bullets,
            )
        )
    return result


def dedupe_cv(cv: StructuredCV) -> StructuredCV:
    """Remove duplicates across every list field of a structured CV."""
    out = cv.model_copy(deep=True)
    out.skills = dedupe_strings(out.skills)
    out.certifications = dedupe_strings(out.certifications)
    out.languages = dedupe_strings(out.languages)
    out.education = dedupe_education(out.education)
    out.experience = dedupe_experience(out.experience)
    if getattr(out, "projects", None):
        # Projects rarely used in PDF; still dedupe titles
        seen: set[str] = set()
        unique_projects = []
        for project in out.projects:
            title = (getattr(project, "title", None) or "").strip()
            key = _norm_key(title, getattr(project, "url", "") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            unique_projects.append(project)
        out.projects = unique_projects
    return out


def _first_sentences(text: str, max_chars: int) -> str:
    """Keep whole sentences under max_chars. Never append ellipsis."""
    cleaned = (text or "").strip()
    if not cleaned or len(cleaned) <= max_chars:
        return cleaned

    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(cleaned) if p.strip()]
    if not parts:
        return cleaned

    kept: list[str] = []
    for part in parts:
        candidate = " ".join(kept + [part]).strip()
        if kept and len(candidate) > max_chars:
            break
        kept.append(part)
        if len(candidate) >= max_chars:
            break

    if kept:
        return " ".join(kept)
    # One very long sentence: keep it intact (better than "…")
    return parts[0]


def _bullet_priority(bullet: str) -> int:
    """Higher = more worth keeping when compressing."""
    score = 0
    lower = bullet.lower()
    if re.search(r"\d", bullet):
        score += 3
    if any(tok in lower for tok in ("%","€", "$", "k ", "x ", "→")):
        score += 2
    if any(tok in lower for tok in ("led", "built", "reduced", "increased", "improved", "launched", "diseñ", "mejor", "reduj", "aument")):
        score += 1
    if "http" in lower or "github.com" in lower:
        score += 2
    score += min(len(bullet) // 40, 2)
    return score


def compress_cv_for_one_page(cv: StructuredCV, level: int = 1) -> StructuredCV:
    """
    Progressive compression to fit one A4 page.
    level 0 = no change; higher = more aggressive (still whole sentences / full bullets kept).
    """
    out = cv.model_copy(deep=True)
    if level <= 0:
        return out

    # Level 1+: shorten summary to whole sentences
    summary_limits = {1: 320, 2: 260, 3: 220, 4: 180, 5: 140}
    max_summary = summary_limits.get(level, 140)
    out.summary = _first_sentences(out.summary, max_summary)

    # Bullet caps per role by level
    bullet_caps = {1: 4, 2: 3, 3: 2, 4: 2, 5: 1}
    max_bullets = bullet_caps.get(level, 1)

    new_experience: list[ExperienceItem] = []
    for item in out.experience:
        bullets = [_clean_bullet(b) for b in item.bullets if b.strip()]
        if len(bullets) > max_bullets:
            ranked = sorted(bullets, key=_bullet_priority, reverse=True)
            keep = set(ranked[:max_bullets])
            # Preserve original order among kept bullets
            bullets = [b for b in bullets if b in keep][:max_bullets]

        # Level 3+: shorten very long bullets to first sentence(s)
        if level >= 3:
            char_cap = 160 if level == 3 else (130 if level == 4 else 110)
            bullets = [_first_sentences(b, char_cap) for b in bullets]

        new_experience.append(
            ExperienceItem(
                role=item.role,
                company=item.company,
                location=item.location,
                period=item.period,
                bullets=bullets,
            )
        )
    out.experience = new_experience

    # Level 4+: trim skills / certs / languages volume
    if level >= 4:
        out.skills = normalize_skills(out.skills)[:8]
        out.certifications = out.certifications[:3]
        out.languages = out.languages[:4]
    if level >= 5:
        out.skills = normalize_skills(out.skills)[:5]
        out.certifications = out.certifications[:2]
        if len(out.experience) > 4:
            out.experience = out.experience[:4]

    return out


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
    bullets = [_clean_bullet(b) for b in bullets_source if b.strip()]
    bullets = dedupe_bullets(bullets)

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
        return dedupe_experience(merged_jobs + merged_projects)

    merged_jobs = _merge_entry_lists(orig_jobs, adapted_jobs) if adapted_jobs else orig_jobs

    if adapted_projects:
        merged_projects = _merge_entry_lists(orig_projects, adapted_projects)
    else:
        merged_projects = [
            _merge_single_entry(p, p) for p in orig_projects if p.bullets or p.role.strip()
        ]

    return dedupe_experience(merged_jobs + merged_projects)


def preserve_contact(original: ContactInfo, updated: ContactInfo) -> None:
    """Nunca borrar datos de contacto del CV original."""
    for field in ("full_name", "email", "phone", "location", "linkedin", "github", "website"):
        new_val = (getattr(updated, field) or "").strip()
        old_val = (getattr(original, field) or "").strip()
        if not new_val and old_val:
            setattr(updated, field, old_val)


def normalize_skills(skills: list[str]) -> list[str]:
    """Deduplicate skills; keep full text (no ellipsis)."""
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
    return cleaned


def sync_headline(cv: StructuredCV, target_role: str = "") -> None:
    role = (target_role or "").strip()
    if role:
        cv.contact.headline = role
        return
    if (cv.contact.headline or "").strip():
        return
    if cv.summary:
        first = cv.summary.strip().split("\n")[0].strip()
        if first:
            cv.contact.headline = first


def prepare_cv_for_pdf(
    cv: StructuredCV,
    *,
    target_role: str = "",
    extra_text: str = "",
    truncate: bool = False,
    compress_level: int = 0,
) -> StructuredCV:
    """Last-mile cleanup before HTML/PDF render."""
    prepared = cv.model_copy(deep=True)
    enrich_cv_links(prepared, extra_text)
    prepared.projects = []
    prepared.experience = [e for e in prepared.experience if not is_project_entry(e)]

    sync_headline(prepared, target_role)
    prepared.summary = (prepared.summary or "").strip()
    prepared.skills = normalize_skills(prepared.skills)

    prepared.experience = [
        ExperienceItem(
            role=item.role.strip(),
            company=item.company.strip(),
            location=item.location.strip(),
            period=item.period.strip(),
            bullets=[_clean_bullet(b) for b in item.bullets if b.strip()],
        )
        for item in prepared.experience
        if item.role.strip() or item.company.strip() or item.bullets
    ]
    prepared = dedupe_cv(prepared)

    if compress_level > 0 or truncate:
        prepared = compress_cv_for_one_page(prepared, level=max(compress_level, 2 if truncate else 1))
        prepared = dedupe_cv(prepared)

    return prepared


PDF_CV_RULES = """
PDF / CV LAYOUT RULES (target: ONE page when possible):
- summary: 2–3 complete sentences (not mid-sentence cuts, never use ellipsis …)
- contact.headline: professional title matching the target job
- skills: 3–5 lines "Category: skill1, skill2, skill3"
- experience: preserve EVERY role, company, period and location — never drop employers
- bullets: 2–3 strong complete bullets per role (action + metric). Prefer fewer full bullets over truncated text with "…"
- Never shorten mid-word or mid-sentence with ellipsis. Drop weaker bullets instead if space is tight.
- contact.github: profile URL (e.g. https://github.com/username) — no separate projects section in PDF
- NEVER remove contact.linkedin, contact.github or URLs in bullets
- do not invent employers, dates or degrees
"""
