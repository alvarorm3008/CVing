"""Deterministic contact-field fill from raw CV text (no AI)."""

from __future__ import annotations

import re

from link_utils import _ensure_https, _LINKEDIN_BARE_RE, normalize_github, normalize_linkedin

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)

# International-ish phones: +34 600..., (34)..., 600 12 34 56, etc.
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+|00)?\s*(?:\(?\d{1,4}\)?[\s.\-]*)?(?:\d[\s.\-]*){8,14}\d(?!\w)",
)

_GITHUB_PROFILE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9\-]{0,38}[A-Za-z0-9])?)"
    r"(?:/(?!repos?\b)[^\s]*)?",
    re.IGNORECASE,
)

_WEBSITE_RE = re.compile(
    r"(?<!@)(?:https?://|www\.)(?!linkedin\.com|github\.com|gitlab\.com|bitbucket\.org)"
    r"([a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+(?:/[^\s<>\"']*)?)",
    re.IGNORECASE,
)

_FALSE_PHONE_HINTS = (
    "http",
    "www.",
    "@",
    "linkedin",
    "github",
)


def _looks_like_phone(candidate: str) -> bool:
    digits = re.sub(r"\D", "", candidate)
    if len(digits) < 9 or len(digits) > 15:
        return False
    lower = candidate.lower()
    if any(h in lower for h in _FALSE_PHONE_HINTS):
        return False
    # Reject years / pure ids that are too short after stripping country
    if len(digits) == 4:
        return False
    return True


def extract_email(text: str) -> str:
    for match in _EMAIL_RE.finditer(text or ""):
        email = match.group(0).strip().rstrip(".,;)")
        if email.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            continue
        return email
    return ""


def extract_phone(text: str) -> str:
    for match in _PHONE_RE.finditer(text or ""):
        raw = match.group(0).strip()
        if _looks_like_phone(raw):
            # Normalize spacing lightly
            return re.sub(r"\s+", " ", raw).strip()
    return ""


def extract_linkedin(text: str) -> str:
    for match in _LINKEDIN_BARE_RE.finditer(text or ""):
        href, _ = normalize_linkedin(match.group(0))
        if href:
            return href
    return ""


def extract_github(text: str) -> str:
    for match in _GITHUB_PROFILE_RE.finditer(text or ""):
        user = match.group(1)
        # Skip common non-profile paths
        if user.lower() in {"features", "topics", "collections", "events", "settings", "orgs", "marketplace"}:
            continue
        href, _ = normalize_github(f"https://github.com/{user}")
        if href:
            return href
    return ""


def extract_website(text: str) -> str:
    for match in _WEBSITE_RE.finditer(text or ""):
        raw = match.group(0).strip().rstrip(".,;)")
        lower = raw.lower()
        if any(d in lower for d in ("linkedin.com", "github.com", "gitlab.com", "bitbucket.org")):
            continue
        if "@" in raw:
            continue
        return _ensure_https(raw)
    return ""


def fill_missing_contact(cv, source_text: str = ""):
    """Fill empty contact fields from regex/URL hits in source_text (+ CV blob)."""
    from cv_schema import StructuredCV
    from link_utils import _cv_text_blob

    if not isinstance(cv, StructuredCV):
        return cv

    blob = _cv_text_blob(cv)
    if source_text:
        blob = f"{source_text}\n{blob}"

    contact = cv.contact

    if not (contact.email or "").strip():
        contact.email = extract_email(blob)

    if not (contact.phone or "").strip():
        contact.phone = extract_phone(blob)

    if not (contact.linkedin or "").strip():
        contact.linkedin = extract_linkedin(blob)

    if not (contact.github or "").strip():
        contact.github = extract_github(blob)

    if not (contact.website or "").strip():
        web = extract_website(blob)
        if web and "github.com" not in web.lower() and "linkedin.com" not in web.lower():
            contact.website = web

    # If website was actually a github profile, move it
    if (contact.website or "").strip() and "github.com" in contact.website.lower():
        if not (contact.github or "").strip():
            contact.github = contact.website.strip()
        contact.website = ""

    return cv
