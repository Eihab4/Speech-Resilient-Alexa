// Collects what the person says until they have really stopped. Speech recognition ends a piece at every
// pause, but this person may pause mid-sentence for longer than that, so Alexa waits their own wait time
// (wait_seconds, learned by the server) before answering. Each pause inside a sentence is measured and sent
// along, so the server keeps learning it.

export const DEFAULT_WAIT_SECONDS = 2;

export function createGatherer({ send, now = () => Date.now() }) {
  let pieces = [];
  let pauses = [];
  let lastEnd = null; // when the last piece ended
  let resumedAt = null; // when the person started talking again after it
  let timer = null;
  let waitMs = DEFAULT_WAIT_SECONDS * 1000;

  function flush() {
    clearTimeout(timer);
    timer = null;
    if (pieces.length === 0) return;
    const words = pieces.join(" ");
    const measured = pauses;
    pieces = [];
    pauses = [];
    lastEnd = null;
    resumedAt = null;
    send(words, measured);
  }

  function waitThen(ms) {
    clearTimeout(timer);
    timer = setTimeout(flush, ms);
  }

  return {
    get pending() {
      return pieces.join(" ");
    },
    setWait(seconds) {
      if (seconds > 0) waitMs = seconds * 1000;
    },
    // Partial words: the person is talking again, so Alexa doesn't answer yet.
    speaking() {
      if (pieces.length === 0) return;
      resumedAt ??= now();
      // If recognition never finishes this piece, still answer in the end.
      waitThen(waitMs * 2);
    },
    // A finished piece. immediate skips the wait, for "stop" during an emergency countdown.
    piece(text, { immediate = false } = {}) {
      if (lastEnd !== null) pauses.push(Math.max(0, Math.round((resumedAt ?? now()) - lastEnd)));
      pieces.push(text);
      lastEnd = now();
      resumedAt = null;
      if (immediate) flush();
      else waitThen(waitMs);
    },
    flush,
  };
}
