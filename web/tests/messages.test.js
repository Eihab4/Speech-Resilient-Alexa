import { expect, test } from "vitest";

import { voiceError } from "../src/messages.js";

test("a known voice error gets its own words", () => {
  expect(voiceError("audio-capture")).toBe("No microphone was found.");
});

test("an unknown voice error still shows its code", () => {
  expect(voiceError("weird")).toContain("weird");
});
