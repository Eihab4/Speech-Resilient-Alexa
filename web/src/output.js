export function createOutput(voices, { onSpeakingChange }) {
  let muted = false;
  let queued = 0;
  let current = 0;
  let last = Promise.resolve();

  async function say(text) {
    while (current < voices.length) {
      try {
        return await voices[current].speak(text);
      } catch {
        current += 1;
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
      if (muted && queued > 0) voices[current].stop();
    },
    get muted() {
      return muted;
    },
    get speaking() {
      return queued > 0;
    },
  };
}
