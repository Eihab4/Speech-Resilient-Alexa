# Tasks

## Voice

- [x] **Rana — Voice input (speech → text):** a Speak button; what was said goes to the server in pieces. The microphone streams to the server, which uses Amazon Transcribe. If Transcribe is unavailable, the browser's own speech recognition takes over (Chrome and Edge).
- [x] **Eihab — Voice output (text → speech):** Alexa reads every reply aloud with Amazon Polly (neural voice, Joanna by default) through the server's `POST /speak`, so the AWS keys never reach the browser. The browser's voice is the fallback. The microphone pauses while she talks, and **Mute Alexa** cuts her off.
- [x] **Rana — Learn each person's pauses:** Alexa waits each person's own mid-sentence pause length before answering, instead of jumping in at every pause. Learned from their measured pauses (outliers dropped, 75th percentile) and from her early answers; returned as `wait_seconds`. Details: [feature-learn-pauses.md](branches/feature-learn-pauses.md).
- [ ] **SOS by voice waits too:** "I fell" said aloud starts the countdown only after the person's wait (up to 6 s). Make SOS words skip the wait in the page.
- [ ] **Polly retry:** once Polly fails, the page stays on the robotic browser voice until it's reloaded. Try Polly again on the next reply instead (`../web/src/output.js`).
- [ ] **Rana — `learn_my_speech`:** keep a word list per person in SQLite (names from contacts, and corrections like "no, *Sara*"). Push it to a Transcribe custom vocabulary so Alexa learns their words. An update takes a few minutes to be ready, so keep using the old list until then.

## Memory

- [x] **Rana — New request in the middle of one:** when the person starts something different while a request is open, Alexa asks before switching ("Should I stop the doctor reminder and call Mom instead?"), so each request stays its own row. Details: [feature-new-request.md](branches/feature-new-request.md).
- [ ] **Rana — Usual requests (after the task above):** Alexa counts what the person asks for most and uses it to understand broken speech faster ("c… mom" → "Call Mom?"). Still asks for yes. Details: [feature-usual-requests.md](branches/feature-usual-requests.md).
- [x] **Rana — Sign-in:** a username and password per person, so two people with the same name never share a memory; Alexa calls the person by the name on their account. Details: [feature-sign-in.md](branches/feature-sign-in.md).
- [x] **Stability:** one lock on the shared SQLite connection, and the server waits for the history tidy-up before closing (both could crash it).
- [ ] **Bug — the brain treats a finished request as open:** the history notes how a cancelled or replaced request ended, but not a finished one, so after "call mom" is done the brain may ask "Should I stop the doctor reminder…?". Add "(this request was done)" in `REQUEST_ENDINGS` (`mcp-server/messages/prompts.py`).
- [ ] **Bug — `cancel` saved as an intent:** when the person cancels, the request is saved with `intent = "cancel"`, which isn't a valid intent (only reminder, message, call).

## New tools

Each tool is a new file in `../mcp-server/tools`, with its texts in `mcp-server/messages/`. Every action asks for "yes" first, except `emergency_sos`. Messages go out through one `notify(contact, text)` helper, so the tools don't care which channel is used.

Next to each tool is the service it uses. **Polly** and **the brain** (the LLM) already work. **SNS**, **Translate**, **Comprehend** and **Location** are new: test each one on the account before building on it.

### Setup (do first)

- [ ] **AWS:** give the IAM user `speech-resilient-alexa` only what's used (SNS, Translate, Comprehend, Location). New accounts are in the SMS sandbox, so verify each demo phone number in the SNS console. If SMS doesn't work, use SNS email.
  - [x] **Location:** inline policy `LocationReverseGeocode`, allowing only `geo-places:ReverseGeocode`. Add `geo-places:SearchNearby` to it for `find_nearby`.
  - [ ] SNS, Translate, Comprehend.
- [x] **Telegram (needed for `emergency_sos`):** a free channel for `notify`. The bot is `@rana_sra_alerts_bot`, with `TELEGRAM_BOT_TOKEN` in `.env`. Helpers link their chat id by opening the bot's link from the page. SMS to Egypt needs a registered sender ID, so Telegram is the main channel for the demo.

