import "./styles.css";
import { Speaker } from "./enums.js";
import { takeTurn } from "./mcp.js";
import { MicLabel, Note, SpeakerName, VoiceHint, voiceError } from "./messages.js";
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

function setupVoice() {
  if (!isVoiceSupported) {
    voiceHint.textContent = VoiceHint.UNSUPPORTED;
    return;
  }

  const listener = createListener({
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
      if (listening) voiceHint.textContent = VoiceHint.LISTENING;
      else if (voiceHint.textContent === VoiceHint.LISTENING) voiceHint.textContent = "";
    },
    onError: (code) => {
      voiceHint.textContent = voiceError(code);
    },
  });

  micButton.hidden = false;
  micButton.textContent = MicLabel.START;
  micButton.addEventListener("click", () => (listener.listening ? listener.stop() : listener.start()));
}

setupVoice();
