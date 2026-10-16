import "./styles.css";
import { Speaker } from "./enums.js";
import { sendSos, takeTurn } from "./mcp.js";
import {
  Greeting,
  MicLabel,
  MuteLabel,
  Note,
  PersonLabel,
  SosLabel,
  SpeakerName,
  VoiceHint,
  voiceError,
} from "./messages.js";
import { pauseWhileSpeaking } from "./pause.js";
import { createOutput } from "./output.js";
import { signIn, signOut, signUp, whoAmI } from "./account.js";
import { forgetSession, loadSession, saveSession } from "./session.js";
import { createPollyVoice } from "./polly.js";
import { readPosition } from "./position.js";
import { setupPeople } from "./setup.js";
import { createSos } from "./sos.js";
import { createBrowserVoice, isBrowserVoiceSupported } from "./speak.js";
import { createTranscribeListener, isMicSupported } from "./transcribe.js";
import { createListener, isVoiceSupported } from "./voice.js";

const form = document.querySelector("#turn-form");
const account = document.querySelector("#account");
const signInForm = document.querySelector("#sign-in-form");
const signUpForm = document.querySelector("#sign-up-form");
const accountError = document.querySelector("#account-error");
const signedIn = document.querySelector("#signed-in");
const personName = document.querySelector("#person-name");
const signOutButton = document.querySelector("#sign-out");
const heard = document.querySelector("#heard");
const sendButton = document.querySelector("#send");
const micButton = document.querySelector("#mic");
const muteButton = document.querySelector("#mute");
const voiceHint = document.querySelector("#voice-hint");
const conversation = document.querySelector("#conversation");
const sosCountdown = document.querySelector("#sos-countdown");
const emptyConversation = conversation.innerHTML;
let listener = null;
let session = loadSession();
// The username is the person's user_id in the MCP tools, as the Amazon account would be on a real Alexa+.
const currentId = () => session?.username ?? "";
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

function sendTurn(words) {
  addMessage(Speaker.USER, words);
  pending += 1;
  sendButton.disabled = true;

  queue = queue.then(async () => {
    try {
      const result = await takeTurn(currentId(), words);
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
const people = setupPeople(document.querySelector("#people"), () => session);

function showAccount() {
  account.hidden = Boolean(session);
  signedIn.hidden = !session;
  personName.textContent = session ? PersonLabel.hello(session.name) : "";
}

function showForm(form) {
  signInForm.hidden = form !== signInForm;
  signUpForm.hidden = form !== signUpForm;
  accountError.textContent = "";
  form.querySelector("input").focus();
}

async function enter(start, form) {
  accountError.textContent = "";
  try {
    session = saveSession(await start());
  } catch (error) {
    accountError.textContent = error.message;
    return;
  }
  form.reset();
  showAccount();
  const hello = Greeting.hello(session.name);
  addMessage(Speaker.ALEXA, hello);
  voice.speak(hello);
  heard.focus();
}

const field = (form, name) => form.querySelector(`[id$="-${name}"]`).value;

signInForm.addEventListener("submit", (event) => {
  event.preventDefault();
  enter(() => signIn(field(signInForm, "username").trim(), field(signInForm, "password")), signInForm);
});

signUpForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const username = field(signUpForm, "username").trim();
  enter(() => signUp(username, field(signUpForm, "name").trim(), field(signUpForm, "password")), signUpForm);
});

document.querySelector("#show-sign-up").addEventListener("click", () => showForm(signUpForm));
document.querySelector("#show-sign-in").addEventListener("click", () => showForm(signInForm));

function leave() {
  if (listener?.listening) listener.stop();
  sos.follow({});
  forgetSession();
  session = null;
  conversation.innerHTML = emptyConversation;
  people.close();
  showAccount();
  showForm(signInForm);
}

signOutButton.addEventListener("click", () => {
  const token = session?.token;
  leave();
  if (token) signOut(token).catch(() => {});
});

// A kept session may have been signed out elsewhere; check it, and keep the name up to date.
async function checkSession() {
  if (!session) return;
  try {
    const me = await whoAmI(session.token);
    session = saveSession({ ...session, name: me.name });
    showAccount();
  } catch (error) {
    if (error.status === 401) leave();
  }
}

showAccount();
checkSession();
