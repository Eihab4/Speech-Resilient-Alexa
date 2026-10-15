export function pauseWhileSpeaking(getListener, onPaused) {
  let resume = false;

  return (speaking) => {
    const listener = getListener();
    if (!listener) return;
    if (speaking) {
      resume = listener.listening;
      if (resume) {
        listener.stop();
        onPaused();
      }
    } else if (resume) {
      resume = false;
      if (!listener.listening) listener.start();
    }
  };
}
