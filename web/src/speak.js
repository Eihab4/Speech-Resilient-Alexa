import { SPEECH_LANG } from "./config.js";

export const isSpeechSupported = Boolean(window.speechSynthesis && window.SpeechSynthesisUtterance);

export function createSpeaker({ onSpeakingChange }) {
  let queued = 0;
  let muted = false;

  function finished() {
    if (queued === 0) return;
    queued -= 1;
    if (queued === 0) onSpeakingChange(false);
  }

  return {
    speak(text) {
      if (muted || !text) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = SPEECH_LANG;
      utterance.onend = finished;
      utterance.onerror = finished;
      if (queued === 0) onSpeakingChange(true);
      queued += 1;
      window.speechSynthesis.speak(utterance);
    },
    setMuted(value) {
      muted = value;
      if (muted) window.speechSynthesis.cancel();
    },
    get muted() {
      return muted;
    },
    get speaking() {
      return queued > 0;
    },
  };
}
