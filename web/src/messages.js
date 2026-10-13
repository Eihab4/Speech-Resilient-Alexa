import { Speaker } from "./enums.js";

export const SpeakerName = Object.freeze({
  [Speaker.USER]: "You",
  [Speaker.ALEXA]: "Alexa",
});

export const Note = Object.freeze({
  ERROR: "Error",
  nextMove: (move) => `Next: ${move}`,
});

export const ErrorMessage = Object.freeze({
  unreachable: (url) => `Could not reach the MCP server at ${url}.`,
  toolFailed: (name) => `${name} failed.`,
});
