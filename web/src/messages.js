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

export const MuteLabel = Object.freeze({
  MUTE: "Mute Alexa",
  UNMUTE: "Unmute Alexa",
});

export const VoiceHint = Object.freeze({
  LISTENING: "Listening… pause between pieces, each pause is sent on its own.",
  LISTENING_IN_BROWSER: "Listening with the browser (Amazon Transcribe is unavailable)… pause between pieces.",
  UNSUPPORTED: "Voice needs Chrome or Edge. You can still type.",
  ALEXA_TALKING: "Alexa is talking… the microphone comes back when she finishes.",
});

const VOICE_ERRORS = Object.freeze({
  "not-allowed": "Microphone access was blocked. Allow it in the browser to talk.",
  "service-not-allowed": "Microphone access was blocked. Allow it in the browser to talk.",
  "audio-capture": "No microphone was found.",
  network: "Voice recognition needs an internet connection.",
  transcribe: "Amazon Transcribe stopped. Press Speak to try again.",
});

export const voiceError = (code) => VOICE_ERRORS[code] ?? `Voice input stopped (${code}).`;
