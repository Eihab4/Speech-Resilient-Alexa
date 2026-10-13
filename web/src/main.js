import "./styles.css";
import { Speaker } from "./enums.js";
import { takeTurn } from "./mcp.js";
import { Note, SpeakerName } from "./messages.js";

const form = document.querySelector("#turn-form");
const userId = document.querySelector("#user-id");
const heard = document.querySelector("#heard");
const sendButton = form.querySelector("button");
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const words = heard.value.trim();
  if (!words) return;

  addMessage(Speaker.USER, words);
  heard.value = "";
  sendButton.disabled = true;

  try {
    const result = await takeTurn(userId.value.trim(), words);
    addMessage(Speaker.ALEXA, result.say, result.next_move ? Note.nextMove(result.next_move) : "");
  } catch (error) {
    addMessage(Speaker.ALEXA, error.message, Note.ERROR);
  } finally {
    sendButton.disabled = false;
    heard.focus();
  }
});
