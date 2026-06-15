from cv_schema import LearningRecommendation, SkillMatch, StructuredCV


def build_ats_match_info(adapted, mode: str = "honest") -> dict:
    """Build ATS match payload from AI adaptation result."""
    matched_display = [
        item.requirement for item in adapted.skills_you_have if item.match_level == "covered"
    ]
    partial_display = [
        item.requirement for item in adapted.skills_you_have if item.match_level == "partial"
    ]

    display_score = adapted.honest_ats_score
    missing = adapted.must_have_missing or []

    return {
        "score": display_score,
        "honest_score": adapted.honest_ats_score,
        "potential_score": adapted.potential_ats_score,
        "adaptation_mode": mode,
        "target_role": adapted.target_role,
        "apply_recommendation": adapted.apply_recommendation,
        "apply_recommendation_reason": adapted.apply_recommendation_reason,
        "matched_keywords": adapted.must_have_matched or matched_display,
        "missing_keywords": missing,
        "partial_keywords": partial_display,
        "total_keywords": len(adapted.must_have_matched) + len(missing),
        "skills_you_have": [item.model_dump() for item in adapted.skills_you_have],
        "skills_to_learn": [item.model_dump() for item in adapted.skills_to_learn],
        "cv_improvements": list(getattr(adapted, "cv_improvements", None) or []),
        "optimization_notes": adapted.optimization_notes,
    }
