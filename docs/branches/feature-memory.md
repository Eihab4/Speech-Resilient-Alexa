# Branch: feature/memory

This branch gives Alexa memory, on top of a clean foundation (config, enums, messages). It starts from `feature/add-bedrock` (PR #4), so it includes the AI brain from that branch, restructured.

The design is in [memory.md](../memory.md).

## Commits

| Commit                                | What it did                                                                                            |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `refactor: structure config`          | Settings in sections, every value from env, complete `.env.example`. Fixed a missing `import json`.    |
| `feat: add enums`                     | Providers, chat roles and next moves as enums instead of loose strings.                                |
| `feat: centralize messages`           | Errors, replies, prompts and tool descriptions in one `messages/` package.                             |
| `feat: add mock brain`                | `LLM_PROVIDER=mock` answers from `data/mock_answers.json`. It is the default, so the server starts with no key. |
| `feat: add sqlite memory store`       | `MemoryStore` interface and the SQLite implementation: companies, users, conversations, turns, requests, actions. |
| `feat: remember conversation turns`   | `understand_speech` loads earlier pieces, sends them to the brain and saves every turn. Store and brain live in the FastMCP lifespan. |
| `feat: add confirm and cancel`        | `do_confirmed_request`, `cancel_request`, yes/no words handled in code, simulated actions, `pending_id` in every reply. |
| `feat: resume unfinished requests`    | `resume_unfinished`, and unfinished requests expire after `MEMORY_UNFINISHED_TTL_HOURS`.               |
| `feat: summarize long conversations`  | One LLM client per provider shared by the brain and a summarizer. Long histories are summarized in the background. Nothing is deleted. |

## Tests

```bash
uv run pytest
uv run ruff check mcp-server tests
```

59 tests pass, 2 are skipped without `OPENROUTER_API_KEY`. They use real things:

- The real MCP server, started as a separate process on a free port and called over Streamable HTTP.
- A real SQLite file, including stopping the server and starting it again on the same file.
- A real request to OpenRouter with a bad key, to check the central error message.
- A real model for interpreting and summarizing, when a key is present.

Every demo scenario from the plan runs end to end over MCP: the broken reminder, the change of mind, the missing piece and the comeback.

## Decisions made on this branch

- **Mock is the default provider.** Judges clone, run and see it work. Real models are one setting away.
- **Code decides yes and no.** The server marks a request confirmed when the person says a yes-word while Alexa was confirming. The LLM never gets to decide that an action happens.
- **Tool descriptions are messages.** They live in `messages/tools.py` and are passed to `@mcp.tool(description=...)`, so an agent reads clear instructions and no docstrings are needed.
- **The company comes from settings.** `MEMORY_COMPANY_ID` is a stand-in for the company that authentication will provide later.
- **Summaries never replace history.** Turns stay in the database; the summary only shortens what the brain reads.

## Still open

1. **The brain's result shape.** It returns `intent` where the plan says `task`, and there is no `missing` list. The AI also writes `say` and picks `next_move` for non-yes/no turns. Aligning this with the plan is a separate change to agree with Rana.
2. **`NextMove.DONE` is in the LLM schema.** Code is the only thing that should produce `done`. Harmless today, but the brain schema could expose a narrower enum.
3. **Bedrock is untested.** No AWS credentials yet, so only the OpenRouter client has been called for real.
4. **OpenRouter strict JSON schema with `$defs`.** Verified by hand only once a key is set (the skipped test will tell us).
5. **Background summaries share one SQLite connection across threads.** Fine for the demo load; a connection per thread would be the production answer.
6. **No `LICENSE` and no `docs/feedback-and-friction.md` yet.** Both are needed for submission.
7. **`docs/system-design` is not merged.** Its `memory.md` is older than this branch's; keep this one when merging.
8. **Merge order.** PR #4 (`feature/add-bedrock`) first, then this branch into `dev`.

## What's needed from the team

- An `OPENROUTER_API_KEY` in a local `.env`, so the two real-model tests run.
- AWS credentials with Bedrock access.
- Rana's decision on the result shape (point 1).
