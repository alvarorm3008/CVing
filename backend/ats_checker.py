import re
from collections import OrderedDict

from cv_schema import StructuredCV
from language_utils import detect_language_hint

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "from", "into", "your", "you", "we", "our",
    "will", "can", "must", "should", "have", "has", "had", "been", "being", "are", "was", "were",
    "this", "that", "these", "those", "not", "but", "all", "any", "each", "other", "such", "than",
    "then", "them", "they", "their", "there", "about", "above", "after", "before", "between",
    "during", "under", "over", "out", "off", "on", "in", "at", "to", "of", "as", "by", "is", "it",
    "be", "do", "does", "did", "done", "via", "per", "etc", "years", "year", "experience",
    "required", "requirements", "responsibilities", "ability", "skills", "skill", "work",
    "working", "team", "role", "position", "job", "candidate", "candidates", "company",
    "including", "include", "using", "use", "used", "based", "within", "across", "strong",
    "good", "great", "high", "level", "plus", "minimum", "preferred", "ideally", "looking",
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en", "con", "por",
    "para", "que", "como", "mas", "muy", "sin", "sobre", "entre", "ser", "es", "son",
    "esta", "este", "estos", "estas", "tus", "sus", "nuestro", "nuestra", "años", "año",
    "experiencia", "trabajo", "equipo", "empresa", "puesto", "candidato", "requisitos",
    "responsabilidades", "habilidades", "conocimientos", "nivel", "minimo", "deseable",
    "oferta", "empleo", "descripcion", "buscamos", "necesitamos", "valoramos", "unirte",
    "incorporar", "personas", "persona", "perfil", "titulacion", "titulación", "universitario",
}

JUNK_PHRASE_FRAGMENTS = (
    "oferta del empleo",
    "descripcion del puesto",
    "descripción del puesto",
    "sobre la empresa",
    "sobre nosotros",
    "que ofrecemos",
    "qué ofrecemos",
    "unirte a",
    "nuestro equipo",
    "buscamos a",
    "join our team",
    "job description",
    "about the company",
    "what we offer",
    "what you'll do",
    "qué harás",
    "que haras",
    "responsabilidades del puesto",
    "funciones del puesto",
)

TECH_PATTERNS = [
    r"\b(?:python|java|javascript|typescript|react|vue|angular|node\.?js|fastapi|django|flask)\b",
    r"\b(?:sql|postgresql|postgres|mysql|mongodb|redis|docker|kubernetes|aws|azure|gcp|git)\b",
    r"\b(?:excel|power\s*bi|tableau|figma|jira|agile|scrum|ci/?cd|rest|api|graphql)\b",
    r"\b(?:machine learning|deep learning|data analysis|project management)\b",
    r"\b(?:c\+\+|c#|\.net|ruby|rails|go|golang|rust|kotlin|swift|php|laravel|spring)\b",
    r"\b(?:html|css|tailwind|next\.?js|vite|webpack|linux|bash|terraform|ansible)\b",
    r"\b(?:pandas|numpy|pytorch|tensorflow|spark|hadoop|kafka|elasticsearch|supabase)\b",
    r"\b(?:seo|sem|crm|erp|saas|b2b|b2c|kpi|ux|ui|devops|microservices|microservicios)\b",
    r"\b(?:selenium|playwright|cypress|jest|pytest|maven|gradle|npm|yarn|pnpm)\b",
]

REQ_HEADER = re.compile(
    r"(?i)^(?:"
    r"requisitos?(?:\s+(?:m[ií]nimos?|deseables?|indispensables?|t[eé]cnicos?|del?\s+puesto))?"
    r"|conocimientos?\s+t[eé]cnicos?"
    r"|tecnolog[ií]as?"
    r"|stack(?:\s+t[eé]cnico)?"
    r"|herramientas"
    r"|qualifications?"
    r"|requirements?"
    r"|must[\s-]?have(?:s)?"
    r"|nice[\s-]?to[\s-]?have"
    r"|qu[eé]\s+(?:necesitamos|buscamos|pedimos|requerimos)"
    r"|lo\s+que\s+(?:necesitas|necesitamos|buscamos|pedimos)"
    r"|what\s+you(?:'ll|\s+will)\s+need"
    r"|your\s+profile"
    r"|perfil\s+(?:requerido|ideal|buscado)"
    r"|(?:se\s+)?valorar[aá]"
    r")\s*:?\s*$"
)

