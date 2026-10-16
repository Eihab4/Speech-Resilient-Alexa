# Devpost submission: text to paste

The text for each step of the submission form, in English as the rules ask. Edit anything that doesn't sound like you. Lines starting with **TODO** need something only you know.

Deadline: **Friday 23 October 2026, 12:00 PM Pacific = 10:00 PM Cairo.**

---

## Step: Project overview

**Project name** (60 characters max). Pick one:

- `Say It Your Way: Alexa+ for people with broken speech` (53)
- `Speech-Resilient Alexa` (22)

**Elevator pitch** (200 characters max, this one is 192):

> An Alexa+ MCP add-on for people whose speech is slow or broken. It keeps every piece they say, asks only for what's missing, never acts without a yes, and alerts family when they say 'I fell'.

**Thumbnail:** 3:2, JPG or PNG, 5 MB max. **TODO:** a screenshot of the page with the red SOS countdown, or a crop of `docs/architecture.png`.

---

## Step: Project details

### About the project

**Inspiration**

People recovering from a stroke, living with Parkinson's, aphasia or a stammer often speak slowly, in pieces, and correct themselves halfway. Voice assistants are built for one clean sentence: a pause ends the request, the pieces are lost, and the person has to start over. The people who need a voice assistant the most are the ones it understands the least.

**What it does**

Speech-Resilient Alexa is an Alexa+ add-on, built as a self-hosted MCP server.

- **Keeps every piece.** "Tomorrow…", then "doctor…", then "ten" become one request: a reminder for the doctor tomorrow at 10:00. Corrections like "no, Mom" change only that part.
- **Asks only for what's missing**, and never acts without a clear yes.
- **Remembers across sessions.** Close the app halfway, and next time Alexa offers to finish the request instead of making the person repeat it. Older history is summarized so the brain stays fast.
- **Knows a new request from a correction.** "Call Mom" in the middle of a reminder makes Alexa ask before switching, so nothing gets merged or lost.
- **Emergency SOS.** "I fell", "help help" or "emergency" start a 5-second countdown. "Stop" cancels it; silence sends it, so someone who fell and can't speak still gets help. Their helpers get a Telegram message with the street address from Amazon Location and a map pin.
- **Talks back** in a natural Amazon Polly voice, and listens through Amazon Transcribe.

**How we built it**

- An **MCP server** in Python with FastMCP, over Streamable HTTP, MCP spec 2025-11-25. Five tools: `understand_speech`, `do_confirmed_request`, `cancel_request`, `resume_unfinished`, `emergency_sos`.
- An **LLM brain** (Groq; Amazon Bedrock wired in) with structured output, plus fixed word lists checked first, so yes, no, SOS and stop work even when the LLM is down.
- **Memory in SQLite**: every turn, the request in progress, a rolling summary, an action log, and the people who get emergency alerts.
- **AWS**: Amazon Transcribe streaming for speech in, Amazon Polly neural voice for speech out, Amazon Location `ReverseGeocode` for the alert's address. All behind the server, so AWS keys never reach the browser.
- A **web page** that simulates the Alexa+ host: it streams the mic, sends one turn per pause, speaks the replies, and runs the SOS countdown.
- **Telegram Bot API** for alerts: a helper links themselves by opening a link and pressing Start.
- **156 Python tests and 34 web tests**, all running against the real server over HTTP, with a recorded mock brain, a fake Telegram and a fake Amazon Location, so they need no keys or network.

**Challenges we ran into**

- **Telling a correction from a new request.** With broken speech, "no, Mom" and "call Mom" sound alike. We stopped guessing: Alexa asks before switching.
- **The microphone hearing Alexa.** We pause the mic while she talks, and start the SOS countdown only after she finishes, otherwise there's no time to say "stop".
- **Amazon Bedrock stayed closed to our account** (see the friction log), so we moved the brain to Groq's free tier and kept Bedrock as a provider in the code.
- **SMS to Egypt needs a registered sender ID**, so emergency alerts go through Telegram, behind one `notify()` so SMS can be added later.

**Accomplishments that we're proud of**

- A request said in five broken pieces, across a restart, still ends up as one correct reminder.
- The SOS works with no LLM at all, and the alert reaches a real phone with a real address.

**What we learned**

- Speech accessibility is mostly about patience and memory, not a better speech model.
- Asking one more question is cheaper than one wrong action.

