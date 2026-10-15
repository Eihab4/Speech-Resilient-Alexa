export const MCP_URL = import.meta.env.VITE_MCP_URL ?? "http://127.0.0.1:8000/mcp";

export const CLIENT_INFO = Object.freeze({ name: "speech-resilient-alexa-web", version: "0.1.0" });

// Language the browser listens for. The demo and the server's prompts are in English.
export const SPEECH_LANG = import.meta.env.VITE_SPEECH_LANG ?? "en-US";

// The voice WebSocket on the MCP server, which passes the microphone to Amazon Transcribe.
const transcribeUrl = new URL("/transcribe", MCP_URL);
transcribeUrl.protocol = transcribeUrl.protocol === "https:" ? "wss:" : "ws:";
export const TRANSCRIBE_URL = import.meta.env.VITE_TRANSCRIBE_URL ?? transcribeUrl.href;

export const SPEAK_URL = import.meta.env.VITE_SPEAK_URL ?? new URL("/speak", MCP_URL).href;

// Must match TRANSCRIBE_SAMPLE_RATE_HZ on the server.
export const TRANSCRIBE_SAMPLE_RATE = 16000;
