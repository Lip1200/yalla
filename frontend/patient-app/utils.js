/**
 * Pure helpers shared across App.js + extracted screens. No JSX, no
 * react-native imports — just data transforms and API plumbing.
 */

import { getActiveAccessToken } from "./services/api";

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://192.168.1.18:8001";

const SERVICE_TOKEN_FALLBACK = "yalla-secret-token";

export function currentAuthToken() {
  return getActiveAccessToken() ?? SERVICE_TOKEN_FALLBACK;
}

export function formatDate(value) {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" }).format(
    new Date(value),
  );
}

export function buildThreads(conversations) {
  return conversations.reduce((threads, conversation) => {
    threads[conversation.id] = [
      {
        id: `${conversation.id}-a`,
        fromMe: false,
        text: conversation.last_message,
        time: formatDate(conversation.updated_at),
      },
      {
        id: `${conversation.id}-b`,
        fromMe: true,
        text: "Merci, je regarde ca aujourd'hui.",
        time: "Vu",
      },
    ];
    return threads;
  }, {});
}

export function mergeRestaurants(restaurants) {
  const seen = new Set();
  return restaurants.filter((restaurant) => {
    const key = String(
      restaurant.thefork_restaurant_id ?? restaurant.id ?? restaurant.name,
    ).toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${currentAuthToken()}` },
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    console.warn(`[apiGet local] ${path} -> ${response.status}  ${body.slice(0, 160)}`);
    throw new Error(`Impossible de charger les données (${response.status}).`);
  }
  return response.json();
}

export async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${currentAuthToken()}`,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Action impossible.");
  }
  return response.json();
}

export async function apiPatch(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${currentAuthToken()}`,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Action impossible.");
  }
  return response.json();
}
