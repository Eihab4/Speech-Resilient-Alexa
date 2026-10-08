# Branch: feature/memory

This branch will give Alexa memory. Before adding memory, it lays a clean foundation, so everything after it uses the same config, enums and messages.

It starts from `feature/add-bedrock` (PR #4, still open), so it already includes the AI brain from that branch.

## What's done

### 1. `refactor: structure config`

All settings live in one place, `mcp-server/config/settings.py`, split into sections. Every value comes from an environment variable, and the default sits next to it.

| Section | Env prefix | Settings |
| --- | --- | --- |
| Server | `MCP_` | `NAME`, `TRANSPORT`, `HOST`, `PORT`, `PATH` |
| LLM | `LLM_` | `PROVIDER`, `MAX_TOKENS`, `TEMPERATURE` |
| Bedrock | `BEDROCK_` | `MODEL_ID`, plus `AWS_REGION` |
| OpenRouter | `OPENROUTER_` | `API_KEY`, `MODEL_ID`, `BASE_URL`, `TIMEOUT_SECONDS`, `APP_TITLE` |

- `.env.example` lists every setting. A test fails if a new setting is added without it.
- The old `OPENROUTER=` key name still works, so nobody's existing `.env` breaks.
- Values that were hardcoded in the brains (URL, timeout, temperature, title) moved into settings.
- Fixed a crash in `brain/bedrock.py`: it used `json` without importing it.
- Removed a duplicated `.env` block from `.gitignore`.

### 2. `feat: add enums`

Fixed values now live in `mcp-server/enums/` instead of loose strings.

| Enum | Values | Used by |
| --- | --- | --- |
| `LlmProvider` | `bedrock`, `openrouter` | settings, brain factory |
| `ChatRole` | `system`, `user` | both brains |
| `NextMove` | `listen`, `ask`, `confirm` | the brain result |

The brain factory is now a simple map from provider to brain class. Adding a new provider means one enum value and one brain class. A test fails if a provider has no brain.

### 3. `feat: centralize messages`

Every text the system produces lives in `mcp-server/messages/`.

| Module | What's in it |
| --- | --- |
| `errors.py` | `ErrorMessage`, every error text |
| `replies.py` | `Reply`, what Alexa says, like "Take your time. I'm still listening." |
| `prompts.py` + `prompts/*.txt` | `Prompt`, the AI prompts, read once and cached |

The prompt used to be loaded separately in each brain. Now both brains call `Prompt.UNDERSTAND_SPEECH.text`.

## Layout after this branch

```text
mcp-server/
  server.py
  config/      settings from env
  enums/       fixed values
  messages/    errors, replies, prompts
  brain/       the AI brains and the factory
  tools/       MCP tools
tests/         real tests, see below
```

## Tests

```bash
uv sync
uv run pytest
```

The tests use real things, not mocks:

- They start the **real MCP server** as a separate process on a free port and call it over Streamable HTTP, just like an agent would.
- They send a **real request to OpenRouter** with a bad key and check that our central error message comes back.
- They read the **real `.env.example`** and check it lists every setting.
- One test asks the **real AI** to understand "tomorrow / doctor / ten". It runs only when `OPENROUTER_API_KEY` is set and is skipped otherwise.

Current result: 14 passed, 1 skipped (no key yet).

## What the tests found

- Our server negotiates MCP protocol `2026-07-28` with a current client. The track needs `2025-11-25` or later, so we pass. The test checks for the minimum version, not an exact one.

## Missing or needs attention

1. **The server won't start without an OpenRouter key.** The default provider is `openrouter`, and the brain refuses to start without a key. Judges cloning the repo would hit this first. We need a mock provider that returns recorded answers. The plan already requires one.
2. **The AI result schema is not verified against a real model.** `NextMove` is now an enum, so the JSON schema sent to OpenRouter uses `$defs`/`$ref`. Some providers don't accept that in strict mode. The real-AI test will tell us once a key is set.
3. **The brain's result doesn't match our documented contract.** It returns `intent` where the docs say `task`. It has no `missing` and no `pending_id`. The AI picks the next move and writes Alexa's reply itself, while the design says our code decides both. This needs a decision with Rana before memory is built on top.
4. **No memory yet.** The brain only sees the latest piece, so "tomorrow" then "doctor ten" still don't combine. `user_id` is received but unused. Memory is the next set of commits.
5. **Bedrock is untested.** There are no AWS credentials yet, so only the OpenRouter path has been called for real.
6. **README is out of date.** It still tells people to look for a `hello_world` tool that no longer exists.
7. **Merge order.** This branch is built on PR #4. PR #4 should be merged into `dev` first, then this branch.
8. **Project-level items still missing:** a `LICENSE` (needed for a public repo), `docs/feedback-and-friction.md` (worth up to a 10% judging bonus), and the system design docs on `docs/system-design`, which aren't merged yet.

## What's needed from the team

- An `OPENROUTER_API_KEY` in each local `.env`, so the real-AI test runs.
- AWS credentials with Bedrock access, so we can test the Bedrock brain.
- A decision with Rana on the brain's result shape (point 3).
- Merging PR #4.

## Next commits on this branch

1. `feat: add sqlite memory store`: companies, users, conversations, turns, requests and actions.
2. `feat: remember conversation turns`: save every turn and send the history to the brain.
3. `feat: add confirm and cancel`: `do_confirmed_request` and `cancel_request`.
4. `feat: resume unfinished requests`: survive closing the app.
5. `feat: summarize long conversations`: a summary for long chats, with the full history kept.
6. `docs: update memory design`: sync the docs with what was built.
