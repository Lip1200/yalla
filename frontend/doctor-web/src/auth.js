const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";
const STORAGE_KEY = "yalla.doctor.session";

export { API_BASE_URL };

export function getSession() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setSession(session) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession() {
  window.localStorage.removeItem(STORAGE_KEY);
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Identifiants invalides.");
  }

  const session = await response.json();
  setSession(session);
  return session;
}

export async function signup(email, password, fullName) {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Inscription échouée.");
  }

  const result = await response.json();
  // 202-style response (email confirmation required) won't include a session.
  if (result?.access_token) {
    setSession(result);
  }
  return result;
}

export async function logout() {
  const session = getSession();
  if (session?.access_token) {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
    } catch {
      // Best-effort; clear locally regardless.
    }
  }
  clearSession();
}

async function refreshSession() {
  const session = getSession();
  if (!session?.refresh_token) throw new Error("Aucun refresh token.");

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });

  if (!response.ok) {
    clearSession();
    throw new Error("Session expirée.");
  }

  const newSession = await response.json();
  setSession(newSession);
  return newSession;
}

export async function authFetch(url, options = {}) {
  const session = getSession();
  if (!session?.access_token) {
    throw new Error("Vous devez vous connecter.");
  }

  const fire = (token) =>
    fetch(url, {
      ...options,
      headers: {
        ...(options.headers ?? {}),
        Authorization: `Bearer ${token}`,
      },
    });

  let response = await fire(session.access_token);
  if (response.status === 401) {
    try {
      const refreshed = await refreshSession();
      response = await fire(refreshed.access_token);
    } catch (error) {
      clearSession();
      throw new Error("Session expirée — veuillez vous reconnecter.");
    }
  }
  return response;
}
