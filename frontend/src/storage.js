const CV_BASE_KEY = "cvAdapter_cvBase";
const HISTORY_KEY = "cvAdapter_history";
const MAX_HISTORY = 30;

export function loadCvBase() {
  try {
    const raw = localStorage.getItem(CV_BASE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveCvBase({ cv, filename }) {
  const payload = {
    cv,
    filename,
    savedAt: new Date().toISOString(),
  };
  localStorage.setItem(CV_BASE_KEY, JSON.stringify(payload));
  return payload;
}

export function clearCvBase() {
  localStorage.removeItem(CV_BASE_KEY);
}

export function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addHistoryEntry(entry) {
  const history = loadHistory();
  const record = {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    status: "prepared",
    ...entry,
  };
  const next = [record, ...history].slice(0, MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  return next;
}

export function updateHistoryEntry(id, patch) {
  const next = loadHistory().map((item) =>
    item.id === id ? { ...item, ...patch } : item,
  );
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  return next;
}

export const HISTORY_STATUSES = ["prepared", "sent", "interview", "rejected"];

export function deleteHistoryEntry(id) {
  const next = loadHistory().filter((item) => item.id !== id);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  return next;
}

export function clearHistory() {
  localStorage.removeItem(HISTORY_KEY);
}

export const DATE_LOCALE_MAP = {
  es: "es-ES",
  en: "en-US",
  fr: "fr-FR",
  de: "de-DE",
  pt: "pt-PT",
  it: "it-IT",
  ca: "ca-ES",
};

export function formatDate(iso, locale = "es-ES") {
  return new Date(iso).toLocaleString(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function jobPreview(text, max = 120) {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned.length <= max) return cleaned;
  return `${cleaned.slice(0, max)}…`;
}
