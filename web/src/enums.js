// Mirrors mcp-server/enums and the tool names in mcp-server/server.py.

export const Tool = Object.freeze({
  UNDERSTAND_SPEECH: "understand_speech",
  DO_CONFIRMED_REQUEST: "do_confirmed_request",
  CANCEL_REQUEST: "cancel_request",
  RESUME_UNFINISHED: "resume_unfinished",
});

export const NextMove = Object.freeze({
  LISTEN: "listen",
  ASK: "ask",
  CONFIRM: "confirm",
  CANCEL: "cancel",
  DONE: "done",
});

export const Speaker = Object.freeze({
  USER: "user",
  ALEXA: "alexa",
});

// Mirrors TranscriptType in mcp-server/enums/speech.py.
export const TranscriptType = Object.freeze({
  PARTIAL: "partial",
  FINAL: "final",
  UNAVAILABLE: "unavailable",
  ERROR: "error",
});
