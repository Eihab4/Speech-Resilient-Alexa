# Branch: feature/voice-output

Alexa reads every reply aloud in the browser page, with the browser's own `speechSynthesis`. It is free, runs on the device and needs no key.

## Commits

| Commit                             | What it did                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------- |
| `chore: add web tests`             | Vitest for `web/`, run with `npm test`.                                                       |
| `feat: read replies aloud`         | `web/src/speak.js` turns text into speech in `SPEECH_LANG`; `main.js` speaks every reply.     |
| `feat: pause the mic while Alexa talks` | `web/src/pause.js` stops the listener when Alexa starts talking and starts it again after, so she never hears herself. |
| `feat: add a mute toggle`          | A **Mute Alexa** button. Muting mid-reply cuts her off and frees the microphone at once.      |

## Tests

```bash
cd web
npm test
```

The browser's speech API does not exist in Node, so `web/tests/fakes.js` stands in for it with the same shape: `speak` queues, `cancel` interrupts, and a `finish` helper ends the current reply. The tests check what the page does with it: what is spoken, when speaking starts and ends, and that the microphone stops and restarts around a reply.

## Decisions made on this branch

- **Speaking lives in its own file.** `speak.js` only talks, `voice.js` only listens, `pause.js` only joins the two. Each is tested alone.
- **The listener is paused, not muted.** Stopping it is the one way to be sure neither Amazon Transcribe nor the browser hears Alexa's reply.
- **Muting cuts the current reply.** A person who presses mute wants silence now, not after the sentence.
- **Same language for both directions.** The voice uses `SPEECH_LANG` from `config.js`, like the listener.

## Still open

1. **Voice choice.** The browser picks its default voice for the language. A setting for a named voice could come later if the demo needs it.
2. **Restarting the browser listener right after a reply** can race with its own `onend`. `pause.js` skips the start when it is already listening, which covers the case seen so far.
3. **Checked in Chrome only.** Safari and Firefox speak too, but their microphone paths differ.