SKIP_HEADER = re.compile(
    r"(?i)^(?:"
    r"sobre(?:\s+(?:la\s+)?empresa|\s+nosotros)?"
    r"|about(?:\s+the\s+company|\s+us)?"
    r"|beneficios"
    r"|qu[eé]\s+ofrecemos"
    r"|what\s+we\s+offer"
    r"|responsabilidades(?:\s+del\s+puesto)?"
    r"|funciones(?:\s+del\s+puesto)?"
    r"|tareas"
    r"|what\s+you(?:'ll|\s+will)\s+do"
    r"|descripci[oó]n(?:\s+del\s+puesto|\s+de\s+la\s+oferta)?"
    r"|qui[eé]nes\s+somos"
    r"|who\s+we\s+are"
    r"|apply"
    r"|solicitud"
    r"|proceso\s+de\s+selecci[oó]n"
    r")\s*:?\s*$"
)

REQUIREMENT_LINE = re.compile(r"^(?:[-•*▪]|\d+[.)])\s*(.+)$")
TECH_IN_TEXT = re.compile("|".join(f"(?:{p})" for p in TECH_PATTERNS), re.IGNORECASE)
KNOWN_TECH = {
    "python", "java", "javascript", "typescript", "react", "vue", "angular", "node", "nodejs",
    "fastapi", "django", "flask", "sql", "postgresql", "postgres", "mysql", "mongodb", "redis",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "excel", "tableau", "figma", "jira",
    "agile", "scrum", "rest", "api", "graphql", "linux", "bash", "terraform", "nextjs", "vite",
    "pandas", "numpy", "pytorch", "tensorflow", "spark", "kafka", "selenium", "supabase",
}


def structured_cv_to_text(cv: StructuredCV) -> str:
    parts: list[str] = []
    contact = cv.contact
    if contact.full_name:
        parts.append(contact.full_name)
    if contact.headline:
        parts.append(contact.headline)
    if cv.summary:
        parts.append(cv.summary)
    if cv.skills:
        parts.append("\n".join(cv.skills))
    for item in cv.experience:
        parts.append(f"{item.role} {item.company}")
        parts.extend(item.bullets)
    for item in cv.education:
        parts.append(f"{item.degree} {item.school}")
    if cv.languages:
        parts.extend(cv.languages)
    if cv.certifications:
        parts.extend(cv.certifications)
    return "\n".join(parts)


def _normalize_token(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().lower())


