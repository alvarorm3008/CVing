export function coverLetterDisplayText(coverLetter) {
  if (!coverLetter) return "";
  if (coverLetter.full_text?.trim()) return coverLetter.full_text.trim();

  const parts = [];
  if (coverLetter.greeting?.trim()) parts.push(coverLetter.greeting.trim());
  if (Array.isArray(coverLetter.paragraphs)) {
    coverLetter.paragraphs.forEach((p) => {
      if (p?.trim()) parts.push(p.trim());
    });
  }
  if (coverLetter.closing?.trim()) parts.push(coverLetter.closing.trim());
  return parts.join("\n\n");
}
