import { SPEECH_LANG } from "./config.js";

export const isBrowserVoiceSupported = Boolean(window.speechSynthesis && window.SpeechSynthesisUtterance);

const STOPPED = new Set(["interrupted", "canceled"]);

export function createBrowserVoice() {
  return {
    speak(text) {
      return new Promise((resolve, reject) => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = SPEECH_LANG;
        utterance.onend = resolve;
        utterance.onerror = (event) => (STOPPED.has(event.error) ? resolve() : reject(new Error(event.error)));
        window.speechSynthesis.speak(utterance);
      });
    },
    stop() {
      window.speechSynthesis.cancel();
    },
  };
}
