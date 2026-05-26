/**
 * Thin wrapper around expo-sensors's Pedometer.
 *
 * Available out-of-the-box in Expo Go (no Dev Build required) — that's
 * the whole point of issue #43 vs the heavier HealthKit/Health Connect
 * path tracked in #23 + #34.
 *
 * iOS reads from CMPedometer (Apple's pedometer API, available on every
 * iPhone 5s+). Android reads from the standard step counter sensor.
 *
 * Historical reads (`getStepsSince`) work great on iOS. On Android the
 * step counter resets at each reboot, so historical accuracy beyond
 * "since last reboot" is limited — Health Connect (Phase 2) is the
 * correct answer for full Android history.
 */
import { Pedometer } from "expo-sensors";

export async function isPedometerAvailable() {
  try {
    return await Pedometer.isAvailableAsync();
  } catch {
    return false;
  }
}

export async function requestPedometerPermission() {
  const { status } = await Pedometer.requestPermissionsAsync();
  return status === "granted";
}

export async function getPedometerPermission() {
  const { status } = await Pedometer.getPermissionsAsync();
  return status === "granted";
}

/**
 * Subscribe to live step counts. The callback fires every time the OS
 * publishes a new step. Returns the subscription handle — call
 * `subscription.remove()` on cleanup (typically inside a React useEffect
 * return).
 *
 * @param {(steps: number) => void} onSteps
 */
export function subscribeSteps(onSteps) {
  return Pedometer.watchStepCount((result) => {
    onSteps(result?.steps ?? 0);
  });
}

/**
 * Read the cumulative step count between two dates. iOS supports
 * arbitrary history (CMPedometer keeps ~7 days). Android only counts
 * since last boot — for longer ranges the call resolves with 0 or
 * rejects. Caller should handle both gracefully.
 *
 * @param {Date} start
 * @param {Date} end
 */
export async function getStepsBetween(start, end) {
  try {
    const result = await Pedometer.getStepCountAsync(start, end);
    return result?.steps ?? 0;
  } catch {
    return 0;
  }
}

/**
 * Convenience: total steps since midnight today.
 */
export async function getStepsToday() {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setHours(0, 0, 0, 0);
  return getStepsBetween(midnight, now);
}
