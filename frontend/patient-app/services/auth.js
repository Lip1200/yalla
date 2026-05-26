/**
 * Lightweight session helpers for the patient-app.
 *
 * Stores the auth session returned by /api/auth/login,
 * /api/auth/signup/patient or /api/auth/setup-password. Used today only
 * by the setup-account flow (issue #37); the broader login/refresh
 * wiring is tracked in #28.
 *
 * Uses expo-secure-store on native (Keychain iOS / EncryptedSharedPreferences
 * Android) with an in-memory fallback on web — sufficient for the demo
 * but should be replaced by a server-set cookie if the doctor-web ever
 * shares this file.
 */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

const SESSION_KEY = "yalla.patient.session";

// In-memory fallback for web (SecureStore is unsupported on web)
let webMemorySession = null;

async function read() {
  if (Platform.OS === "web") return webMemorySession;
  const raw = await SecureStore.getItemAsync(SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}

async function write(value) {
  if (Platform.OS === "web") {
    webMemorySession = value;
    return;
  }
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(value));
}

async function remove() {
  if (Platform.OS === "web") {
    webMemorySession = null;
    return;
  }
  await SecureStore.deleteItemAsync(SESSION_KEY);
}

export async function getSession() {
  try {
    return await read();
  } catch {
    return null;
  }
}

export async function saveSession(session) {
  try {
    await write(session);
  } catch {
    // swallow — losing the session locally is not fatal for the demo
  }
}

export async function clearSession() {
  try {
    await remove();
  } catch {
    // swallow
  }
}
