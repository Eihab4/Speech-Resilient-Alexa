import { expect, test } from "vitest";

import { pauseWhileSpeaking } from "../src/pause.js";

function fakeListener(listening) {
  const calls = [];
  return {
    calls,
    listening,
    paused: 0,
    start() {
      this.listening = true;
      calls.push("start");
    },
    stop() {
      this.listening = false;
      calls.push("stop");
    },
  };
}

test("the mic stops while Alexa talks and starts again after", () => {
  const listener = fakeListener(true);
  const onSpeakingChange = pauseWhileSpeaking(
    () => listener,
    () => (listener.paused += 1),
  );

  onSpeakingChange(true);
  onSpeakingChange(false);

  expect(listener.calls).toEqual(["stop", "start"]);
  expect(listener.paused).toBe(1);
});

test("a mic that was off stays off", () => {
  const listener = fakeListener(false);
  const onSpeakingChange = pauseWhileSpeaking(
    () => listener,
    () => (listener.paused += 1),
  );

  onSpeakingChange(true);
  onSpeakingChange(false);

  expect(listener.calls).toEqual([]);
  expect(listener.paused).toBe(0);
});

test("a mic started by hand during the reply is not started twice", () => {
  const listener = fakeListener(true);
  const onSpeakingChange = pauseWhileSpeaking(
    () => listener,
    () => (listener.paused += 1),
  );

  onSpeakingChange(true);
  listener.start();
  onSpeakingChange(false);

  expect(listener.calls).toEqual(["stop", "start"]);
});

test("no listener means nothing to pause", () => {
  const onSpeakingChange = pauseWhileSpeaking(
    () => null,
    () => {},
  );

  expect(() => onSpeakingChange(true)).not.toThrow();
});
