from memory.context import render_turns
from memory.models import Summary
from memory.store import MemoryStore


class History:
    def __init__(self, store: MemoryStore, summarizer, recent_messages: int, summary_trigger_words: int) -> None:
        self._store = store
        self._summarizer = summarizer
        self._recent = recent_messages
        self._trigger = summary_trigger_words

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
