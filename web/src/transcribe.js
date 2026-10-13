import { TRANSCRIBE_SAMPLE_RATE, TRANSCRIBE_URL } from "./config.js";
import { TranscriptType } from "./enums.js";

const workletUrl = new URL("./pcm-worklet.js", import.meta.url);

// Every current browser has these; without them the page uses its own recognition, or typing.
export const isMicSupported = Boolean(navigator.mediaDevices?.getUserMedia && window.AudioWorkletNode);

// Same shape as the browser listener in voice.js, so the page doesn't care which one runs.
// Audio streams to the MCP server, which passes it to Amazon Transcribe; only text comes back.
// onUnavailable fires when Transcribe can't be reached at all, so the page can fall back.
export function createTranscribeListener({ onInterim, onFragment, onListeningChange, onError, onUnavailable }) {
  let session = null;

  async function start() {
    const current = { opened: false, stopped: false, unavailable: false, release: () => {} };
    session = current;
    onListeningChange(true);

    let microphone;
    try {
      microphone = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
    } catch (error) {
      session = null;
      onListeningChange(false);
      onError(error.name === "NotAllowedError" ? "not-allowed" : "audio-capture");
      return;
    }

    // Stopped while the browser was still asking for the microphone.
    if (current.stopped) {
      microphone.getTracks().forEach((track) => track.stop());
      session = null;
      onListeningChange(false);
      return;
    }

    const audio = new AudioContext();
    const socket = new WebSocket(TRANSCRIBE_URL);
    socket.binaryType = "arraybuffer";
    current.socket = socket;
    current.release = () => {
      microphone.getTracks().forEach((track) => track.stop());
      if (audio.state !== "closed") audio.close();
    };

    socket.onopen = async () => {
      current.opened = true;
      await audio.audioWorklet.addModule(workletUrl);
      const pcm = new AudioWorkletNode(audio, "pcm-16", { processorOptions: { targetRate: TRANSCRIBE_SAMPLE_RATE } });
      pcm.port.onmessage = ({ data }) => {
        if (socket.readyState === WebSocket.OPEN) socket.send(data);
      };
      audio.createMediaStreamSource(microphone).connect(pcm);
    };

    socket.onmessage = ({ data }) => {
      const { type, text } = JSON.parse(data);
      if (type === TranscriptType.PARTIAL) onInterim(text);
      else if (type === TranscriptType.FINAL) onFragment(text);
      else if (type === TranscriptType.UNAVAILABLE) current.unavailable = true;
      else if (type === TranscriptType.ERROR) onError("transcribe");
    };

    // The server closes the socket once Transcribe has sent its last words, or when it failed.
    socket.onclose = () => {
      current.release();
      if (session === current) session = null;
      onListeningChange(false);
      if (!current.stopped && (current.unavailable || !current.opened)) onUnavailable();
    };
  }

  function stop() {
    const current = session;
    if (!current) return;
    current.stopped = true;
    current.release();
    // Ask the server to finish, so the last words still arrive; if it never connected, just close.
    if (current.socket?.readyState === WebSocket.OPEN) current.socket.send("stop");
    else current.socket?.close();
  }

  return {
    start,
    stop,
    get listening() {
      return session !== null;
    },
  };
}
