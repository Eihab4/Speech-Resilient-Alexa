import { expect, test } from "vitest";

import { POSITION_MAX_AGE_MS, POSITION_TIMEOUT_MS } from "../src/config.js";
import { readPosition } from "../src/position.js";

function fakeGeolocation(answer) {
  const calls = [];
  return {
    calls,
    getCurrentPosition(onSuccess, onError, options) {
      calls.push(options);
      answer(onSuccess, onError);
    },
  };
}

test("the device's position comes back as latitude and longitude", async () => {
  const geolocation = fakeGeolocation((ok) => ok({ coords: { latitude: 30.04, longitude: 31.23, accuracy: 9 } }));

  expect(await readPosition(geolocation)).toEqual({ latitude: 30.04, longitude: 31.23 });
  expect(geolocation.calls).toEqual([{ timeout: POSITION_TIMEOUT_MS, maximumAge: POSITION_MAX_AGE_MS }]);
});

test("a refused or failed location gives null instead of an error", async () => {
  const geolocation = fakeGeolocation((_, fail) => fail({ code: 1 }));

  expect(await readPosition(geolocation)).toBeNull();
});

test("no location support gives null", async () => {
  expect(await readPosition(null)).toBeNull();
});
