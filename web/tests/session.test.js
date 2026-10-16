import { expect, test } from "vitest";

import { forgetSession, loadSession, saveSession } from "../src/session.js";

function fakeStorage() {
  const items = new Map();
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => items.set(key, String(value)),
    removeItem: (key) => items.delete(key),
  };
}

const blocked = () => {
  throw new Error("blocked");
};
const brokenStorage = { getItem: blocked, setItem: blocked, removeItem: blocked };

const SESSION = { token: "t1", username: "rana_h", name: "Rana" };

test("the browser keeps the person signed in until they sign out", () => {
  const storage = fakeStorage();

  saveSession(SESSION, storage);

  expect(loadSession(storage)).toEqual(SESSION);
  forgetSession(storage);
  expect(loadSession(storage)).toBeNull();
});

test("blocked storage means signing in again, not an error", () => {
  expect(saveSession(SESSION, brokenStorage)).toEqual(SESSION);
  expect(loadSession(brokenStorage)).toBeNull();
  expect(() => forgetSession(brokenStorage)).not.toThrow();
});

test("anything else kept under the key is ignored", () => {
  const storage = fakeStorage();
  storage.setItem("speech-resilient-alexa.session", JSON.stringify({ name: "no token" }));

  expect(loadSession(storage)).toBeNull();
});
