/**
 * Session storage + auth-endpoint wrappers for the patient-app.
 *
 * Uses expo-secure-store on native (Keychain iOS / EncryptedSharedPreferences
 * Android), in-memory fallback on web (lost on refresh, fine for dev).
 *
 * Side effect: every function that produces a session ALSO updates the
 * module-level access-token cache in `./api.js` so all subsequent
 * apiGet/apiPost calls automatically use it. logout clears both.
 */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

import {
  API_BASE_URL,
  clearActiveAccessToken,
  setActiveAccessToken,
} from "./api";

const SESSION_KEY = "yalla.patient.session";

let webMemorySession = null;

async function readStored() {
  if (Platform.OS === "web") return webMemorySession;
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}

async function writeStored(value) {
  if (Platform.OS === "web") {
    webMemorySession = value;
    return;
  }
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(value));
}

async function removeStored() {
  if (Platform.OS === "web") {
    webMemorySession = null;
    return;
  }
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

export async function getSession() {
  try {
    return await readStored();
  } catch {
    return null;
  }
}

export async function saveSession(session) {
  try {
    await writeStored(session);
    if (session?.access_token) {
      setActiveAccessToken(session.access_token);
    }
  } catch {
    // swallow — losing the session locally is not fatal for the demo
  }
}

export async function clearSession() {
  try {
    await removeStored();
  } catch {
    // swallow
  }
  clearActiveAccessToken();
}

/**
 * Called at app boot. Reads any persisted session and primes the api.js
 * access-token cache. Returns the session (or null) so the caller can
 * decide whether to render the auth flow vs the main shell.
 */
export async function bootstrapSession() {
  const session = await getSession();
  if (session?.access_token) {
    setActiveAccessToken(session.access_token);
  }
  return session;
}

// ===========================================================================
// HTTP helpers for the auth endpoints
// ===========================================================================

async function postJson(path, payload, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(body.detail ?? "Action impossible.");
    err.status = response.status;
    err.body = body;
    throw err;
  }
  return body;
}

export async function loginPatient(email, password) {
  const session = await postJson("/api/auth/login", { email, password });
  await saveSession(session);
  return session;
}

export async function signupPatient(email, password, fullName) {
  const result = await postJson("/api/auth/signup/patient", {
    email,
    password,
    full_name: fullName,
  });
  if (result?.access_token) {
    await saveSession(result);
  }
  return result;
}

export async function refreshSession() {
  const current = await getSession();
  if (!current?.refresh_token) {
    await clearSession();
    return null;
  }
  try {
    const refreshed = await postJson("/api/auth/refresh", {
      refresh_token: current.refresh_token,
    });
    await saveSession(refreshed);
    return refreshed;
  } catch {
    await clearSession();
    return null;
  }
}

export async function logoutPatient() {
  const current = await getSession();
  if (current?.access_token) {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${current.access_token}` },
      });
    } catch {
      // best-effort
    }
  }
  await clearSession();
}
