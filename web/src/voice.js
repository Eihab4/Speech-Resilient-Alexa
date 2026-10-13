import { SPEECH_LANG } from "./config.js";

const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;

// Chrome and Edge have it; Firefox does not, so the page falls back to typing.
export const isVoiceSupported = Boolean(Recognition);

// Errors that only mean "nothing was said yet". Listening simply carries on.
const QUIET_ERRORS = new Set(["no-speech", "aborted"]);

// Listens until stopped. Every pause in speech ends one piece, which is passed to onFragment:
// slow, broken-up speech arrives as separate turns, the way Alexa would hear it.
export function createListener({ onInterim, onFragment, onListeningChange, onError }) {
  const recognition = new Recognition();
  recognition.lang = SPEECH_LANG;
  recognition.continuous = true;
  recognition.interimResults = true;

  let wanted = false;

  recognition.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      const text = result[0].transcript.trim();
      if (!text) continue;
      if (result.isFinal) onFragment(text);
      else onInterim(text);
    }
  };

  recognition.onerror = (event) => {
    if (QUIET_ERRORS.has(event.error)) return;
    wanted = false;
    onError(event.error);
  };

  // The browser ends a session on its own after a while; restart it while the user still wants to talk.
  recognition.onend = () => {
    if (wanted) recognition.start();
    else onListeningChange(false);
  };

  return {
    start() {
      wanted = true;
      recognition.start();
      onListeningChange(true);
    },
    stop() {
      wanted = false;
      recognition.stop();
    },
    get listening() {
      return wanted;
    },
  };
}
