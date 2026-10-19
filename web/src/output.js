export function createOutput(voices, { onSpeakingChange }) {
  let muted = false;
  let queued = 0;
  let active = null;
  let last = Promise.resolve();

  async function say(text) {
    for (const voice of voices) {
      active = voice;
      try {
        return await voice.speak(text);
      } catch {
        active = null;
      }
    }
  }

  function begin() {
    if (queued === 0) onSpeakingChange(true);
    queued += 1;
  }

  function end() {
    queued -= 1;
    if (queued === 0) onSpeakingChange(false);
  }

  return {
    speak(text) {
      if (muted || !text) return;
      begin();
      last = last.then(() => (muted ? undefined : say(text))).finally(end);
    },
    setMuted(value) {
      muted = value;
      if (muted) active?.stop();
    },
    get muted() {
      return muted;
    },
    get speaking() {
      return queued > 0;
    },
  };
}
