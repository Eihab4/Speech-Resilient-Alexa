# Memory Design

How our Alexa remembers what a person said, without getting slower as the conversation grows.

## The problem

People whose speech is slow or broken rarely say a request in one go. They pause, come back, correct themselves, or get interrupted and close the app. If Alexa forgets any of that, they have to start over, which is exactly what we promise will never happen.

But memory can't grow forever either. The more we send to the AI on every turn, the slower and more confused it gets, and every turn has to answer in under 2 seconds.

So memory has to do two things at once: **keep everything that matters** and **stay small**.

## What we remember

Everything is stored in one SQLite file, per user. SQLite needs zero setup, so judges can run the project on their own machine.

### 1. The request in progress

Every piece the person has said for the current request, exactly as heard, plus what we understood so far (task, details, what's missing).

- It is never cut or summarized. This is what makes "tomorrow… doctor… ten" work across three turns.
- It is saved after every change, so closing the app loses nothing.
- It is cleared when the request is done or cancelled.
- If the person leaves it unfinished, it stays for about a day. Next time, `resume_unfinished` offers to finish it. After that it expires, because "want to finish your reminder about pills?" feels strange a week later.

### 2. Conversation history, with a running summary

Past messages from finished requests, so references like "message her too" still work after "call mom".

When the history gets too long, the oldest part is turned into a short summary, and those messages are deleted. The AI then sees the summary plus the most recent messages, so the size stays about the same no matter how long the person talks.

How the summary works:

- It runs **after** Alexa has already replied, so the person never waits for it.
- It only summarizes finished requests, never the request in progress.
- The new summary is written from the old summary plus the messages being removed, so nothing important drops out between rounds.
- If the summary call fails, nothing is deleted. It simply tries again after the next turn.

### 3. Action log

A short record of everything Alexa did: "reminder set", "message sent to Ahmed", and so on.

- It lets Alexa answer "did you send it?"
- It feeds the X-ray panel, so judges can see what happened.
- Entries are deleted after a few days. We only keep what's useful.

### 4. Personal words

Shortcuts the person teaches Alexa, like "my pills" meaning blood pressure medicine (the `remember_word` tool).

- These are kept until the person removes them.
- Only the words that appear in what was just heard are sent to the AI, not the whole list.

## What the AI sees on every turn

1. The request in progress, with all its pieces.
2. The summary of older conversation.
3. The most recent messages.
4. Any personal words that match what was just said.

Contacts ("mom", "my sister") come from the demo profile file, not from memory.

## Settings

Every limit lives in an environment variable, so we can tune it without touching the code.

| Variable | What it controls | Starting value |
| --- | --- | --- |
| `MEMORY_DB_PATH` | Where the SQLite file lives | `data/memory.db` |
| `MEMORY_RECENT_MESSAGES` | How many recent messages the AI always sees in full | `10` |
| `MEMORY_SUMMARY_TRIGGER_WORDS` | How long the history can get before we summarize | `400` |
| `MEMORY_UNFINISHED_TTL_HOURS` | How long an unfinished request is kept | `24` |
| `MEMORY_HISTORY_TTL_HOURS` | How long history and its summary are kept | `24` |
| `MEMORY_ACTION_LOG_TTL_DAYS` | How long the action log is kept | `7` |

We measure history in words, not messages, because one long message can matter more than five short ones.

## How it fits in the code

Three small pieces, each with one job:

- **`MemoryStore`**: one interface for saving and loading memory, with two versions. The SQLite version is the real one. The in-memory version is for tests and mock mode. The brain only talks to the interface, so it never cares which one is behind it.
- **Context builder**: takes what's in memory and assembles exactly what the AI sees on this turn.
- **Summarizer**: shrinks old history in the background. In mock mode it's replaced by a fake that needs no AWS.

Keeping these separate means we can test each one on its own, and swap storage later (for example to AgentCore Memory) without touching the brain.

## Must-have vs. later

- **Must-have:** the request in progress, unfinished requests across sessions, and the action log. The demo depends on these.
- **Should-have:** history with the running summary, and personal words.

## How we'll know it works

- "tomorrow" / "doctor ten" / "yes" becomes one reminder across three turns.
- Close the app halfway, open it again, and Alexa offers to finish. A day later, it doesn't.
- "call mom" followed by "message her I'm late" sends the message to Mom.
- A 50-message conversation keeps what the AI sees small, and still resolves references.
- Every turn still answers in under 2 seconds.

## Ideas we considered and dropped

- **Keep everything.** Simple, but the AI gets slower and more confused as the chat grows.
- **Keep only the last N messages.** Too blunt. It can throw away something the person said early that still matters.
- **LRU cache.** Good for caches, but a conversation has an order that matters. The oldest part gets summarized instead of evicted.
- **A separate "who/when/what" memory.** Useful on its own, but the summary plus recent messages already tell the AI who "her" is. One mechanism instead of two.
- **Summarizing on every turn.** An extra AI call each time would break the 2-second target. Summarizing only when history gets long, and only in the background, avoids that.
- **Search with embeddings.** Overkill for this amount of data. Simple word matching is enough for personal words.
- **AgentCore Memory.** Needs AWS, so judges couldn't run the project without an account. It can come later behind the same `MemoryStore` interface.
