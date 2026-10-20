import "./styles.css";
import { Speaker } from "./enums.js";
import { sendSos, takeTurn } from "./mcp.js";
import { Greeting, MicLabel, MuteLabel, Note, SosLabel, SpeakerName, VoiceHint, voiceError } from "./messages.js";
import { pauseWhileSpeaking } from "./pause.js";
import { createGatherer } from "./gather.js";
import { createOutput } from "./output.js";
import { createPollyVoice } from "./polly.js";
import { readPosition } from "./position.js";
import { setupPeople } from "./setup.js";
import { setupSignIn } from "./signin.js";
import { createSos } from "./sos.js";
import { createBrowserVoice, isBrowserVoiceSupported } from "./speak.js";
import { createTranscribeListener, isMicSupported } from "./transcribe.js";
import { createListener, isVoiceSupported } from "./voice.js";

const form = document.querySelector("#turn-form");
const heard = document.querySelector("#heard");
const sendButton = document.querySelector("#send");
const micButton = document.querySelector("#mic");
const muteButton = document.querySelector("#mute");
const voiceHint = document.querySelector("#voice-hint");
const conversation = document.querySelector("#conversation");
const sosCountdown = document.querySelector("#sos-countdown");
const emptyConversation = conversation.innerHTML;
let listener = null;
let signedIn = null;
// The username is the person's user_id in the MCP tools, as the Amazon account would be on a real Alexa+.
const currentId = () => signedIn?.session?.username ?? "";
const sos = createSos({
  readPosition,
  onTick: (seconds) => {
    sosCountdown.hidden = seconds === 0;
    sosCountdown.textContent = seconds ? SosLabel.countdown(seconds) : "";
  },
  onDue: () => (queue = queue.then(sendAlert)),
});
const pauseMic = pauseWhileSpeaking(
  () => listener,
  () => (voiceHint.textContent = VoiceHint.ALEXA_TALKING),
);
const onSpeakingChange = (speaking) => {
  pauseMic(speaking);
  if (!speaking) sos.begin();
};
const voices = [createPollyVoice(), ...(isBrowserVoiceSupported ? [createBrowserVoice()] : [])];
const voice = createOutput(voices, { onSpeakingChange });

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

function sendTurn(words, pausesMs = []) {
  addMessage(Speaker.USER, words);
  pending += 1;
  sendButton.disabled = true;

  queue = queue.then(async () => {
    try {
      const result = await takeTurn(currentId(), words, pausesMs);
      gatherer.setWait(result.wait_seconds);
      addMessage(Speaker.ALEXA, result.say, result.next_move ? Note.nextMove(result.next_move) : "");
      sos.follow(result);
      voice.speak(result.say);
      if (!voice.speaking) sos.begin();
    } catch (error) {
      addMessage(Speaker.ALEXA, error.message, Note.ERROR);
    } finally {
      pending -= 1;
      sendButton.disabled = pending > 0;
    }
  });
}

// Queued behind the turns already sent, so a "stop" said just before the end still cancels it.
async function sendAlert() {
  const position = sos.take();
  if (!position) return;
  try {
    const result = await sendSos(currentId(), await position);
    addMessage(Speaker.ALEXA, result.say, Note.ALERT);
    voice.speak(result.say);
  } catch (error) {
    addMessage(Speaker.ALEXA, error.message, Note.ERROR);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const words = heard.value.trim();
  if (!words) return;

  heard.value = "";
  sendTurn(words);
  heard.focus();
});

// Spoken pieces wait for the person's own pause length; typed words go at once.
const gatherer = createGatherer({
  send: (words, pausesMs) => {
    heard.value = "";
    sendTurn(words, pausesMs);
  },
});

let usingBrowser = false;
const ownHints = [VoiceHint.LISTENING, VoiceHint.LISTENING_IN_BROWSER];

const listenerEvents = {
  onInterim: (text) => {
    gatherer.speaking();
    heard.value = [gatherer.pending, text].filter(Boolean).join(" ");
  },
  onFragment: (text) => {
    // During an emergency countdown, "stop" can't wait.
    gatherer.piece(text, { immediate: sos.state !== "idle" });
    heard.value = gatherer.pending;
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

  listener = browser;
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

function setupMute() {
  muteButton.addEventListener("click", () => {
    voice.setMuted(!voice.muted);
    muteButton.setAttribute("aria-pressed", String(voice.muted));
    muteButton.textContent = voice.muted ? MuteLabel.UNMUTE : MuteLabel.MUTE;
  });
}

setupVoice();
setupMute();
const people = setupPeople(document.querySelector("#people"), () => signedIn?.session);

signedIn = setupSignIn({
  onSession: (session) => gatherer.setWait(session.wait_seconds),
  onSignedIn(session) {
    const hello = Greeting.hello(session.name);
    addMessage(Speaker.ALEXA, hello);
    voice.speak(hello);
    heard.focus();
  },
  onSignedOut() {
    if (listener?.listening) listener.stop();
    sos.follow({});
    conversation.innerHTML = emptyConversation;
    people.close();
  },
});
