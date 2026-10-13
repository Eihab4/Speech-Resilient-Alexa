export const MCP_URL = import.meta.env.VITE_MCP_URL ?? "http://127.0.0.1:8000/mcp";

export const CLIENT_INFO = Object.freeze({ name: "speech-resilient-alexa-web", version: "0.1.0" });

// Language the browser listens for. The demo and the server's prompts are in English.
export const SPEECH_LANG = import.meta.env.VITE_SPEECH_LANG ?? "en-US";
