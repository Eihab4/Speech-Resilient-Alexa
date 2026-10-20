from statistics import quantiles

from config.settings import PauseSettings
from memory import MemoryStore


def wait_from_pauses(pauses_ms: list[int], settings: PauseSettings) -> float | None:
    """How long to wait for someone with these pauses, or None until there are enough of them.

    Pauses over the limit don't count, outliers are dropped with the IQR rule, and the wait covers three in four
    of what's left, with a margin. The 75th percentile isn't pulled by one long pause the way an average is.
    """
    seconds = [ms / 1000 for ms in pauses_ms if 0 < ms <= settings.ignore_over_seconds * 1000]
    if len(seconds) < settings.min_samples:
        return None
    first, _, third = quantiles(seconds, n=4, method="inclusive")
    reach = 1.5 * (third - first)
    kept = [pause for pause in seconds if first - reach <= pause <= third + reach]
    _, _, usual = quantiles(kept, n=4, method="inclusive")
    return _within_limits(usual * settings.margin, settings)


def _within_limits(seconds: float, settings: PauseSettings) -> float:
    return round(min(max(seconds, settings.min_seconds), settings.max_seconds), 2)


class Pacing:
    """Learns how long each person pauses in the middle of a sentence, so Alexa waits for them, not for a
    fixed time. Until enough pauses are measured, each early answer (Alexa said "go on" and the person went on
    with the same request) adds a little to the wait."""

    def __init__(self, store: MemoryStore, settings: PauseSettings) -> None:
        self._store = store
        self._settings = settings

    def wait(self, company_id: str, user_id: str) -> float:
        return self._wait(company_id, user_id, answered_too_early=False)

    def learn(self, company_id: str, user_id: str, pauses_ms: list[int], answered_too_early: bool) -> float:
        if pauses_ms:
            self._store.add_pauses(company_id, user_id, pauses_ms)
        return self._wait(company_id, user_id, answered_too_early)

    def _wait(self, company_id: str, user_id: str, answered_too_early: bool) -> float:
        recent = self._store.recent_pauses(company_id, user_id, self._settings.keep)
        if (measured := wait_from_pauses(recent, self._settings)) is not None:
            return measured
        grown = self._store.pause_wait(company_id, user_id)
        wait = grown if grown is not None else self._settings.start_seconds
        if answered_too_early:
            wait = _within_limits(wait + self._settings.step_seconds, self._settings)
            self._store.save_pause_wait(company_id, user_id, wait)
        return _within_limits(wait, self._settings)
