/**
 * API base URL:
 * - Dev: localhost:8000
 * - Vercel: set VITE_API_URL to Railway API URL at build time (e.g. https://api.alvarorodriguez.dev)
 */
function resolveApiUrl() {
  let fromEnv = (import.meta.env.VITE_API_URL || "").trim().replace(/\/$/, "");
  if (fromEnv) {
    // Browsers reject schemes like "Https://" — normalize
    fromEnv = fromEnv.replace(/^https?:\/\//i, (m) => m.toLowerCase());
    return fromEnv;
  }
  if (import.meta.env.DEV) return "http://localhost:8000";
  return "";
}

export const API_URL = resolveApiUrl();

export function isApiConfigured() {
  return Boolean(API_URL);
}

/** True when production split-deploy (e.g. Vercel) has no backend URL baked in. */
export function getApiBaseForDisplay() {
  if (API_URL) return API_URL;
  if (import.meta.env.DEV) return "http://localhost:8000";
  if (typeof window !== "undefined") return `${window.location.origin} (sin VITE_API_URL — mal en Vercel)`;
  return "";
}

export function isSplitDeployMisconfigured() {
  if (import.meta.env.DEV) return false;
  return !API_URL;
}

/** Normalize FastAPI error payloads for display. */
export function formatApiError(detail, fallback = "Request failed") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === "object" && item?.msg ? item.msg : String(item)))
      .join("; ");
  }
  return fallback;
}

/** True only when the response looks like our FastAPI /health JSON (not SPA index.html). */
export async function verifyBackendHealth(response) {
  const type = response.headers.get("content-type") || "";
  if (!type.includes("application/json")) return false;
  try {
    const data = await response.json();
    return data?.status === "ok";
  } catch {
    return false;
  }
}

const RETRYABLE_STATUS = new Set([502, 503, 504]);

/** Wake Render (GET /health with retries). Call before heavy POSTs. */
export async function wakeBackend({ attempts = 10, delayMs = 5000 } = {}) {
  if (!isApiConfigured()) return false;
  const res = await fetchWithRetry(
    `${API_URL}/health`,
    { method: "GET" },
    { attempts, delayMs },
  );
  if (!res.ok) return false;
  return verifyBackendHealth(res);
}

/** Retry fetch while Render free tier wakes up (cold start). GET only — avoid hammering POST. */
export async function fetchWithRetry(url, options = {}, { attempts = 6, delayMs = 5000 } = {}) {
  const method = (options.method || "GET").toUpperCase();
  const maxAttempts = method === "GET" || method === "HEAD" ? attempts : 1;
  let lastError;
  for (let i = 0; i < maxAttempts; i += 1) {
    try {
      const response = await fetch(url, options);
      if (response.ok || !RETRYABLE_STATUS.has(response.status) || i === maxAttempts - 1) {
        return response;
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (err) {
      lastError = err;
      if (i === maxAttempts - 1) throw err;
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw lastError ?? new Error("Request failed");
}
