/**
 * Minimal API wrapper for the patient-app. Mirrors the apiGet/apiPost
 * helpers currently inline in App.js so the new pedometer + GPS code
 * can import from a stable module path.
 *
 * Once the real Supabase Auth flow lands (issue #28), replace the
 * hardcoded service token with the stored session.access_token. The
 * service-token fallback is preserved server-side (cf. issue #2) so
 * it keeps working for the demo.
 */

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.18:8001";

const SERVICE_TOKEN = "yalla-secret-token";

function authHeaders(extra = {}) {
  return {
    Authorization: `Bearer ${SERVICE_TOKEN}`,
    ...extra,
  };
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Impossible de charger les données.");
  }
  return response.json();
}

export async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Action impossible.");
  }
  return response.json();
}

export { API_BASE_URL };
