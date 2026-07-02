"""Fetch and extract text from public job posting URLs."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

import httpx

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
MIN_TEXT_LENGTH = 200
USER_AGENT = (
    "Mozilla/5.0 (compatible; CVingBot/1.0; +https://github.com/alvarorm3008/CVing)"
)


def _validate_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    host = (parsed.hostname or "").lower()
    if not host or host in BLOCKED_HOSTS or host.endswith(".local"):
        raise ValueError("Invalid or blocked URL.")
    return url.strip()


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p\s*>", "\n\n", html)
    html = re.sub(r"(?is)</li\s*>", "\n", html)
    html = re.sub(r"(?is)<li[^>]*>", "- ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    text = unescape(html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_title(html: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if match:
        return unescape(re.sub(r"\s+", " ", match.group(1))).strip()[:200]
    return ""


def fetch_job_offer_text(url: str) -> dict:
    clean_url = _validate_url(url)

    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(clean_url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(f"Could not fetch URL: {exc}") from exc

    content_type = response.headers.get("content-type", "").lower()
    raw = response.text

    if "html" not in content_type and not raw.lstrip().startswith("<"):
        text = raw.strip()
        title = ""
    else:
        title = _extract_title(raw)
        text = _strip_html(raw)

    warning = None
    if len(text) < MIN_TEXT_LENGTH:
        host = urlparse(clean_url).hostname or ""
        if "linkedin.com" in host or "indeed.com" in host:
            warning = (
                "LinkedIn and Indeed often block automated access. "
                "Copy and paste the job description manually."
            )
        raise ValueError(
            warning
            or "Could not extract enough text from this page. Paste the job description manually."
        )

    if len(text) > 15000:
        text = text[:15000] + "\n\n[… truncated …]"

    return {
        "text": text,
        "title": title,
        "source_url": clean_url,
        "warning": warning,
    }