def _looks_like_header(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return False
    if REQUIREMENT_LINE.match(stripped):
        return False
    header = stripped.rstrip(":")
    if REQ_HEADER.match(header) or SKIP_HEADER.match(header):
        return True
    if stripped.endswith(":") and len(header.split()) <= 8:
        return True
    if stripped.isupper() and len(stripped.split()) <= 8:
        return True
    return False


def _extract_requirements_text(job_description: str) -> str:
    lines = job_description.splitlines()
    chunks: list[str] = []
    in_req = False
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append("\n".join(current))
            current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_req:
                flush()
            continue

        if _looks_like_header(stripped):
            flush()
            header = stripped.rstrip(":")
            if SKIP_HEADER.match(header):
                in_req = False
            elif REQ_HEADER.match(header):
                in_req = True
            else:
                in_req = False
            continue

        if in_req:
            current.append(stripped)

    flush()

    if chunks:
        return "\n\n".join(chunks)

    # Fallback: bullet lines that mention a known technology
    tech_bullets = []
    for line in lines:
        bullet = REQUIREMENT_LINE.match(line.strip())
        if bullet and TECH_IN_TEXT.search(bullet.group(1)):
            tech_bullets.append(bullet.group(1))
    if tech_bullets:
        return "\n".join(tech_bullets)

    return ""


def _is_junk_phrase(phrase: str) -> bool:
    if any(fragment in phrase for fragment in JUNK_PHRASE_FRAGMENTS):
        return True
    words = phrase.split()
    if len(words) > 4:
        return True
    if len(words) >= 2 and all(word in STOPWORDS for word in words):
        return True
    if words and words[0] in STOPWORDS and words[-1] in STOPWORDS:
        return True
    return False


def _is_valid_keyword(phrase: str) -> bool:
    if len(phrase) < 2 or len(phrase) > 40:
        return False
    if _is_junk_phrase(phrase):
        return False
    if TECH_IN_TEXT.search(phrase):
        return True
    compact = phrase.replace(".", "").replace("-", "")
    if compact in KNOWN_TECH:
        return True
    words = phrase.split()
    if len(words) == 1:
        if phrase in STOPWORDS:
            return False
        # Single token only if it looks technical (digits, +, #, or CamelCase origin)
        if re.fullmatch(r"[a-z0-9+#./]+", phrase) and len(phrase) >= 2:
            return phrase not in STOPWORDS
        return False
    # Multi-word: must contain a tech match or be a known compound like "machine learning"
    return bool(TECH_IN_TEXT.search(phrase))


def _split_skill_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    text = re.sub(r"\([^)]*\)", " ", text)
    for part in re.split(r"[,;/|•·]|(?:\s+y\s+|\s+and\s+|\s+e\s+|\s+o\s+|\s+or\s+)", text, flags=re.IGNORECASE):
        part = _normalize_token(part)
        part = re.sub(r"^[\(\[]|[\)\]]$", "", part).strip()
        part = re.sub(
            r"^(?:experiencia|experience|dominio|conocimientos?|know(?:ledge)?|skills?)\s+(?:en|de|in|with|of)\s+",
            "",
            part,
            flags=re.IGNORECASE,
        )
        part = re.sub(r"^(?:m[ií]nimo|minimum|al menos|at least)\s+\d+\s+años?\s+(?:de\s+)?", "", part)
        if part:
            candidates.append(part)
    return candidates


def _extract_keywords(requirements_text: str, full_job: str) -> list[str]:
    found: OrderedDict[str, None] = OrderedDict()
    scan_text = requirements_text or full_job

    for pattern in TECH_PATTERNS:
        for match in re.finditer(pattern, scan_text, re.IGNORECASE):
            phrase = _normalize_token(match.group(0))
            if _is_valid_keyword(phrase):
                found[phrase] = None

    lines = (requirements_text or "").splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        bullet = REQUIREMENT_LINE.match(stripped)
        content = bullet.group(1) if bullet else stripped
        if not bullet and not TECH_IN_TEXT.search(content):
            continue
        for candidate in _split_skill_candidates(content):
            if _is_valid_keyword(candidate):
                found[candidate] = None

    if not found and requirements_text:
        for candidate in _split_skill_candidates(requirements_text.replace("\n", ", ")):
            if _is_valid_keyword(candidate):
                found[candidate] = None

    return list(found.keys())[:30]


def _guess_role(job_description: str) -> str:
    lines = [line.strip() for line in job_description.splitlines() if line.strip()]
    for line in lines[:6]:
        if len(line) < 80 and not line.startswith(("-", "•", "*")):
            if not REQ_HEADER.match(line) and not SKIP_HEADER.match(line.rstrip(":")):
                return line
    return ""


def _keyword_in_cv(keyword: str, cv_text: str) -> bool:
    cv_lower = cv_text.lower()
    keyword_lower = keyword.lower()
    if keyword_lower in cv_lower:
        return True
    tokens = keyword_lower.split()
    if len(tokens) > 1:
        return all(token in cv_lower for token in tokens if len(token) > 2)
    return False


ATS_MESSAGES: dict[str, dict[str, str]] = {
    "es": {
        "no_req_section": "No detecté una sección clara de requisitos. Añade títulos como «Requisitos» o «Qué buscamos» en la oferta.",
        "add_keyword": "Añade «{keyword}» en skills o experiencia si lo dominas (tecnología detectada en requisitos).",
        "no_tech": "No encontré tecnologías concretas en los requisitos. Revisa que la oferta tenga una sección de requisitos/stack.",
        "low_score": "Encaje bajo con las tecnologías pedidas: refuerza skills y bullets con las que faltan.",
        "near_pass": "Cerca del umbral ATS: añade las tecnologías que faltan en la sección de skills.",
        "expand_cv": "Amplía la experiencia con logros concretos y métricas (%, €, tiempos).",
        "matched_ratio": "Tecnologías detectadas en requisitos: {matched}/{total} ya aparecen en tu CV.",
        "job_required": "La descripción de la oferta es obligatoria.",
        "cv_required": "No se pudo leer texto del CV.",
        "no_tech_apply": "No se detectaron tecnologías en los requisitos — revisa la oferta o adapta el CV manualmente.",
        "apply_now": "Las tecnologías clave de los requisitos aparecen en tu CV (análisis local).",
        "apply_moderate": "Encaje moderado: faltan algunas tecnologías pedidas en requisitos.",
        "apply_low": "Faltan varias tecnologías que la oferta pide en requisitos.",
        "notes": "Análisis local (solo requisitos/tecnologías): {matched} coincidencias, {partial} parciales, {missing} ausentes.",
        "notes_no_req": " No se encontró sección de requisitos — solo se usaron bullets con tecnologías.",
        "why_needed": "Tecnología pedida en requisitos y no detectada claramente en tu CV.",
        "how_to_learn": "Añádela en skills o en un bullet si tienes experiencia real.",
        "evidence": "Detectado en el texto del CV",
    },
    "en": {
        "no_req_section": "No clear requirements section found. Add headings like «Requirements» or «What we're looking for» in the job post.",
        "add_keyword": "Add «{keyword}» to skills or experience if you know it (technology found in requirements).",
        "no_tech": "No concrete technologies found in requirements. Check the job post has a requirements/stack section.",
        "low_score": "Low match with required technologies: strengthen skills and bullets for missing ones.",
        "near_pass": "Close to ATS threshold: add missing technologies to your skills section.",
        "expand_cv": "Expand experience with concrete achievements and metrics (%, €, time saved).",
        "matched_ratio": "Technologies in requirements: {matched}/{total} already appear in your CV.",
        "job_required": "Job description is required.",
        "cv_required": "Could not read CV text.",
        "no_tech_apply": "No technologies detected in requirements — review the job post or adapt the CV manually.",
        "apply_now": "Key technologies from requirements appear in your CV (local analysis).",
        "apply_moderate": "Moderate match: some required technologies are missing.",
        "apply_low": "Several technologies requested in the job post are missing from your CV.",
        "notes": "Local analysis (requirements/technologies only): {matched} matches, {partial} partial, {missing} missing.",
        "notes_no_req": " No requirements section found — only bullets with technologies were used.",
        "why_needed": "Technology requested in requirements and not clearly detected in your CV.",
        "how_to_learn": "Add it to skills or a bullet if you have real experience.",
        "evidence": "Detected in CV text",
    },
}


def _ats_lang(job_description: str) -> str:
    return detect_language_hint(job_description) or "es"


def _msg(lang: str, key: str, **kwargs: str) -> str:
    bundle = ATS_MESSAGES.get(lang, ATS_MESSAGES["es"])
    template = bundle.get(key, ATS_MESSAGES["es"][key])
    return template.format(**kwargs)


def _build_improvements(
    *,
    score: int,
    missing: list[str],
    cv_text: str,
    matched_count: int,
    total: int,
    no_requirements_section: bool,
    lang: str = "es",
) -> list[str]:
    improvements: list[str] = []

    if no_requirements_section:
        improvements.append(_msg(lang, "no_req_section"))

    for keyword in missing[:8]:
        improvements.append(_msg(lang, "add_keyword", keyword=keyword))

    if total == 0:
        improvements.append(_msg(lang, "no_tech"))
    elif score < 70:
        improvements.append(_msg(lang, "low_score"))
    elif score < 85:
        improvements.append(_msg(lang, "near_pass"))

    if len(cv_text) < 800:
        improvements.append(_msg(lang, "expand_cv"))

    if matched_count > 0 and total > 0:
        improvements.append(
            _msg(lang, "matched_ratio", matched=str(matched_count), total=str(total))
        )

    return improvements[:10]


def analyze_ats_local(cv_text: str, job_description: str) -> dict:
    job_description = job_description.strip()
    cv_text = cv_text.strip()
    lang = _ats_lang(job_description)
    if not job_description:
        raise ValueError(_msg(lang, "job_required"))
    if not cv_text:
        raise ValueError(_msg(lang, "cv_required"))

    requirements_text = _extract_requirements_text(job_description)
    no_requirements_section = not requirements_text.strip()
    keywords = _extract_keywords(requirements_text, job_description)

    matched: list[str] = []
    missing: list[str] = []
    partial: list[str] = []

    for keyword in keywords:
        if _keyword_in_cv(keyword, cv_text):
            matched.append(keyword)
        else:
            tokens = [t for t in keyword.split() if len(t) > 2]
            if tokens and any(_keyword_in_cv(token, cv_text) for token in tokens):
                partial.append(keyword)
            else:
                missing.append(keyword)

    total = len(keywords)
    if total == 0:
        score = 0
        passes = False
    else:
        score = int(round((len(matched) + 0.5 * len(partial)) / total * 100))
        score = max(0, min(100, score))
        passes = score >= 75

    improvements = _build_improvements(
        score=score,
        missing=missing,
        cv_text=cv_text,
        matched_count=len(matched),
        total=total,
        no_requirements_section=no_requirements_section,
        lang=lang,
    )

    if total == 0:
        apply_rec = "apply_after_learning"
        apply_reason = _msg(lang, "no_tech_apply")
    elif passes:
        apply_rec = "apply_now"
        apply_reason = _msg(lang, "apply_now")
    elif score >= 55:
        apply_rec = "apply_after_learning"
        apply_reason = _msg(lang, "apply_moderate")
    else:
        apply_rec = "not_recommended"
        apply_reason = _msg(lang, "apply_low")

    notes = _msg(
        lang,
        "notes",
        matched=str(len(matched)),
        partial=str(len(partial)),
        missing=str(len(missing)),
    )
    if no_requirements_section:
        notes += _msg(lang, "notes_no_req")

    return {
        "score": score,
        "honest_score": score,
        "potential_score": min(100, score + 15) if total else 0,
        "passes_ats": passes,
        "adaptation_mode": "local",
        "analysis_type": "keyword",
        "target_role": _guess_role(job_description),
        "apply_recommendation": apply_rec,
        "apply_recommendation_reason": apply_reason,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "partial_keywords": partial,
        "total_keywords": total,
        "skills_you_have": [
            {"requirement": kw, "evidence": _msg(lang, "evidence"), "match_level": "covered"}
            for kw in matched[:12]
        ],
        "skills_to_learn": [
            {
                "skill": kw,
                "priority": "high" if index < 3 else "medium",
                "why_needed": _msg(lang, "why_needed"),
                "how_to_learn": _msg(lang, "how_to_learn"),
            }
            for index, kw in enumerate(missing[:6])
        ],
        "cv_improvements": improvements,
        "optimization_notes": notes,
    }