**What's next**

- Usual requests: learn what each person asks for most, so "c… Mom" becomes "Call Mom?" faster.
- A per-person Transcribe custom vocabulary (names, corrections).
- Yes/no mode after a few failed tries, and noticing frustration with Amazon Comprehend.
- Running on a real Alexa+ device.

### Built with

`python` `fastmcp` `model-context-protocol` `starlette` `uvicorn` `pydantic` `sqlite` `javascript` `vite` `amazon-transcribe` `amazon-polly` `amazon-location-service` `aws-iam` `boto3` `amazon-bedrock` `groq` `telegram-bot-api`

### Try it out

- **TODO:** the GitHub repository URL.

### Video demo link

- **TODO:** the YouTube or Vimeo link (public, under 3 minutes, English).

---

## Step: Additional info

**Track:** Alexa+ (self-hosted MCP server, MCP 2025-11-25 over Streamable HTTP; the browser page simulates the Alexa+ host).

**Mini challenges:** AWS Builder. Also Open Source, only if you make the extra open-source contribution (a new repo, or a pull request to an existing one).

**Repository access. TODO, pick one:**

- Public: add an open-source license (for example MIT) so it shows in the repo's About section.
- Private: add `chris-trag`, `knmeiss`, `giolaq`, `anishamalde`, `mosesroth` and `emersonsklar` as collaborators, and share it with testing@devpost.com.

**How the project was significantly updated during the hackathon:** **TODO** if the form asks. The first commit is from 2026-09-27, inside the submission period (31 August to 23 October).

### Product feedback

**Which developer tools, APIs and SDKs did you use, and for what?**

- **Model Context Protocol** (FastMCP, Streamable HTTP, spec 2025-11-25): the whole add-on is an MCP server with five tools; the web page is a plain MCP client.
- **Amazon Transcribe** (streaming, `amazon-transcribe` Python SDK): live speech to text, relayed through a server WebSocket so AWS keys stay on the server.
- **Amazon Polly** (neural voice, `boto3`): Alexa's spoken replies.
- **Amazon Location Service** (`geo-places` `ReverseGeocode`, `boto3`): the street address in emergency alerts.
- **AWS IAM**: one user with only the permissions the app uses.
- **Amazon Bedrock** (Converse API, Nova Lite): wired in as the brain; blocked on our account (see below).
- **Telegram Bot API**: delivering emergency alerts and linking helpers.
- **Groq** (OpenAI-compatible API): the LLM brain we could actually use.

**What worked well?**

- **Transcribe streaming** worked with a real voice once the IAM policy was attached, and its per-pause results map naturally onto "one turn per piece".
- **Polly** is simple: one call, a natural neural voice, MP3 straight to the browser.
- **Amazon Location** `ReverseGeocode` answered in 0.2 to 0.8 seconds for points in Cairo, with readable English street addresses.
- **MCP over Streamable HTTP** let the same server serve MCP Inspector, our web page and an AI host with no changes.

**What needs work?**

- **Bedrock access for new accounts**: "account is currently being verified", then "Operation not allowed" for every model, and a quota increase denied twice. Nothing in the console said why or for how long.
- **Finding the right IAM permission for Amazon Location**: searching for "geospatial" leads to SageMaker policies; the actions live under `geo-places`, and we wrote an inline policy by hand.
- **SMS to Egypt** needs a registered sender ID with company papers; not workable for an individual developer.
- The `ReverseGeocode` label sometimes starts with a nearby place ("Open Air Market, Tahrir Square, Cairo") rather than the street.

**How was your onboarding experience (zero to hello world)?**

- **TODO:** how long each one took you. What we know:
- MCP: the spec and MCP Inspector made the first tool quick to test.
- Transcribe, Polly and Location: the code was short; most of the time went into finding the right IAM permission.
- Bedrock: we never reached hello world.

**Would you build with these devices and services again?**

Yes. Transcribe, Polly and Location did exactly what an accessibility product needs, and MCP made the add-on portable across hosts. We'd want Bedrock open to new accounts so the brain can run on AWS too.

**AWS Builder: which AWS services did you use, and how?**