### Do first

- [ ] **`ask_for_help`** — SNS, memory: when the person says "help", or Alexa still hasn't understood after a few tries, the caregiver gets what was understood so far ("Dad is trying to set a reminder for the doctor tomorrow, the time is unclear"). In the demo, a teammate's phone gets the SMS live.
- [ ] **`speech_trend`** — memory only: how many tries Alexa needed per request, day by day ("4 tries on day one, 1 now"). Goes with **Usual requests** in Memory: together they show Alexa learns the person over time.
- [ ] **`speech_practice`** — Transcribe, memory: daily speech exercises. Alexa gives words to say, scores each one from Transcribe's confidence per word, and tracks progress with `speech_trend`. For people recovering after a stroke. Today the server only passes the text on, so `transcription/stream.py` must also pass the confidence.
- [ ] **`finish_my_sentence`** — memory, brain: the person says "call…" and stops. Alexa offers the likely endings: "Mom? Sara? The doctor?", like phone keyboard suggestions, but spoken. The suggestions come from **Usual requests**, so do that first.
- [ ] **`notice_frustration`** — Comprehend: when the person repeats themselves or says "no no no", Alexa calms things down ("Take your time, I'm listening") and switches to yes/no questions or offers help. Comprehend reads the mood of the text and supports Arabic.
- [ ] **`yes_no_mode`** — memory only: after a few failed tries, Alexa stops asking to repeat and asks yes/no questions instead ("Do you want to call someone?" "Mom?"). A change in `understand_speech`, not a new tool.
- [ ] **`my_phrases`** — Polly, memory: one word says a saved sentence. "doctor" → "I'm not feeling well and I need a doctor."
- [ ] **`translate_for_me`** — Translate, Polly: the person speaks Arabic, and Alexa says it in English (for a doctor, for example).

### If there's time

- [x] **Rana — `emergency_sos`** — Telegram, Location, browser location: "I fell", "help help", "emergency". Instead of asking "yes", Alexa counts down 5 seconds ("say stop if you're okay"), then sends every helper a Telegram alert with the address and a map pin. Silence sends it. Helpers are added from the page and link themselves by opening the bot. Details: [feature-emergency-sos.md](branches/feature-emergency-sos.md).
- [ ] **`where_am_i`** — Location, browser location: says the current address (`ReverseGeocode`), then offers to send it to someone.
- [ ] **`share_location`** — SNS, browser location: "send Sara my location" sends the contact a map pin.
- [ ] **`find_nearby`** — Location, browser location: "nearest pharmacy?" answers with name, address and distance (`SearchNearby`).
- [ ] **`what_did_i_ask`** — memory only: "what did I ask for today?"
- [ ] **`say_it_for_me`** — Polly, brain: the person says it in pieces, and Alexa says it clearly to whoever is in front of them ("I need my blood pressure medicine").
- [ ] **`say_it_simpler`** — Polly, brain, memory: "I didn't understand". Alexa repeats her last reply in simpler, shorter words, and speaks it slower.

### Not now (timers or heavy setup)

- [ ] **`medication_reminder`** — timer, SNS: reminds at the set time. If they don't say "I took it" within 15 minutes, the caregiver is alerted. Every dose taken or missed is logged.
- [ ] **`safe_walk`** — timer, SNS, browser location: "going to the pharmacy, back in half an hour". If they don't say "I'm home" in time, the caregiver gets an alert.
- [ ] **`daily_summary`** — timer, SNS, brain: an evening message to the family: what was asked for, which medicines were taken or missed, and whether help was asked for.
- [ ] **`add_calendar_event`** — Google Calendar: "doctor tomorrow at ten" becomes a real event. Needs Google OAuth, the heaviest setup.
- [ ] **`read_medicine_box`** — Textract, Polly: the person photographs a medicine box, and Alexa reads the name and dose.

Timers can run as a background task inside the server (simple) or with EventBridge + Lambda (a bigger AWS integration).
