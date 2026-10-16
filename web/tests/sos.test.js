import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { NextMove } from "../src/enums.js";
import { createSos } from "../src/sos.js";

const SOS = { next_move: NextMove.SOS, countdown_seconds: 3 };
const HERE = { latitude: 30.0444, longitude: 31.2357 };

let ticks;
let due;
let sos;

beforeEach(() => {
  vi.useFakeTimers();
  ticks = [];
  due = 0;
  sos = createSos({
    readPosition: () => Promise.resolve(HERE),
    onTick: (seconds) => ticks.push(seconds),
    onDue: () => (due += 1),
  });
});

afterEach(() => {
  vi.useRealTimers();
});

test("silence sends the alert when the countdown ends", async () => {
  sos.follow(SOS);
  sos.begin();
  vi.advanceTimersByTime(3000);

  expect(ticks).toEqual([3, 2, 1, 0]);
  expect(due).toBe(1);
  expect(await sos.take()).toEqual(HERE);
  expect(sos.take()).toBeNull();
});

test("the countdown waits for Alexa to finish talking", () => {
  sos.follow(SOS);
  vi.advanceTimersByTime(10000);

  expect(ticks).toEqual([]);
  expect(due).toBe(0);
});

test("a reply other than sos, like the answer to stop, clears the countdown", () => {
  sos.follow(SOS);
  sos.begin();
  vi.advanceTimersByTime(1000);

  sos.follow({ next_move: NextMove.LISTEN });
  vi.advanceTimersByTime(5000);

  expect(ticks).toEqual([3, 2, 0]);
  expect(due).toBe(0);
  expect(sos.take()).toBeNull();
});

test("more sos replies during the countdown don't restart it", () => {
  sos.follow(SOS);
  sos.begin();
  vi.advanceTimersByTime(2000);

  sos.follow(SOS);
  sos.begin();
  vi.advanceTimersByTime(1000);

  expect(ticks).toEqual([3, 2, 1, 0]);
  expect(due).toBe(1);
});

test("a stop answered after the end but before the alert left still cancels it", () => {
  sos.follow(SOS);
  sos.begin();
  vi.advanceTimersByTime(3000);

  sos.follow({ next_move: NextMove.LISTEN });

  expect(due).toBe(1);
  expect(sos.take()).toBeNull();
});

test("the location is asked for once, when the server says sos", () => {
  const readPosition = vi.fn(() => Promise.resolve(HERE));
  const counted = createSos({ readPosition, onTick: () => {}, onDue: () => {} });

  counted.follow(SOS);
  counted.follow(SOS);
  counted.begin();

  expect(readPosition).toHaveBeenCalledTimes(1);
});