Speech comes in through **Amazon Transcribe** streaming, relayed by the MCP server's `/transcribe` WebSocket. The MCP tools understand it, and every reply is spoken with **Amazon Polly** through `/speak`. In an emergency, **Amazon Location Service** `ReverseGeocode` turns the device's coordinates into a street address for the helper's alert. All three run on the server under one IAM user with only the permissions they need; the integrations are documented in the README's "AWS services" section, with the code paths and IAM permissions. **Amazon Bedrock** (Nova Lite) is wired in as an alternative brain but was blocked on our account.

### Friction log

Entries 1 to 4 come from what happened while building. **TODO:** add your own with the template at the end.

**1. Amazon Bedrock: no model could be called**

- **Task:** use Nova Lite through the Converse API as the add-on's brain.
- **Steps:** attached `AmazonBedrockFullAccess` to the IAM user, called Converse in `us-east-1`, and opened a support case for a quota increase.
- **Expected:** a response from Nova Lite.
- **Actual:** first "AccessDeniedException: Your account is currently being verified", then "ValidationException: Operation not allowed" for Nova Lite and Micro, Llama 3.3 and gpt-oss. An AWS email said the applied Nova 2 Lite quota was 0, and the quota request was denied twice. Anthropic models were refused for our country.
- **Severity:** Critical. It blocked our planned AWS brain.
- **Workaround:** moved the brain to Groq's free tier and kept Bedrock as a provider in the code.
- **Suggestion:** show the account's verification state and per-model quota in the Bedrock console, with an expected date; give hackathon participants a small default quota.

**2. Amazon SNS: SMS to Egypt**

- **Task:** send an emergency alert to a helper by SMS.
- **Steps:** while planning SMS alerts, read the SNS SMS and AWS End User Messaging docs for Egypt.
- **Expected:** send to a verified number from the SMS sandbox.
- **Actual:** Egypt needs a registered sender ID with a letter of authorization and company documents, and new accounts are capped at $1 a month of SMS.
- **Severity:** High for an alerts feature.
- **Workaround:** Telegram Bot API, behind one `notify()` so SMS can come back later.
- **Suggestion:** let the SMS sandbox send to verified numbers in every country, and list each country's registration needs on one page at the start of the docs.

**3. IAM: finding the permission for Amazon Location**

- **Task:** let the app's IAM user call `ReverseGeocode`.
- **Steps:** searched the IAM managed policies for "geospatial" and attached `AmazonSageMakerGeospatialFullAccess` and `AmazonSageMakerGeospatialExecutionRole`.
- **Expected:** a clearly named policy for Amazon Location Service.
- **Actual:** those policies belong to SageMaker geospatial, not Amazon Location; the calls we needed are under the `geo-places` prefix, which we only found in the API docs.
- **Severity:** Medium.
- **Workaround:** an inline policy allowing `geo-places:ReverseGeocode`.
- **Suggestion:** show Amazon Location Service when searching IAM for "location" or "geospatial", and link a ready policy from each Location API page.

**4. IAM console: two error messages for one problem**

- **Task:** save the inline policy.
- **Steps:** entered a policy name with characters that aren't allowed, then pressed Create policy.
- **Expected:** a message pointing at the character that isn't allowed.
- **Actual:** "The specified value for policyName is invalid…" and "Policy name is required" at the same time, without saying which character was wrong.
- **Severity:** Low.
- **Workaround:** typed the name by hand.
- **Suggestion:** highlight the invalid characters instead of saying the name is missing.

**Template for more entries**

- **Task:**
- **Steps:**
- **Expected:**
- **Actual:**
- **Severity:** Critical / High / Medium / Low
- **Workaround:**
- **Suggestion:**

---

## Video plan (under 3 minutes)

1. **0:00 to 0:20, the problem.** A person speaks in pieces; a normal assistant gives up after the first pause.
2. **0:20 to 1:10, broken speech.** Say "tomorrow…", "doctor…", "ten" with pauses: live captions from Transcribe, Alexa's Polly voice asks "Should I set a reminder…?", "yes", done. Then a correction: "call Sara", "no, Mom".
3. **1:10 to 1:30, memory.** Stop halfway, restart, and Alexa offers to finish the request.
4. **1:30 to 2:30, SOS.** Say "I fell": the red countdown. Stay silent: a teammate's phone gets the Telegram alert with the street address and the map pin. Then "help help" and "stop": nothing is sent.
5. **2:30 to 2:55, how it's built.** The architecture picture: MCP server, Transcribe, Polly, Location.

Keep the camera on the message on the phone, not on app logos, and use no copyrighted music.
