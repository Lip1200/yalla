/**
 * Network layer for the patient-app.
 *
 * Carries a module-level "active access token" that is set after
 * login/signup (via `auth.js`) and cleared on logout. All requests
 * automatically pick it up; if none is set, falls back to the static
 * service token preserved server-side (cf. issue #2) so demos and CI
 * scripts keep working.
 *
 * `apiGet`/`apiPost` automatically attempt one refresh-token roundtrip
 * on a 401 — if it succeeds the original request is retried, if it
 * fails the session is cleared and the error bubbles up to the caller
 * (the App-level bootstrap then redirects to the login screen).
 */

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.18:8001";

const SERVICE_TOKEN = "yalla-secret-token";

let _activeAccessToken = null;

// auth.js calls these — not for consumer use.
export function setActiveAccessToken(token) {
  _activeAccessToken = token || null;
}
export function clearActiveAccessToken() {
  _activeAccessToken = null;
}
export function getActiveAccessToken() {
  return _activeAccessToken;
}

// `_onUnauthorized` is set by App.js to a function that attempts a
// refresh-token roundtrip and returns the new access_token (or null
// if refresh failed). Keeps the api.js module decoupled from
// auth.js's specifics.
let _onUnauthorized = null;
export function setUnauthorizedHandler(fn) {
  _onUnauthorized = fn;
}

function authHeaders(token, extra = {}) {
  return {
    Authorization: `Bearer ${token ?? _activeAccessToken ?? SERVICE_TOKEN}`,
    ...extra,
  };
}

async function fetchWithRetry(url, init) {
  const token = _activeAccessToken ?? SERVICE_TOKEN;
  let response = await fetch(url, {
    ...init,
    headers: { ...authHeaders(token), ...(init?.headers ?? {}) },
  });

  // On 401, try one refresh round-trip if a handler is installed.
  if (response.status === 401 && _onUnauthorized && _activeAccessToken) {
    const newToken = await _onUnauthorized();
    if (newToken) {
      response = await fetch(url, {
        ...init,
        headers: { ...authHeaders(newToken), ...(init?.headers ?? {}) },
      });
    }
  }

  return response;
}

export async function apiGet(path) {
  const response = await fetchWithRetry(`${API_BASE_URL}${path}`, {});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Impossible de charger les données.");
  }
  return response.json();
}

export async function apiPost(path, payload) {
  const response = await fetchWithRetry(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Action impossible.");
  }
  return response.json();
}

export { API_BASE_URL };
