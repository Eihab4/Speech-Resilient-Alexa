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

export const MicLabel = Object.freeze({
  START: "Speak",
  STOP: "Stop listening",
});

export const VoiceHint = Object.freeze({
  LISTENING: "Listening… pause between pieces, each pause is sent on its own.",
  UNSUPPORTED: "Voice needs Chrome or Edge. You can still type.",
});

const VOICE_ERRORS = Object.freeze({
  "not-allowed": "Microphone access was blocked. Allow it in the browser to talk.",
  "service-not-allowed": "Microphone access was blocked. Allow it in the browser to talk.",
  "audio-capture": "No microphone was found.",
  network: "Voice recognition needs an internet connection.",
});

export const voiceError = (code) => VOICE_ERRORS[code] ?? `Voice input stopped (${code}).`;
