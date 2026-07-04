/**
 * API base URL:
 * - Dev: localhost:8000
 * - Vercel (or split deploy): set VITE_API_URL to your Render/backend URL at build time
 * - Render Docker (SERVE_FRONTEND=1): leave unset → same-origin
 */
function resolveApiUrl() {
  const fromEnv = (import.meta.env.VITE_API_URL || "").trim().replace(/\/$/, "");
  if (fromEnv) return fromEnv;
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

/** Retry fetch while Render free tier wakes up (cold start). */
export async function fetchWithRetry(url, options = {}, { attempts = 6, delayMs = 5000 } = {}) {
  let lastError;
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(url, options);
      if (response.ok || !RETRYABLE_STATUS.has(response.status) || i === attempts - 1) {
        return response;
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (err) {
      lastError = err;
      if (i === attempts - 1) throw err;
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw lastError ?? new Error("Request failed");
}
