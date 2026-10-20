from memory import DayTries, MemoryStore
from messages import Reply


def speech_trend(store: MemoryStore, company_id: str, user_id: str, days: int) -> dict:
    trend = store.tries_per_day(store.conversation_for(company_id, user_id), days)
    return {"days": [day.model_dump() for day in trend], "say": _say(trend)}


def _say(trend: list[DayTries]) -> str:
    if not trend:
        return Reply.TREND_EMPTY
    first, last = trend[0], trend[-1]
    if first is last:
        return Reply.TREND_ONE_DAY.format(tries=f"{first.tries:g}")
    return Reply.TREND.format(first_tries=f"{first.tries:g}", first_day=first.day, last_tries=f"{last.tries:g}")
