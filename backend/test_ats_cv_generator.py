#!/usr/bin/env python3
"""Verify ATS CV generator output (PDF + TXT)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ats_cv_generator import generate_cv_pdf, generate_cv_txt

SAMPLE_CV = {
    "personal": {
        "name": "María García López",
        "title": "Senior Software Engineer",
        "email": "maria.garcia@email.com",
        "phone": "+34 600 123 456",
        "linkedin": "linkedin.com/in/mariagarcia",
        "github": "github.com/mariagarcia",
        "city": "Madrid, Spain",
    },
    "summary": (
        "Software engineer with 5+ years building scalable web applications and data "
        "pipelines. Expert in Python, FastAPI, and cloud-native architectures. Led teams "
        "delivering ATS-friendly products with measurable impact on hiring workflows."
    ),
    "experience": [
        {
            "company": "TechCorp España",
            "title": "Senior Software Engineer",
            "start_date": "03/2021",
            "end_date": "Present",
            "location": "Madrid, Spain",
            "bullets": [
                "Designed REST APIs serving 2M+ monthly requests using FastAPI and PostgreSQL.",
                "Reduced deployment time by 40% by implementing CI/CD pipelines on AWS.",
                "Mentored 3 junior developers on code quality and ATS-optimized documentation.",
            ],
        },
        {
            "company": "StartupXYZ",
            "title": "Full Stack Developer",
            "start_date": "06/2019",
            "end_date": "02/2021",
            "location": "Barcelona, Spain",
            "bullets": [
                "Built React dashboards integrated with Python backends for real-time analytics.",
                "Improved page load performance by 35% through query optimization and caching.",
            ],
        },
    ],
    "projects": [
        {
            "name": "CV Parser Engine",
            "github_url": "github.com/mariagarcia/cv-parser",
            "bullets": [
                "Open-source PDF/DOCX parser extracting structured JSON for ATS systems.",
                "Technologies: Python, pypdf, Pydantic. 500+ GitHub stars.",
            ],
        },
    ],
    "education": [
        {
            "degree": "B.S. Computer Science",
            "university": "Universidad Politécnica de Madrid",
            "start_date": "09/2015",
            "end_date": "06/2019",
        },
    ],
    "skills": {
        "languages": ["Python", "JavaScript", "SQL"],
        "frameworks": ["FastAPI", "React", "Django"],
        "tools": ["Git", "Docker", "PostgreSQL"],
        "cloud": ["AWS", "GCP"],
        "data_ai": ["Pandas", "scikit-learn", "Gemini API"],
    },
    "language": "en",
}


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "test_output"
    out_dir.mkdir(exist_ok=True)

    pdf_path = out_dir / "sample_ats_cv.pdf"
    txt_path = out_dir / "sample_ats_cv.txt"

    pdf_bytes = generate_cv_pdf(SAMPLE_CV)
    txt_content = generate_cv_txt(SAMPLE_CV)

    pdf_path.write_bytes(pdf_bytes)
    txt_path.write_text(txt_content, encoding="utf-8")

    print(f"PDF written: {pdf_path} ({len(pdf_bytes)} bytes)")
    print(f"TXT written: {txt_path} ({len(txt_content)} chars)")
    print("\n--- TXT preview (first 800 chars) ---")
    print(txt_content[:800])
    if not pdf_bytes.startswith(b"%PDF"):
        raise SystemExit("ERROR: output is not a valid PDF")
    print("\nOK: ATS CV generator test passed.")


if __name__ == "__main__":
    main()
