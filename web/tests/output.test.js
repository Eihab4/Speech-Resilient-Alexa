import { expect, test, vi } from "vitest";

import { createOutput } from "../src/output.js";
import { fakeVoice } from "./fakes.js";

function setup(...voices) {
  const changes = [];
  const output = createOutput(voices, { onSpeakingChange: (speaking) => changes.push(speaking) });
  return { output, changes };
}

test("speaking starts with the first reply and ends after the last one", async () => {
  const log = [];
  const voice = fakeVoice("browser", log);
  const { output, changes } = setup(voice);

  output.speak("What time?");
  output.speak("Should I set it?");
  expect(output.speaking).toBe(true);

  await vi.waitFor(() => expect(log).toEqual(["browser: What time?"]));
  voice.finish();
  await vi.waitFor(() => expect(log).toEqual(["browser: What time?", "browser: Should I set it?"]));
  expect(output.speaking).toBe(true);

  voice.finish();
  await vi.waitFor(() => expect(output.speaking).toBe(false));
  expect(changes).toEqual([true, false]);
});

test("the next voice takes over when the first cannot speak, and the first is tried again next time", async () => {
  const log = [];
  const browser = fakeVoice("browser", log);
  const { output } = setup(fakeVoice("polly", log, { fails: true }), browser);

  output.speak("Done.");
  await vi.waitFor(() => expect(log).toEqual(["polly: Done.", "browser: Done."]));

  browser.finish();
  output.speak("Mm-hm.");
  await vi.waitFor(() => expect(log).toEqual(["polly: Done.", "browser: Done.", "polly: Mm-hm.", "browser: Mm-hm."]));
});

test("muting stops the voice that is speaking, whichever one took over", async () => {
  const log = [];
  const browser = fakeVoice("browser", log);
  const { output } = setup(fakeVoice("polly", log, { fails: true }), browser);

  output.speak("Done.");
  await vi.waitFor(() => expect(log.at(-1)).toBe("browser: Done."));
  output.setMuted(true);

  await vi.waitFor(() => expect(output.speaking).toBe(false));
  expect(log.at(-1)).toBe("browser: stop");
});

test("when no voice can speak the page carries on", async () => {
  const log = [];
  const { output, changes } = setup(fakeVoice("polly", log, { fails: true }));

  output.speak("Done.");

  await vi.waitFor(() => expect(output.speaking).toBe(false));
  expect(changes).toEqual([true, false]);
});

test("a muted Alexa says nothing", () => {
  const log = [];
  const { output, changes } = setup(fakeVoice("browser", log));

  output.setMuted(true);
  output.speak("Done.");

  expect(log).toEqual([]);
  expect(changes).toEqual([]);
  expect(output.muted).toBe(true);
});

test("muting mid-reply stops it, drops what was queued and frees the microphone", async () => {
  const log = [];
  const voice = fakeVoice("browser", log);
  const { output, changes } = setup(voice);

  output.speak("Should I set a reminder?");
  output.speak("Anything else?");
  await vi.waitFor(() => expect(log).toEqual(["browser: Should I set a reminder?"]));
  output.setMuted(true);

  await vi.waitFor(() => expect(output.speaking).toBe(false));
  expect(log).toEqual(["browser: Should I set a reminder?", "browser: stop"]);
  expect(changes).toEqual([true, false]);
});

test("unmuting brings the voice back", async () => {
  const log = [];
  const { output } = setup(fakeVoice("browser", log));

  output.setMuted(true);
  output.setMuted(false);
  output.speak("Mm-hm.");

  await vi.waitFor(() => expect(log).toEqual(["browser: Mm-hm."]));
});

test("blank text is not spoken", () => {
  const log = [];
  const { output, changes } = setup(fakeVoice("browser", log));

  output.speak("");

  expect(log).toEqual([]);
  expect(changes).toEqual([]);
});
