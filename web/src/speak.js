import { SPEECH_LANG } from "./config.js";

export const isSpeechSupported = Boolean(window.speechSynthesis && window.SpeechSynthesisUtterance);

export function createSpeaker({ onSpeakingChange }) {
  let queued = 0;

  function finished() {
    if (queued === 0) return;
    queued -= 1;
    if (queued === 0) onSpeakingChange(false);
  }

  return {
    speak(text) {
      if (!text) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = SPEECH_LANG;
      utterance.onend = finished;
      utterance.onerror = finished;
      if (queued === 0) onSpeakingChange(true);
      queued += 1;
      window.speechSynthesis.speak(utterance);
    },
    get speaking() {
      return queued > 0;
    },
  };
}
