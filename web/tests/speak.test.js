import { beforeEach, expect, test } from "vitest";

import { installFakeSpeechSynthesis } from "./fakes.js";

let spoken;
let voice;

beforeEach(async () => {
  spoken = installFakeSpeechSynthesis();
  const { createBrowserVoice } = await import("../src/speak.js");
  voice = createBrowserVoice();
});

test("a reply ends once the browser finished saying it", async () => {
  const done = voice.speak("Mm-hm, go on.");
  speechSynthesis.finish();

  await expect(done).resolves.toBeUndefined();
});

test("the utterance carries the text and language", () => {
  voice.speak("Mm-hm, go on.");

  expect(spoken.map((utterance) => utterance.text)).toEqual(["Mm-hm, go on."]);
  expect(spoken[0].lang).toBe("en-US");
});

test("stopping ends the reply without an error", async () => {
  const done = voice.speak("Should I set it?");
  voice.stop();

  await expect(done).resolves.toBeUndefined();
});

test("a voice that cannot speak reports it", async () => {
  const done = voice.speak("Done.");
  speechSynthesis.fail();

  await expect(done).rejects.toThrow("synthesis-failed");
});
