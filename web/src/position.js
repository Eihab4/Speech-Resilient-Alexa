import { POSITION_MAX_AGE_MS, POSITION_TIMEOUT_MS } from "./config.js";

// The device's position, or null when the browser can't or won't give it. Never rejects:
// an emergency alert goes out with or without a location.
export function readPosition(geolocation = globalThis.navigator?.geolocation) {
  if (!geolocation) return Promise.resolve(null);
  return new Promise((resolve) =>
    geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude }),
      () => resolve(null),
      { timeout: POSITION_TIMEOUT_MS, maximumAge: POSITION_MAX_AGE_MS },
    ),
  );
}
