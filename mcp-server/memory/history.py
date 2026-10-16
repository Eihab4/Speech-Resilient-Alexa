from threading import Lock, Thread, current_thread

from memory.context import render_turns
from memory.models import Summary
from memory.store import MemoryStore


class History:
    def __init__(self, store: MemoryStore, summarizer, recent_messages: int, summary_trigger_words: int) -> None:
        self._store = store
        self._summarizer = summarizer
        self._recent = recent_messages
        self._trigger = summary_trigger_words
        self._running: set[Thread] = set()
        self._running_lock = Lock()

    def maintain_later(self, conversation_id: int) -> None:
        """Tidies the history in the background, so the person never waits for a summary."""
        thread = Thread(target=self._maintain_and_forget, args=(conversation_id,), daemon=True)
        with self._running_lock:
            self._running.add(thread)
        thread.start()

    def _maintain_and_forget(self, conversation_id: int) -> None:
        try:
            self.maintain(conversation_id)
        finally:
            with self._running_lock:
                self._running.discard(current_thread())

    def wait(self, timeout: float | None = None) -> None:
        """Waits for tidy-ups still running, so the store isn't closed under them."""
        with self._running_lock:
            running = list(self._running)
        for thread in running:
            thread.join(timeout)

    def for_brain(self, conversation_id: int) -> str:
        summary = self._store.summary(conversation_id)
        turns = self._store.finished_turns(conversation_id, summary.covers_up_to_seq)
        return render_turns(summary.text, turns[-self._recent :])

    def maintain(self, conversation_id: int) -> None:
        summary = self._store.summary(conversation_id)
        older = self._store.finished_turns(conversation_id, summary.covers_up_to_seq)[: -self._recent or None]
        if len(render_turns("", older).split()) <= self._trigger:
            return
        text = self._summarizer.summarize(summary.text, older)
        self._store.save_summary(conversation_id, Summary(text=text, covers_up_to_seq=older[-1].seq))
