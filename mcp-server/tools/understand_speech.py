def understand(user_id: str, heard: str) -> dict:
    heard = heard.lower().strip()

    if "tomorrow" in heard and "doctor" in heard and "ten" in heard:
        return {
            "task": "reminder",
            "details": {
                "what": "doctor appointment",
                "when": "10:00 AM tomorrow"
            },
            "missing": [],
            "changed": [],
            "assumptions": ["ten means 10 AM"],
            "next_move": "confirm",
            "say": "Should I set a reminder for your doctor appointment tomorrow at 10 AM?"
        }

    if "doctor" in heard:
        return {
            "task": "reminder",
            "details": {
                "what": "doctor appointment"
            },
            "missing": ["when"],
            "changed": [],
            "assumptions": [],
            "next_move": "ask",
            "say": "What time?"
        }

    if "tomorrow" in heard:
        return {
            "task": "reminder",
            "details": {},
            "missing": ["what", "when"],
            "changed": [],
            "assumptions": [],
            "next_move": "ask",
            "say": "Mm-hm, go on."
        }

    return {
        "task": None,
        "details": {},
        "missing": ["task"],
        "changed": [],
        "assumptions": [],
        "next_move": "ask",
        "say": "What would you like me to do?"
    }