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
  };
  return spoken;
}
