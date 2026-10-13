import "./styles.css";
import { Speaker } from "./enums.js";
import { takeTurn } from "./mcp.js";
import { MicLabel, Note, SpeakerName, VoiceHint, voiceError } from "./messages.js";
import { createTranscribeListener, isMicSupported } from "./transcribe.js";
import { createListener, isVoiceSupported } from "./voice.js";

const form = document.querySelector("#turn-form");
const userId = document.querySelector("#user-id");
const heard = document.querySelector("#heard");
const sendButton = document.querySelector("#send");
const micButton = document.querySelector("#mic");
const voiceHint = document.querySelector("#voice-hint");
const conversation = document.querySelector("#conversation");

function addMessage(speaker, text, note = "") {
  conversation.querySelector(".empty")?.remove();
  const message = document.createElement("article");
  message.className = `message ${speaker}`;
  message.innerHTML = "<strong></strong><p></p><small></small>";
  message.querySelector("strong").textContent = SpeakerName[speaker];
  message.querySelector("p").textContent = text;
  message.querySelector("small").textContent = note;
  conversation.append(message);
}

// Turns go to the server one at a time, in the order they were said, because each one
// builds on the pieces before it. Voice can produce a new piece while the last is still in flight.
let queue = Promise.resolve();
let pending = 0;

function sendTurn(words) {
  addMessage(Speaker.USER, words);
  pending += 1;
  sendButton.disabled = true;

  queue = queue.then(async () => {
    try {
      const result = await takeTurn(userId.value.trim(), words);
      addMessage(Speaker.ALEXA, result.say, result.next_move ? Note.nextMove(result.next_move) : "");
    } catch (error) {
      addMessage(Speaker.ALEXA, error.message, Note.ERROR);
    } finally {
      pending -= 1;
      sendButton.disabled = pending > 0;
    }
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const words = heard.value.trim();
  if (!words) return;

  heard.value = "";
  sendTurn(words);
  heard.focus();
});

let usingBrowser = false;
const ownHints = [VoiceHint.LISTENING, VoiceHint.LISTENING_IN_BROWSER];

const listenerEvents = {
  onInterim: (text) => {
    heard.value = text;
  },
  onFragment: (text) => {
    heard.value = "";
    sendTurn(text);
  },
  onListeningChange: (listening) => {
    micButton.setAttribute("aria-pressed", String(listening));
    micButton.textContent = listening ? MicLabel.STOP : MicLabel.START;
    // Clear only our own hint, so an error shown just before the mic stopped stays visible.
    if (listening) voiceHint.textContent = usingBrowser ? VoiceHint.LISTENING_IN_BROWSER : VoiceHint.LISTENING;
    else if (ownHints.includes(voiceHint.textContent)) voiceHint.textContent = "";
  },
  onError: (code) => {
    voiceHint.textContent = voiceError(code);
  },
};

// Amazon Transcribe first; the browser's own recognition if Transcribe can't be reached.
function setupVoice() {
  const browser = isVoiceSupported ? createListener(listenerEvents) : null;
  if (!isMicSupported && !browser) {
    voiceHint.textContent = VoiceHint.UNSUPPORTED;
    return;
  }

  let listener = browser;
  if (isMicSupported) {
    listener = createTranscribeListener({
      ...listenerEvents,
      onUnavailable: () => {
        listener = browser;
        usingBrowser = true;
        if (browser) {
          browser.start();
        } else {
          micButton.hidden = true;
          voiceHint.textContent = VoiceHint.UNSUPPORTED;
        }
      },
    });
  }

  micButton.hidden = false;
  micButton.textContent = MicLabel.START;
  micButton.addEventListener("click", () => (listener.listening ? listener.stop() : listener.start()));
}

setupVoice();
