import { SPEAK_URL } from "./config.js";

export function createPollyVoice() {
  let playing = null;

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
      const response = await fetch(SPEAK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const url = URL.createObjectURL(await response.blob());
      try {
        await play(url);
      } finally {
        URL.revokeObjectURL(url);
        playing = null;
      }
    },
    stop() {
      playing?.pause();
    },
  };
}
