import os
import re
from html import escape

from markupsafe import Markup

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

_BARE_REPO_RE = re.compile(
    r"(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)/[^\s<>\"']+",
    re.IGNORECASE,
)

_LINKEDIN_BARE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-./%]+",
    re.IGNORECASE,
)

_KEYWORD_DOMAINS = (
    ("github", r"\b(GitHub|Github)\b"),
    ("gitlab", r"\b(GitLab|Gitlab)\b"),
    ("linkedin", r"\b(LinkedIn|Linked In)\b"),
)

_PROJECT_PIPE_RE = re.compile(
    r"^(?P<title>.+?)\s*\|\s*(?:(?P<label>GitHub|Github|GitLab)\s*:?\s*)?(?P<desc>.+)$",
    re.IGNORECASE,
)
_PROJECT_DASH_RE = re.compile(
    r"^(?P<title>.+?)\s+[-–—]\s+(?P<desc>.+)$",
    re.IGNORECASE,
)

_PROJECT_TITLE_RE = re.compile(
    r"^(?P<title>.+?)\s*\|\s*(?P<label>GitHub|Github|GitLab|Portfolio)\s*$",
    re.IGNORECASE,
)


def _ensure_https(url: str) -> str:
    cleaned = url.strip().rstrip(".,;:)")
    if cleaned.startswith(("http://", "https://", "mailto:", "tel:")):
        return cleaned
    if "@" in cleaned and " " not in cleaned and not cleaned.startswith("www."):
        return f"mailto:{cleaned}"
    if cleaned.startswith("www."):
        return f"https://{cleaned}"
    return f"https://{cleaned}"


def normalize_linkedin(value: str) -> tuple[str, str]:
    raw = (value or "").strip()
    if not raw:
        return "", ""
    if raw.lower() in ("linkedin", "linked in"):
        return "", "LinkedIn"
    return _ensure_https(raw), "LinkedIn"


def normalize_github(value: str) -> tuple[str, str]:
    raw = (value or "").strip()
    if not raw:
        return "", ""
    if raw.lower() in {"github"}:
        return "", "GitHub"
    if "github.com" not in raw.lower():
        raw = f"github.com/{raw.lstrip('@')}"
    return _ensure_https(raw), "GitHub"


def normalize_website(value: str) -> tuple[str, str]:
    raw = (value or "").strip()
    if not raw:
        return "", ""
    href = _ensure_https(raw)
    label = raw.replace("https://", "").replace("http://", "").rstrip("/")
    if len(label) > 40:
        label = label[:37] + "…"
    return href, label or "Website"


def build_contact_links(contact) -> list[dict[str, str]]:
    """Orden: email, teléfono, ubicación implícita en contact row, LinkedIn, web/GitHub."""
    links: list[dict[str, str]] = []

    email = (contact.email or "").strip()
    if email:
        links.append({"href": f"mailto:{email}", "label": email, "type": "email"})

    phone = (contact.phone or "").strip()
    if phone:
        tel = re.sub(r"[^\d+]", "", phone)
        links.append({"href": f"tel:{tel}", "label": phone, "type": "phone"})

    linkedin_href, linkedin_label = normalize_linkedin(contact.linkedin or "")
    if linkedin_href:
        links.append({"href": linkedin_href, "label": linkedin_label, "type": "linkedin"})

    github_raw = (getattr(contact, "github", None) or "").strip()
    if not github_raw and (contact.website or "").strip():
        if "github.com" in contact.website.lower():
            github_raw = contact.website.strip()

    github_href, github_label = normalize_github(github_raw)
    if github_href:
        links.append({"href": github_href, "label": github_label, "type": "github"})

    web_href, web_label = normalize_website(contact.website or "")
    if web_href and "github.com" not in web_href.lower():
        if not linkedin_href or web_href.lower() != linkedin_href.lower():
            links.append(
                {
                    "href": web_href,
                    "label": web_label,
                    "type": "website",
                }
            )

    return links


