import { SPEAK_URL } from "./config.js";
import { json, signedIn } from "./http.js";

export function createPollyVoice(token) {
  let playing = null;
  let stopped = false;

  async function play(url) {
    playing = new Audio(url);
    await new Promise((resolve, reject) => {
      playing.onended = resolve;
      playing.onpause = resolve;
      playing.onerror = () => reject(new Error("audio"));
      playing.play().catch(reject);
    });
  }

  return {
    async speak(text) {
      stopped = false;
      const response = await fetch(SPEAK_URL, signedIn(token(), json("POST", { text })));
      if (!response.ok) throw new Error(String(response.status));
      const url = URL.createObjectURL(await response.blob());
      try {
        if (!stopped) await play(url);
      } finally {
        URL.revokeObjectURL(url);
        playing = null;
      }
    },
    stop() {
      stopped = true;
      playing?.pause();
    },
  };
}
