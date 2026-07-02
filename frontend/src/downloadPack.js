import JSZip from "jszip";
import { API_URL } from "./api.js";
import { coverLetterDisplayText } from "./coverLetterUtils.js";

async function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function fetchPdfBase64(cv, templateId, filename) {
  const response = await fetch(`${API_URL}/render-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv, template_id: templateId, filename }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "PDF generation failed");
  }
  const blob = await response.blob();
  return blobToBase64(blob);
}

async function fetchAtsTxt(cv) {
  const response = await fetch(`${API_URL}/render-txt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "TXT generation failed");
  }
  return response.text();
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function downloadApplicationPack({
  cv,
  pdfData,
  coverLetter,
  templateId = "modern-pro",
  atsTemplateId = "ats-plain",
  baseFilename = "cv-adaptado",
}) {
  const zip = new JSZip();
  const baseName = baseFilename.replace(/\.pdf$/i, "");

  let mainPdfB64 = pdfData?.base64;
  if (!mainPdfB64) {
    mainPdfB64 = await fetchPdfBase64(cv, templateId, `${baseName}.pdf`);
  }
  zip.file(`${baseName}.pdf`, mainPdfB64, { base64: true });

  const atsPdfB64 = await fetchPdfBase64(cv, atsTemplateId, `${baseName}-ats.pdf`);
  zip.file(`${baseName}-ats.pdf`, atsPdfB64, { base64: true });

  const atsTxt = await fetchAtsTxt(cv);
  zip.file(`${baseName}-ats.txt`, atsTxt);

  if (coverLetter) {
    const letterText = coverLetterDisplayText(coverLetter);
    if (letterText) {
      zip.file("carta-presentacion.txt", letterText);
    }
  }

  const content = await zip.generateAsync({ type: "blob" });
  triggerDownload(content, `${baseName}-pack.zip`);
}