def _urls_by_domain(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for pattern in (_URL_RE, _BARE_REPO_RE, _LINKEDIN_BARE_RE):
        for match in pattern.finditer(text):
            raw = match.group(0)
            lower = raw.lower()
            for domain in ("github.com", "gitlab.com", "linkedin.com"):
                if domain in lower and domain not in found:
                    found[domain] = _ensure_https(raw)
    return found


def _find_urls(text: str) -> list[re.Match[str]]:
    matches = list(_URL_RE.finditer(text))
    for pattern in (_BARE_REPO_RE, _LINKEDIN_BARE_RE):
        for match in pattern.finditer(text):
            if not any(m.start() <= match.start() and m.end() >= match.end() for m in matches):
                matches.append(match)
    return sorted(matches, key=lambda m: m.start())


def _strip_repo_urls(text: str) -> str:
    cleaned = _URL_RE.sub("", text)
    cleaned = _BARE_REPO_RE.sub("", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip(" .,;")


def linkify_text(text: str) -> Markup:
    if not text or not text.strip():
        return Markup("")

    original = text.strip()
    domain_urls = _urls_by_domain(original)
    working = original
    parts: list[str] = []

    def link_for_url(raw: str) -> str:
        href = _ensure_https(raw)
        return f'<a href="{escape(href)}" class="link">{escape(raw)}</a>'

    last_end = 0
    for match in _find_urls(working):
        parts.append(escape(working[last_end : match.start()]))
        parts.append(link_for_url(match.group(0)))
        last_end = match.end()
    parts.append(escape(working[last_end:]))
    result = "".join(parts)

    for domain, pattern in _KEYWORD_DOMAINS:
        if domain + ".com" not in domain_urls:
            continue
        href = domain_urls[domain + ".com"]
        result = re.sub(
            pattern,
            rf'<a href="{escape(href)}" class="link">\1</a>',
            result,
            count=1,
            flags=re.IGNORECASE,
        )

    return Markup(result)


def _first_repo_url(text: str) -> tuple[str, str]:
    """Primera URL de repo en el texto: (texto original del documento, href clicable)."""
    for match in _find_urls(text):
        raw = match.group(0).rstrip(".,;:)")
        lower = raw.lower()
        if any(domain in lower for domain in ("github.com", "gitlab.com", "bitbucket.org")):
            return raw, _ensure_https(raw)
    return "", ""


def _project_title_from_bullet(bullet: str) -> str:
    bullet = bullet.strip()
    match = _PROJECT_PIPE_RE.match(bullet)
    if match:
        return match.group("title").strip()
    match = _PROJECT_DASH_RE.match(bullet)
    if match:
        title = match.group("title").strip()
        if "github.com" not in title.lower() and "gitlab.com" not in title.lower():
            return title
    raw, href = _first_repo_url(bullet)
    if href:
        return _repo_title_from_url(href)
    return bullet.split("|")[0].strip()


def restore_bullet_repo_url(adapted: str, original: str) -> str:
    """Restaura la URL del bullet original (misma lógica que preserve_contact para LinkedIn)."""
    if not original.strip():
        return adapted
    orig_raw, _ = _first_repo_url(original)
    if not orig_raw:
        return adapted

    adapt_raw, _ = _first_repo_url(adapted)
    if adapt_raw:
        if adapt_raw.rstrip("/").lower() != orig_raw.rstrip("/").lower():
            return adapted.replace(adapt_raw, orig_raw, 1)
        return adapted

    if "|" in adapted:
        title, _, rest = adapted.partition("|")
        title = title.strip()
        rest = rest.strip()
        if rest.lower().startswith(("github", "gitlab")):
            if ":" in rest:
                _, _, desc = rest.partition(":")
                rest = desc.strip()
            else:
                rest = ""
        if rest:
            return f"{title} | {orig_raw}: {rest}"
        return f"{title} | {orig_raw}"

    for sep in (" — ", " – ", " - "):
        if sep in adapted:
            title, desc = adapted.split(sep, 1)
            return f"{title.strip()} | {orig_raw}: {desc.strip()}"

    title = _project_title_from_bullet(adapted) or _project_title_from_bullet(original)
    desc = adapted.strip()
    if not desc or desc.lower() == title.lower():
        return f"{title} | {orig_raw}"
    return f"{title} | {orig_raw}: {desc}"


def merge_bullets_preserving_urls(
    original_bullets: list[str],
    adapted_bullets: list[str],
) -> list[str]:
    orig = [b.strip() for b in original_bullets if b and b.strip()]
    adapted = [b.strip() for b in adapted_bullets if b and b.strip()]
    if not orig:
        return adapted

    orig_by_title = {
        _project_title_from_bullet(b).lower(): b for b in orig if _project_title_from_bullet(b)
    }

    merged: list[str] = []
    for i, bullet in enumerate(adapted):
        orig_ref = orig[i] if i < len(orig) else ""
        if not orig_ref and len(orig) == 1:
            orig_ref = orig[0]
        if not orig_ref:
            orig_ref = orig_by_title.get(_project_title_from_bullet(bullet).lower(), "")
        merged.append(restore_bullet_repo_url(bullet, orig_ref))
    return merged


def _short_link_label(href: str) -> str:
    """Etiqueta corta para PDF: github.com/usuario/repo"""
    cleaned = href.strip().replace("https://", "").replace("http://", "").rstrip("/")
    if len(cleaned) > 48:
        return cleaned[:45] + "…"
    return cleaned


def _repo_title_from_url(href: str) -> str:
    slug = href.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").replace("_", " ").strip() or "Project"


def parse_project_bullet(bullet: str, fallback_title: str = "") -> dict:
    bullet = bullet.strip()
    github_raw, github_href = _first_repo_url(bullet)

    def _with_link(title: str, desc: str, label: str = "") -> dict:
        href = github_href
        if github_raw:
            link_label = github_raw
        elif href:
            link_label = _short_link_label(href)
        else:
            link_label = label
        clean_desc = _strip_repo_urls(desc)
        if github_raw and clean_desc.lower().replace(" ", "") == github_raw.lower().replace(" ", ""):
            clean_desc = ""
        resolved_title = title.strip()
        if not resolved_title:
            resolved_title = _repo_title_from_url(href) if href else (fallback_title or "Project")
        elif href and ("github.com" in resolved_title.lower() or "gitlab.com" in resolved_title.lower()):
            resolved_title = _repo_title_from_url(href)
        return {
            "title": resolved_title,
            "link_label": link_label,
            "link_href": href,
            "description": clean_desc,
            "description_html": linkify_text(clean_desc) if clean_desc else Markup(""),
        }

    match = _PROJECT_PIPE_RE.match(bullet)
    if match:
        title = match.group("title").strip()
        desc = (match.group("desc") or "").strip()
        label = (match.groupdict().get("label") or "").strip() if "label" in match.groupdict() else ""
        if not label and desc.lower() in {"github", "gitlab"} and not github_href:
            title_only = _PROJECT_TITLE_RE.match(bullet)
            if title_only:
                return _with_link(title_only.group("title").strip(), "", title_only.group("label"))
        return _with_link(title, desc, label)

    match = _PROJECT_DASH_RE.match(bullet)
    if match:
        title = match.group("title").strip()
        desc = (match.group("desc") or "").strip()
        label = (match.groupdict().get("label") or "").strip() if "label" in match.groupdict() else ""
        return _with_link(title, desc, label)

    title_only = _PROJECT_TITLE_RE.match(bullet)
    if title_only:
        return _with_link(title_only.group("title").strip(), "", title_only.group("label"))

    if "|" in bullet:
        title, _, rest = bullet.partition("|")
        return _with_link(title.strip() or fallback_title, rest.strip())

    if github_href:
        title = fallback_title or bullet.split("|")[0].strip()
        desc = _strip_repo_urls(bullet)
        if title and desc.lower().startswith(title.lower()):
            desc = desc[len(title) :].strip(" -–—:|")
        if not title or title.lower() in {"github", "gitlab"} or "github.com" in title.lower():
            title = _repo_title_from_url(github_href)
        return _with_link(title, desc)

    return {
        "title": fallback_title or bullet,
        "link_label": "",
        "link_href": "",
        "description": "",
        "description_html": linkify_text(bullet),
    }


def sync_projects_from_experience(cv) -> None:
    """Rellena cv.projects desde entradas de experiencia tipo proyecto."""
    from cv_schema import ProjectItem, StructuredCV

    if not isinstance(cv, StructuredCV):
        return
    if cv.projects:
        return

    projects: list[ProjectItem] = []
    for item in cv.experience:
        if not is_project_entry(item):
            continue
        if item.bullets:
            for bullet in item.bullets:
                if not bullet.strip():
                    continue
                parsed = parse_project_bullet(bullet, item.role)
                projects.append(
                    ProjectItem(
                        title=parsed["title"],
                        url=parsed["link_href"] or "",
                        description=parsed.get("description", ""),
                    )
                )
        elif item.role.strip():
            parsed = parse_project_bullet(item.role, item.role)
            projects.append(
                ProjectItem(
                    title=parsed["title"],
                    url=parsed["link_href"] or "",
                    description=parsed.get("description", ""),
                )
            )
    cv.projects = projects


_PROJECT_SECTION_ROLES = frozenset(
    {
        "relevant projects",
        "personal projects",
        "personal project",
        "projects",
        "proyectos relevantes",
        "proyectos personales",
        "proyectos",
        "proyecto personal",
        "selected projects",
        "side projects",
    }
)


def is_project_entry(item) -> bool:
    role = (item.role or "").strip().lower()
    company = (item.company or "").strip()
    if role in _PROJECT_SECTION_ROLES:
        return True
    if role.startswith("project") and not company:
        return True
    if role.startswith("proyecto") and not company:
        return True
    # Bullets con formato proyecto (GitHub / pipe) sin empresa
    if not company and item.bullets and all(
        "|" in b or "github" in b.lower() or "gitlab" in b.lower() for b in item.bullets
    ):
        return True
    return False


def _cv_text_blob(cv) -> str:
    """Concatena todo el texto del CV para buscar URLs."""
    parts: list[str] = []
    contact = cv.contact
    for value in (
        contact.full_name,
        contact.headline,
        contact.email,
        contact.phone,
        contact.location,
        contact.linkedin,
        contact.github,
        contact.website,
        cv.summary,
    ):
        if value and str(value).strip():
            parts.append(str(value).strip())
    for item in cv.experience:
        for value in (item.role, item.company, item.location, item.period):
            if value and str(value).strip():
                parts.append(str(value).strip())
        parts.extend(b.strip() for b in item.bullets if b and b.strip())
    for item in cv.education:
        for value in (item.degree, item.school, item.period):
            if value and str(value).strip():
                parts.append(str(value).strip())
    parts.extend(s.strip() for s in cv.skills if s and s.strip())
    parts.extend(c.strip() for c in cv.certifications if c and c.strip())
    return "\n".join(parts)


def enrich_cv_links(cv, extra_text: str = ""):
    """Rellena contact.linkedin / contact.website desde URLs en el CV."""
    from cv_schema import StructuredCV

    if not isinstance(cv, StructuredCV):
        return cv

    blob = _cv_text_blob(cv)
    if extra_text:
        blob = f"{blob}\n{extra_text}"

    urls = _urls_by_domain(blob)
    contact = cv.contact

    if not (contact.linkedin or "").strip() and urls.get("linkedin.com"):
        contact.linkedin = urls["linkedin.com"]

    if not (contact.github or "").strip() and urls.get("github.com"):
        contact.github = urls["github.com"]
    elif not (contact.github or "").strip() and (contact.website or "").strip():
        if "github.com" in contact.website.lower():
            contact.github = contact.website.strip()
            contact.website = ""

    if not (contact.website or "").strip() and urls.get("gitlab.com"):
        contact.website = urls["gitlab.com"]

    default_github = os.getenv("DEFAULT_GITHUB_USERNAME", "").strip()
    if not (contact.github or "").strip() and default_github:
        contact.github = f"https://github.com/{default_github.lstrip('@')}"

    # linkedin.com/in/... a veces queda solo como texto "LinkedIn" junto a URL en otra línea
    if not (contact.linkedin or "").strip():
        for match in _LINKEDIN_BARE_RE.finditer(blob):
            contact.linkedin = _ensure_https(match.group(0))
            break

    return cv


def parse_skill_groups(skills: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    groups: list[dict[str, str]] = []
    flat: list[str] = []
    for skill in skills:
        cleaned = skill.strip()
        if not cleaned:
            continue
        if ":" in cleaned:
            category, items = cleaned.split(":", 1)
            groups.append({"category": category.strip(), "items": items.strip()})
        else:
            flat.append(cleaned)

    if len(flat) > 8:
        mid = len(flat) // 2
        groups.append({"category": "Skills", "items": ", ".join(flat[:mid])})
        groups.append({"category": "Tools", "items": ", ".join(flat[mid:])})
        flat = []
    elif len(flat) > 3:
        groups.append({"category": "Skills", "items": ", ".join(flat)})
        flat = []

    return groups, flat
