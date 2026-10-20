import { expect, test } from "vitest";

import { asksForSos } from "../src/words.js";

test.each(["I fell", "uh… I… fell… floor", "Emergency!", "help help", "call an ambulance"])(
  "%s asks for help",
  (heard) => expect(asksForSos(heard)).toBe(true),
);

test.each(["help", "call mom", "the shelf fell", "tomorrow doctor ten"])("%s is an ordinary piece", (heard) =>
  expect(asksForSos(heard)).toBe(false),
);
