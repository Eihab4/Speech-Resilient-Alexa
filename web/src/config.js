export const MCP_URL = import.meta.env.VITE_MCP_URL ?? "http://127.0.0.1:8000/mcp";

export const CLIENT_INFO = Object.freeze({ name: "speech-resilient-alexa-web", version: "0.1.0" });

// Language the browser listens for. The demo and the server's prompts are in English.
export const SPEECH_LANG = import.meta.env.VITE_SPEECH_LANG ?? "en-US";

// The voice WebSocket on the MCP server, which passes the microphone to Amazon Transcribe.
const transcribeUrl = new URL("/transcribe", MCP_URL);
transcribeUrl.protocol = transcribeUrl.protocol === "https:" ? "wss:" : "ws:";
export const TRANSCRIBE_URL = import.meta.env.VITE_TRANSCRIBE_URL ?? transcribeUrl.href;

export const SPEAK_URL = import.meta.env.VITE_SPEAK_URL ?? new URL("/speak", MCP_URL).href;

// The page's account on the MCP server: the username is the person's user_id in the MCP tools.
export const SIGN_UP_URL = new URL("/signup", MCP_URL).href;
export const SIGN_IN_URL = new URL("/signin", MCP_URL).href;
export const SIGN_OUT_URL = new URL("/signout", MCP_URL).href;
export const ME_URL = new URL("/me", MCP_URL).href;

// The family's setup on the MCP server: who the person is, and who gets their emergency alerts.
export const PROFILE_URL = new URL("/profile", MCP_URL).href;
export const HELPERS_URL = new URL("/helpers", MCP_URL).href;
// How often the helper list is checked while someone hasn't opened their Telegram link yet.
export const HELPERS_REFRESH_MS = 3000;

// Must match TRANSCRIBE_SAMPLE_RATE_HZ on the server.
export const TRANSCRIBE_SAMPLE_RATE = 16000;

// The location sent with an emergency alert. A position up to a minute old is good enough, and the
// alert never waits longer than the timeout for a new one.
export const POSITION_TIMEOUT_MS = 4000;
export const POSITION_MAX_AGE_MS = 60000;
