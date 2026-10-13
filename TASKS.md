# Tasks

- [x] **Rana — Voice input (speech → text):** A "Speak" button uses the browser's speech recognition (Web Speech API). Each pause sends what was said as its own turn, so slow, broken-up speech reaches the server in pieces. Code: `web/src/voice.js`. Works in Chrome and Edge; other browsers fall back to typing.
- [ ] **Eihab — Voice output (text → speech):** Alexa reads every reply aloud with the browser's `speechSynthesis`. Free and on-device, no API key.
  - Speak `result.say` after each reply is shown, in `sendTurn` in `web/src/main.js`.
  - Put the speaking code next to the listening code in `web/src/voice.js` (for example a `speak(text)` export), and texts in `web/src/messages.js`.
  - Pause the microphone while Alexa is talking, or it will hear her and send her words as the user's turn.
  - Add a mute toggle, and use `SPEECH_LANG` from `web/src/config.js` for the voice.
  - Test in Chrome.
  - **Option, a better voice with Amazon Polly:** instead of the browser's robotic voice, use Polly's neural voices, which sound like real Alexa. It also counts for the AWS Builder mini challenge.
    - The AWS keys must stay on the server, so the browser can't call Polly itself. Add a small route on the MCP server (FastMCP's `@mcp.custom_route`, for example `POST /speech`) that takes the text, calls Polly `synthesize_speech` (`Engine="neural"`) and returns the mp3. The page plays it with an `<audio>` element.
    - The IAM user `speech-resilient-alexa` needs the `AmazonPollyReadOnlyAccess` policy first (today it is refused with "not authorized").
    - Keep the browser's `speechSynthesis` as the fallback when Polly fails, so the page still talks.

- [ ] **Rana — Voice input with Amazon Transcribe, and `learn_my_speech`:** replace the browser's speech recognition with Amazon Transcribe streaming. It is more accurate, and its **custom vocabulary** lets Alexa learn each person's own words (names, places, the way they say things), which the browser cannot do. It counts for the AWS Builder mini challenge.
  - [x] **Permissions first:** the IAM user `speech-resilient-alexa` needs `AmazonTranscribeFullAccess` (today it is refused with "not authorized"). Test that streaming works on the account before building on it.
  - [x] **Audio path:** the AWS keys must stay on the server, so the browser can't call Transcribe itself. The page captures the microphone (`getUserMedia`, 16 kHz PCM) and streams it to the MCP server over a WebSocket route. The server forwards it to Transcribe streaming (the `amazon-transcribe` Python package) and sends the text back.
  - [x] **Pieces:** Transcribe marks a result as final when the person pauses. Send each final result as its own turn, exactly like `web/src/voice.js` does today, and show partial results live in the text box.
  - [ ] **`learn_my_speech`:** keep a word list per person in memory (SQLite). Add to it when the person corrects something ("no, *Sara*"), and from the names in their contacts. Push the list to a Transcribe custom vocabulary and pass its name when streaming starts. Updating a vocabulary takes a few minutes before it's ready, so update it in the background and keep using the previous one until then.
  - [x] **Fallback:** keep the browser's Web Speech API for when Transcribe is unavailable, so the Speak button always works.
  - This is the hardest task here: get plain streaming working end to end first, then add the vocabulary.

## New tools

Each tool is a new MCP tool in `mcp-server/tools/`, registered in `mcp-server/server.py`, with its texts in `mcp-server/messages/`.

Messages to people go out by Telegram (free, needs the app) or SMS through Amazon SNS (works on any phone, which suits older families). Put sending behind one small `notify(contact, text)` helper, so the tools don't care which channel is used.

- [ ] **Telegram setup (do first, the other tools need it):** a bot created with BotFather, `TELEGRAM_BOT_TOKEN` in settings and `.env.example`, a small client that sends a message to a chat id, and a contacts list that maps names ("Sara", "my son") to Telegram chat ids.
- [ ] **`share_location` — send where I am to someone:** "send Sara my location". The web page gets the position from the browser (`navigator.geolocation`, the person allows it once) and passes it to the tool, which sends it to the contact on Telegram as a map pin. Asks for "yes" first, like every action.
- [ ] **`ask_for_help` — call in the caregiver:** when the person says "help", or Alexa still hasn't understood after a few tries, the caregiver gets a Telegram message with what was understood so far, for example: "Dad is trying to set a reminder for the doctor tomorrow, the time is unclear." The pieces heard are already in memory.
- [ ] **`emergency_sos` — urgent alert:** "help!", "I fell", "emergency". Sends an urgent Telegram alert with the location to the caregiver straight away. This is the one action that does not wait for "yes": in an emergency, asking first costs time. Make the words that trigger it clear and hard to say by accident.
- [ ] **`add_calendar_event` — add to Google Calendar:** "doctor tomorrow at ten" becomes a real event in the person's calendar. Needs a Google Cloud project, the Calendar API and OAuth (free, but the setup is the heaviest part). The brain must turn "tomorrow ten" into a real date and time, so the prompt needs today's date.
- [ ] **AWS setup (do first for the tools that use SNS, Location or timers):**
  - Attach to the IAM user `speech-resilient-alexa` only the policies used: `AmazonSNSFullAccess`, `AmazonLocationFullAccess`, and Scheduler if it's used. Test each service on the account before building on it (Bedrock had a new-account limit).
  - **SNS:** new accounts start in the SMS sandbox, so each phone number used in the demo must be verified in the SNS console first.
  - **Location:** use the Places API (`geo-places`: `ReverseGeocode`, `SearchNearby`), which needs no resource to be created.
  - **Timers and escalations:** the MCP server runs on localhost, so AWS cannot call back into it. Either run the timed checks inside the server (a background task started in the lifespan in `server.py`, reading due items from SQLite and sending through SNS), or move the whole check into AWS (EventBridge Scheduler → Lambda, with the state in DynamoDB). The first is much simpler; the second counts as a bigger AWS integration.
  - The person's position comes from the browser (`navigator.geolocation`, allowed once) and is passed to the tools that need it.
- [ ] **`where_am_i` — "where am I?":** turns the position into a spoken address with Location `ReverseGeocode` ("You're on Tahrir Street, near the pharmacy"), then offers to send it to someone. For someone who is lost or has early dementia.
- [ ] **`find_nearby` — "nearest pharmacy?":** Location `SearchNearby` from the person's position, answers with the name, address and distance, and offers to send the directions to their phone (an SMS with a maps link).
- [ ] **`safe_walk` — "going to the pharmacy, back in half an hour":** starts a timer with the place and the time. When the person is back they say "I'm home". If they don't confirm in time, the caregiver gets an alert with where they were going and their last known location. Remember to cancel the timer when they confirm.
- [ ] **`medication_reminder` — reminders for medicine:** at the set time Alexa reminds the person (and an SMS goes out). If they don't say "I took it" within 15 minutes, the caregiver gets an alert. Log every dose taken or missed in SQLite: `daily_summary` reads it.
- [ ] **`daily_summary` — the evening update for the family:** every evening, the caregiver gets a short SMS: what was asked for today, which medicines were taken or missed, and whether help was asked for. Build it from memory and the medication log; the LLM can write it in a few warm sentences.
- [ ] **`say_it_simpler` — "I didn't understand":** Alexa repeats her last reply in simpler, shorter words. The last reply is already in memory; ask the brain to rewrite it simply. If Polly is used for the voice, also speak it slower (SSML `<prosody rate="slow">`).
