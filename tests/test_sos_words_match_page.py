import json
import re
from pathlib import Path

from messages import SOS_PHRASES

PAGE_WORDS = Path(__file__).resolve().parents[1] / "web" / "src" / "words.js"


def test_the_page_uses_the_same_sos_phrases_as_the_server():
    listed = re.search(r"SOS_PHRASES = Object\.freeze\((\[.*?\])\)", PAGE_WORDS.read_text()).group(1)

    assert tuple(json.loads(listed)) == SOS_PHRASES
