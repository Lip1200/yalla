/**
 * Thin wrapper around expo-location.
 *
 * Used today by RestaurantsScreen for auto-positioning (the backend
 * /api/restaurants/recommendations expects lat + lon). Could later be
 * used for outdoor walking challenges (distance tracking).
 */
import * as Location from "expo-location";

/** Geneva centre — sensible fallback when permission denied or GPS off. */
export const FALLBACK_GENEVA = { latitude: 46.2044, longitude: 6.1432 };

export async function requestLocationPermission() {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === "granted";
}

export async function getLocationPermission() {
  const { status } = await Location.getForegroundPermissionsAsync();
  return status === "granted";
}

/**
 * Returns the current device coordinates or a Geneva-centre fallback if
 * the user denied permission or the lookup timed out. Never throws — the
 * caller can always render restaurants nearby a reasonable default.
 *
 * @returns {Promise<{latitude: number, longitude: number, accuracy: number | null, fromFallback: boolean}>}
 */
export async function getCurrentCoords() {
  try {
    const granted = await getLocationPermission();
    if (!granted) {
      const ok = await requestLocationPermission();
      if (!ok) {
        return { ...FALLBACK_GENEVA, accuracy: null, fromFallback: true };
      }
    }
    const position = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    return {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy,
      fromFallback: false,
    };
  } catch {
    return { ...FALLBACK_GENEVA, accuracy: null, fromFallback: true };
  }
}
