# Tasks

- [x] **Rana — Voice input (speech → text):** A "Speak" button uses the browser's speech recognition (Web Speech API). Each pause sends what was said as its own turn, so slow, broken-up speech reaches the server in pieces. Code: `web/src/voice.js`. Works in Chrome and Edge; other browsers fall back to typing.
- [ ] **Eihab — Voice output (text → speech):** Alexa reads every reply aloud with the browser's `speechSynthesis`. Free and on-device, no API key.
  - Speak `result.say` after each reply is shown, in `sendTurn` in `web/src/main.js`.
  - Put the speaking code next to the listening code in `web/src/voice.js` (for example a `speak(text)` export), and texts in `web/src/messages.js`.
  - Pause the microphone while Alexa is talking, or it will hear her and send her words as the user's turn.
  - Add a mute toggle, and use `SPEECH_LANG` from `web/src/config.js` for the voice.
  - Test in Chrome.
