import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { createGatherer, DEFAULT_WAIT_SECONDS } from "../src/gather.js";

let sent;
let clock;
let gatherer;

beforeEach(() => {
  vi.useFakeTimers();
  sent = [];
  clock = 0;
  gatherer = createGatherer({ send: (words, pauses) => sent.push([words, pauses]), now: () => clock });
});

afterEach(() => {
  vi.useRealTimers();
});

function after(ms) {
  clock += ms;
  vi.advanceTimersByTime(ms);
}

test("one piece goes once the person's wait has passed, not before", () => {
  gatherer.piece("call mom");
  after(DEFAULT_WAIT_SECONDS * 1000 - 1);
  expect(sent).toEqual([]);

  after(1);
  expect(sent).toEqual([["call mom", []]]);
});

test("pieces said within the wait go together, with the pauses between them", () => {
  gatherer.setWait(3);
  gatherer.piece("call");
  after(2500);
  gatherer.speaking();
  after(800);
  gatherer.piece("mom");
  after(3000);

  expect(sent).toEqual([["call mom", [2500]]]);
});

test("talking again holds the answer even past the wait", () => {
  gatherer.piece("remind me");
  after(1900);
  gatherer.speaking();
  after(2500);
  expect(sent).toEqual([]);

  gatherer.piece("doctor tomorrow");
  after(2000);
  expect(sent).toEqual([["remind me doctor tomorrow", [1900]]]);
});

test("if a piece never finishes, the answer still comes", () => {
  gatherer.piece("call");
  after(500);
  gatherer.speaking();
  after(DEFAULT_WAIT_SECONDS * 2000);

  expect(sent).toEqual([["call", []]]);
});

test("an immediate piece goes at once, with what was waiting", () => {
  gatherer.piece("help");
  after(300);
  gatherer.piece("stop", { immediate: true });

  expect(sent).toEqual([["help stop", [300]]]);
});

test("the wait follows what the server learned, and ignores nonsense", () => {
  gatherer.setWait(4);
  gatherer.setWait(undefined);
  gatherer.piece("call mom");
  after(3999);
  expect(sent).toEqual([]);
  after(1);
  expect(sent).toHaveLength(1);
});
