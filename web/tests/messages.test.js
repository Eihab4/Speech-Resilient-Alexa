import { expect, test } from "vitest";

import { invitation, voiceError } from "../src/messages.js";

test("a known voice error gets its own words", () => {
  expect(voiceError("audio-capture")).toBe("No microphone was found.");
});

test("an unknown voice error still shows its code", () => {
  expect(voiceError("weird")).toContain("weird");
});

test("the invitation tells the helper who added them and what to do", () => {
  const text = invitation("Sara", "Rana", "https://t.me/rana_sra_alerts_bot?start=abc");

  expect(text).toContain("Hi Sara! Rana added you as an emergency contact");
  expect(text).toContain("1. Open this link on your phone (install Telegram first if you don't have it): https://t.me/rana_sra_alerts_bot?start=abc");
  expect(text).toContain("2. Press Start.");
});
