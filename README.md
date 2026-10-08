# Speech-Resilient Alexa

An Alexa+ add-on for people whose speech is slow, comes out in pieces, or needs correcting. It keeps every piece heard, guesses the request, asks only for what's missing, and never acts without a yes.

## For judges

- Track: **Alexa+**, as a self-hosted **MCP server**.
- Transport: **Streamable HTTP** at `http://127.0.0.1:8000/mcp`.
- MCP spec: negotiates **2025-11-25 or later** (the test suite checks this).
- Where MCP is imported and called: `mcp-server/server.py`.
- Runs with **no AWS account and no API key**: the default `LLM_PROVIDER=mock` uses recorded answers.

## Run it

```bash
uv sync
cp .env.example .env
uv run python mcp-server/server.py
```

Then open MCP Inspector in another terminal and connect with **Streamable HTTP** to the URL above:

```bash
npx -y @modelcontextprotocol/inspector
```

## Try the demo in MCP Inspector

Call `understand_speech` three times for the same `user_id`:

| Turn | `heard`      | What comes back                                                   |
| ---- | ------------ | ----------------------------------------------------------------- |
| 1    | `tomorrow`   | `next_move: listen`, "Mm-hm, go on."                              |
| 2    | `doctor ten` | `next_move: confirm`, "Should I set a reminder for your doctor…?" |
| 3    | `yes`        | `next_move: done`, plus a `pending_id`                            |

Then call `do_confirmed_request` with that `pending_id`. You get "Done. Reminder set: doctor appointment, tomorrow 10:00."

Stop the server between turn 1 and turn 2, start it again, and the pieces are still there.

## Tools

| Tool                   | What it does                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| `understand_speech`    | Takes the exact words of one turn, adds them to earlier pieces, returns what was understood and the next move. |
| `do_confirmed_request` | Carries out a request. Refuses unless the person clearly said yes.                                     |
| `cancel_request`       | Drops the request in progress.                                                                         |
| `resume_unfinished`    | At the start of a session, offers back a request left unfinished last time.                            |

## Settings

Everything is read from environment variables. `.env.example` lists every setting with its default.

| Setting                        | What it controls                                                      |
| ------------------------------ | --------------------------------------------------------------------- |
| `LLM_PROVIDER`                 | `mock` (default, no key needed), `openrouter` or `bedrock`            |
| `MEMORY_DB_PATH`               | The SQLite file that holds memory                                     |
| `MEMORY_UNFINISHED_TTL_HOURS`  | How long an unfinished request is offered back                        |
| `MEMORY_RECENT_MESSAGES`       | How many recent messages the brain always sees in full                |
| `MEMORY_SUMMARY_TRIGGER_WORDS` | How long the history can get before older parts are summarized        |

To use a real model, set `LLM_PROVIDER=openrouter` and `OPENROUTER_API_KEY`, or `LLM_PROVIDER=bedrock` with AWS credentials.

## Tests

```bash
uv run pytest
uv run ruff check mcp-server tests
```

The tests start the real server over Streamable HTTP and talk to it like an agent would. Two tests call a real model and are skipped unless `OPENROUTER_API_KEY` is set.

## Layout

```text
mcp-server/
  server.py     the MCP server: tools, lifespan, MCP is called here
  config/       settings, all from environment variables
  enums/        fixed values: providers, moves, intents, statuses
  messages/     every text in one place: replies, errors, prompts, tool descriptions
  brain/        the LLM brain, the mock brain, the summarizer, one client per provider
  memory/       SQLite store, history and summaries
  actions/      simulated reminder, message and call
  tools/        one file per MCP tool
  utils/        ids and time
data/           recorded answers for mock mode
docs/           design notes
tests/          real tests over HTTP and a real SQLite file
```
