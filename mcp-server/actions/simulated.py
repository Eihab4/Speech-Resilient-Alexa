from memory import Request
from messages import ACTION_RESULTS, GENERIC_ACTION_RESULT


def perform(request: Request) -> str:
    template = ACTION_RESULTS.get(request.intent, GENERIC_ACTION_RESULT)
    try:
        return template.format(**request.details)
    except KeyError:
        return GENERIC_ACTION_RESULT
