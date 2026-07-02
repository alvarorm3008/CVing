function cvTextBlob(cv) {
  if (!cv) return "";
  const parts = [
    cv.summary,
    ...(cv.skills || []),
    ...(cv.experience || []).flatMap((e) => [e.role, e.company, ...(e.bullets || [])]),
  ];
  return parts.filter(Boolean).join(" ").toLowerCase();
}

export function computeChanges(originalCv, adaptedCv, atsMatch) {
  if (!originalCv || !adaptedCv) {
    return { addedKeywords: [], newSkills: [], bulletChanges: [], missingKeywords: [] };
  }

  const origText = cvTextBlob(originalCv);
  const matched = atsMatch?.matched_keywords || [];

  const addedKeywords = matched.filter((kw) => {
    const lower = kw.toLowerCase();
    return !origText.includes(lower);
  });

  const origSkills = new Set((originalCv.skills || []).map((s) => s.trim().toLowerCase()));
  const newSkills = (adaptedCv.skills || []).filter(
    (s) => s.trim() && !origSkills.has(s.trim().toLowerCase()),
  );

  const bulletChanges = [];
  const origExp = originalCv.experience || [];
  const adaptExp = adaptedCv.experience || [];

  adaptExp.forEach((item, idx) => {
    const orig = origExp[idx];
    if (!orig) return;
    const origBullets = orig.bullets || [];
    const newBullets = item.bullets || [];
    newBullets.forEach((bullet, bIdx) => {
      const before = origBullets[bIdx];
      if (before && before.trim() !== bullet.trim()) {
        bulletChanges.push({
          role: item.role,
          company: item.company,
          before: before.trim(),
          after: bullet.trim(),
        });
      }
    });
  });

  const missingKeywords = atsMatch?.missing_keywords || [];

  return { addedKeywords, newSkills, bulletChanges, missingKeywords };
}
