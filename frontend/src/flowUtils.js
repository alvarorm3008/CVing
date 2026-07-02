/** Determines recommended action id and flow step (1–3). */
export function getRecommendedAction({
  preflight,
  atsMatch,
  lastAction,
  cvData,
  coverLetter,
  hasCvSource,
  jobDescription,
}) {
  if (!jobDescription?.trim() || !hasCvSource) {
    return { recommendedId: "check-ats", step: 1 };
  }

  const score = preflight?.honest_score ?? atsMatch?.honest_score ?? atsMatch?.score ?? null;
  const isLocal = preflight?.adaptation_mode === "local" || atsMatch?.adaptation_mode === "local";
  const hasPreflight = preflight && preflight.total_keywords > 0;

  if (cvData && !coverLetter && lastAction !== "check-ats" && lastAction !== "improve") {
    return { recommendedId: "full", step: 3 };
  }

  if (cvData && (lastAction === "adapt" || lastAction === "honest" || lastAction === "full")) {
    return { recommendedId: "full", step: 3 };
  }

  if (hasPreflight || isLocal) {
    if (score !== null && score < 75) {
      return { recommendedId: "adapt", step: 2 };
    }
    if (score !== null && score >= 75 && lastAction === "improve") {
      return { recommendedId: "improve", step: 1 };
    }
    if (score !== null && score >= 75) {
      return { recommendedId: "adapt", step: 2 };
    }
  }

  if (!preflight && !atsMatch) {
    return { recommendedId: "check-ats", step: 1 };
  }

  return { recommendedId: "check-ats", step: 1 };
}

export function getFlowStep(lastAction, cvData, coverLetter) {
  if (cvData && (coverLetter || lastAction === "adapt" || lastAction === "full" || lastAction === "honest")) {
    return 3;
  }
  if (lastAction === "adapt" || lastAction === "honest" || lastAction === "full") {
    return 3;
  }
  if (lastAction === "check-ats" || lastAction === "improve") {
    return 2;
  }
  return 1;
}
