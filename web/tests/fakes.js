export function installFakeSpeechSynthesis() {
  const spoken = [];
  globalThis.window = globalThis;
  globalThis.SpeechSynthesisUtterance = class {
    constructor(text) {
      this.text = text;
    }
  };
  globalThis.speechSynthesis = {
    speak: (utterance) => spoken.push(utterance),
    cancel: () => spoken.splice(0).forEach((utterance) => utterance.onerror?.({ error: "interrupted" })),
    finish: () => spoken.shift()?.onend?.(),
    fail: () => spoken.shift()?.onerror?.({ error: "synthesis-failed" }),
  };
  return spoken;
}

export function fakeVoice(name, log, { fails = false } = {}) {
  let finish = null;
  return {
    speak(text) {
      log.push(`${name}: ${text}`);
      if (fails) return Promise.reject(new Error(name));
      return new Promise((resolve) => (finish = resolve));
    },
    stop() {
      log.push(`${name}: stop`);
      finish?.();
    },
    finish() {
      finish?.();
    },
  };
}
