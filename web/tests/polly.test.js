import { beforeEach, expect, test, vi } from "vitest";

let requests;
let players;
let respond;
let voice;

class FakeAudio {
  constructor(src) {
    this.src = src;
    this.paused = false;
    players.push(this);
  }
  play() {
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
    this.onpause?.();
  }
  end() {
    this.onended?.();
  }
}

beforeEach(async () => {
  requests = [];
  players = [];
  respond = () => new Response(new Blob([new Uint8Array([1, 2, 3])], { type: "audio/mpeg" }));
  globalThis.window = globalThis;
  globalThis.Audio = FakeAudio;
  globalThis.fetch = vi.fn(async (url, init) => {
    requests.push({ url, body: JSON.parse(init.body), authorization: init.headers.Authorization });
    return respond();
  });
  const { createPollyVoice } = await import("../src/polly.js");
  voice = createPollyVoice(() => "session-token");
});

test("the text goes to the server's speak route and the audio is played", async () => {
  const done = voice.speak("Mm-hm, go on.");

  await vi.waitFor(() => expect(players).toHaveLength(1));
  expect(requests).toEqual([
    { url: "http://127.0.0.1:8000/speak", body: { text: "Mm-hm, go on." }, authorization: "Bearer session-token" },
  ]);
  expect(players[0].src).toMatch(/^blob:/);

  players[0].end();
  await expect(done).resolves.toBeUndefined();
});

test("a server that cannot speak makes the voice fail so the next one takes over", async () => {
  respond = () => new Response(JSON.stringify({ error: "Amazon Polly is unavailable" }), { status: 503 });

  await expect(voice.speak("Done.")).rejects.toThrow("503");
  expect(players).toEqual([]);
});

test("a server that cannot be reached makes the voice fail too", async () => {
  respond = () => Promise.reject(new TypeError("Failed to fetch"));

  await expect(voice.speak("Done.")).rejects.toThrow("Failed to fetch");
});

test("stopping while the audio is still being fetched means it never plays", async () => {
  let deliver;
  respond = () => new Promise((resolve) => (deliver = resolve));
  const done = voice.speak("Should I set it?");
  await vi.waitFor(() => expect(deliver).toBeDefined());

  voice.stop();
  deliver(new Response(new Blob([new Uint8Array([1])], { type: "audio/mpeg" })));

  await expect(done).resolves.toBeUndefined();
  expect(players).toEqual([]);
});

test("stopping pauses the audio and ends the reply", async () => {
  const done = voice.speak("Should I set it?");
  await vi.waitFor(() => expect(players).toHaveLength(1));

  voice.stop();

  await expect(done).resolves.toBeUndefined();
  expect(players[0].paused).toBe(true);
});
