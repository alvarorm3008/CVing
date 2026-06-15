"""Fallback web search when not using Gemini grounding."""

from __future__ import annotations

from salary_research import extract_offer_hints


def _extract_search_terms(text: str) -> list[str]:
    hints = extract_offer_hints(text)
    company = hints["company"]
    role = hints["role"]
    location = hints["location"] or "España"

    queries: list[str] = []
    if company and role:
        queries.extend(
            [
                f"{company} empresa qué hace cultura",
                f"salario {role} {company} {location}",
                f"salario medio {role} {location} 2024 2025",
                f"{company} opiniones empleados glassdoor indeed",
                f"carrera profesional {role} {company}",
            ]
        )
    elif company:
        queries.extend(
            [
                f"{company} empresa información cultura valores",
                f"{company} salarios empleados {location}",
            ]
        )
    else:
        queries.append(f"salario medio empleo {location} glassdoor indeed")

    return queries[:6]


def build_web_context(prompt: str) -> tuple[str, list[dict[str, str]]]:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "", []

    queries = _extract_search_terms(prompt)
    snippets: list[str] = []
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = list(ddgs.text(query, max_results=4))
            except Exception:
                continue

            for item in results:
                url = (item.get("href") or "").strip()
                title = (item.get("title") or url).strip()
                body = (item.get("body") or "").strip()
                if not body:
                    continue
                snippets.append(f"[{title}] {body}")
                if url and url not in seen:
                    seen.add(url)
                    sources.append({"title": title, "url": url})

    return "\n".join(snippets[:20]), sources
