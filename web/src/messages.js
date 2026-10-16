import { Speaker } from "./enums.js";

export const SpeakerName = Object.freeze({
  [Speaker.USER]: "You",
  [Speaker.ALEXA]: "Alexa",
});

export const Note = Object.freeze({
  ERROR: "Error",
  ALERT: "Emergency alert",
  nextMove: (move) => `Next: ${move}`,
});

export const ErrorMessage = Object.freeze({
  unreachable: (url) => `Could not reach the MCP server at ${url}.`,
  toolFailed: (name) => `${name} failed.`,
  setupFailed: (status) => `The server answered ${status}.`,
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

export const SosLabel = Object.freeze({
  countdown: (seconds) => `Emergency alert in ${seconds}… Say "stop" if you're okay.`,
});

export const PeopleLabel = Object.freeze({
  LINKED: "Linked",
  WAITING: "Waiting for them to open the link",
  COPY: "Copy invitation",
  COPIED: "Copied",
  COPY_FAILED: "Couldn't copy. Select the link above and copy it by hand.",
  SHARE: "Share invitation",
  REMOVE: "Remove",
  SAVED: "Saved.",
  NO_TELEGRAM: "Telegram isn't set up on the server, so alerts only go to the server log.",
  LOCATION_ON: "Location allowed. It's only read during an emergency.",
  LOCATION_OFF: "No location from this device: alerts will give the home address instead.",
  sendLink: (name) =>
    `Send ${name} the invitation. Once they open the link in Telegram and press Start, they get your alerts.`,
});

// What the family sends a helper, ready to paste into WhatsApp, a text message or an email.
export const invitation = (helper, person, link) =>
  [
    `Hi ${helper}! ${person} added you as an emergency contact on Speech-Resilient Alexa.`,
    `If ${person} ever says "I fell" or "help help", you'll get a message in Telegram with where they are.`,
    "",
    "To start:",
    `1. Open this link on your phone (install Telegram first if you don't have it): ${link}`,
    "2. Press Start.",
    "",
    `The bot answers "You're linked" when it's done.`,
  ].join("\n");

export const PersonLabel = Object.freeze({
  hello: (name) => `Hi, ${name}`,
});

// What Alexa says when someone signs in.
export const Greeting = Object.freeze({
  hello: (name) => `Hi ${name}! Take your time, I'm listening.`,
});
