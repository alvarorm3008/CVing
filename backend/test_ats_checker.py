from ats_checker import _extract_keywords, _extract_requirements_text, analyze_ats_local


def test_ignores_intro_boilerplate():
    job = """
    Oferta del empleo — Empresa XYZ

    Sobre la empresa
    Somos líderes en tecnología y buscamos talento.

    Requisitos
    - 3+ años de experiencia con Python
    - Conocimientos de React y PostgreSQL
    - Docker y Git

    Responsabilidades
    - Desarrollar APIs
    """
    req = _extract_requirements_text(job)
    assert "Python" in req
    assert "oferta del empleo".lower() not in req.lower()

    keywords = _extract_keywords(req, job)
    assert "python" in keywords
    assert "react" in keywords
    assert "postgresql" in keywords or "postgres" in keywords
    assert not any("oferta" in k for k in keywords)


def test_cv_match_only_technologies():
    job = """
    Qué buscamos
    • TypeScript, Node.js
    • Experiencia con AWS
    """
    cv = "Desarrollador con TypeScript, Node.js y AWS en producción."
    result = analyze_ats_local(cv, job)
    assert result["total_keywords"] >= 2
    assert result["honest_score"] >= 70
    assert not any("oferta" in imp.lower() for imp in result["cv_improvements"])
