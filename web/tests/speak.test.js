import { beforeEach, expect, test } from "vitest";

import { installFakeSpeechSynthesis } from "./fakes.js";

let spoken;
let changes;
let speaker;

beforeEach(async () => {
  spoken = installFakeSpeechSynthesis();
  changes = [];
  const { createSpeaker } = await import("../src/speak.js");
  speaker = createSpeaker({ onSpeakingChange: (speaking) => changes.push(speaking) });
});

test("a reply is read aloud in the configured language", () => {
  speaker.speak("Mm-hm, go on.");

  expect(spoken.map((utterance) => utterance.text)).toEqual(["Mm-hm, go on."]);
  expect(spoken[0].lang).toBe("en-US");
});

test("speaking starts with the first reply and ends after the last one", () => {
  speaker.speak("What time?");
  speaker.speak("Should I set it?");
  expect(speaker.speaking).toBe(true);

  speechSynthesis.finish();
  expect(speaker.speaking).toBe(true);

  speechSynthesis.finish();
  expect(speaker.speaking).toBe(false);
  expect(changes).toEqual([true, false]);
});

test("an interrupted reply still counts as finished", () => {
  speaker.speak("Done.");
  speechSynthesis.cancel();

  expect(speaker.speaking).toBe(false);
  expect(changes).toEqual([true, false]);
});

test("blank text is not spoken", () => {
  speaker.speak("");

  expect(spoken).toEqual([]);
  expect(changes).toEqual([]);
});
