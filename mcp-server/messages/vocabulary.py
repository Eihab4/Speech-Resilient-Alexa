YES_WORDS = frozenset(
    {"yes", "yeah", "yep", "yup", "mm-hm", "mhm", "right", "sure", "okay", "ok", "that's it", "do it"}
)
NO_WORDS = frozenset({"no", "nope", "no no", "nah", "wrong"})
# Said when the person is in danger. Matched anywhere in a piece, because the speech is often broken
# ("uh… i fell… floor"). "help" alone is not here: it takes two of them, see tools/emergency_sos.py.
SOS_PHRASES = ("i fell", "i fall", "fell down", "emergency", "sos", "ambulance")
HELP_WORDS = frozenset({"help", "help me", "i need help", "get help"})
# Said during the countdown to stop the alert. Matched as the whole piece, because "okay" alone is a yes.
# "no" is left out on purpose: a missed stop only sends an alert, a wrong stop leaves someone without help.
STOP_WORDS = frozenset(
    {"stop", "i'm okay", "im okay", "i'm ok", "im ok", "i'm fine", "im fine", "cancel", "never mind", "don't send"}
)
