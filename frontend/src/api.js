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

/** True when production split-deploy (e.g. Vercel) has no backend URL baked in. */
export function getApiBaseForDisplay() {
  if (API_URL) return API_URL;
  if (import.meta.env.DEV) return "http://localhost:8000";
  if (typeof window !== "undefined") return `${window.location.origin} (sin VITE_API_URL — mal en Vercel)`;
  return "";
}

export function isSplitDeployMisconfigured() {
  if (import.meta.env.DEV) return false;
  if (API_URL) return false;
  const host = typeof window !== "undefined" ? window.location.hostname : "";
  return host.includes("vercel.app") || host.endsWith(".vercel.app");
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
