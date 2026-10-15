# Tasks

## Voice

- [x] **Rana — Voice input (speech → text):** a Speak button; each pause sends what was said as its own turn. The microphone streams to the server, which uses Amazon Transcribe. If Transcribe is unavailable, the browser's own speech recognition takes over (Chrome and Edge).
- [x] **Eihab — Voice output (text → speech):** Alexa reads every reply aloud with Amazon Polly (neural voice, Joanna by default) through the server's `POST /speak`, so the AWS keys never reach the browser. The browser's voice is the fallback. The microphone pauses while she talks, and **Mute Alexa** cuts her off.
- [ ] **Polly retry:** once Polly fails, the page stays on the robotic browser voice until it's reloaded. Try Polly again on the next reply instead (`../web/src/output.js`).
- [ ] **Rana — `learn_my_speech`:** keep a word list per person in SQLite (names from contacts, and corrections like "no, *Sara*"). Push it to a Transcribe custom vocabulary so Alexa learns their words. An update takes a few minutes to be ready, so keep using the old list until then.

## Memory

- [x] **Rana — New request in the middle of one:** when the person starts something different while a request is open, Alexa asks before switching ("Should I stop the doctor reminder and call Mom instead?"), so each request stays its own row. Details: [feature-new-request.md](branches/feature-new-request.md).
- [ ] **Rana — Usual requests (after the task above):** Alexa counts what the person asks for most and uses it to understand broken speech faster ("c… mom" → "Call Mom?"). Still asks for yes. Details: [feature-usual-requests.md](branches/feature-usual-requests.md).
- [ ] **Bug — `cancel` saved as an intent:** when the person cancels, the request is saved with `intent = "cancel"`, which isn't a valid intent (only reminder, message, call).

## New tools

Each tool is a new file in `../mcp-server/tools`, with its texts in `mcp-server/messages/`. Every action asks for "yes" first, except `emergency_sos`. Messages go out by Telegram or SMS (Amazon SNS) through one `notify(contact, text)` helper, so the tools don't care which channel is used.

### Setup (do first)

- [ ] **Telegram:** create a bot with BotFather, add `TELEGRAM_BOT_TOKEN` to settings, and a contacts list that maps names ("Sara", "my son") to chat ids.
- [ ] **AWS:** give the IAM user `speech-resilient-alexa` only what's used (SNS, Location). New accounts are in the SMS sandbox, so verify each demo phone number in the SNS console. Timers can run as a background task inside the server (simple) or with EventBridge + Lambda (bigger AWS integration).

### Tools

- [ ] **`share_location`:** "send Sara my location". The page gets the position from the browser, and the tool sends it to the contact as a map pin.
- [ ] **`ask_for_help`:** when the person says "help", or Alexa still hasn't understood after a few tries, the caregiver gets what was understood so far ("Dad is trying to set a reminder for the doctor tomorrow, the time is unclear").
- [ ] **`emergency_sos`:** "help!", "I fell", "emergency". Sends an urgent alert with the location right away, without asking "yes". The trigger words must be hard to say by accident.
- [ ] **`add_calendar_event`:** "doctor tomorrow at ten" becomes a real Google Calendar event. Needs Google OAuth (the heaviest setup), and the prompt needs today's date.
- [ ] **`where_am_i`:** says the current address (Location `ReverseGeocode`), then offers to send it to someone.
- [ ] **`find_nearby`:** "nearest pharmacy?" answers with name, address and distance (Location `SearchNearby`), and can text the directions.
- [ ] **`safe_walk`:** "going to the pharmacy, back in half an hour". If they don't say "I'm home" in time, the caregiver gets an alert with where they went and their last location.
- [ ] **`medication_reminder`:** reminds at the set time. If they don't say "I took it" within 15 minutes, the caregiver is alerted. Every dose taken or missed is logged.
- [ ] **`daily_summary`:** an evening SMS to the family: what was asked for, which medicines were taken or missed, and whether help was asked for.
- [ ] **`say_it_simpler`:** "I didn't understand". Alexa repeats her last reply in simpler, shorter words, and speaks it slower.
