"""
Keyword safety screen for free-text check-in answers.

Deliberately errs towards flagging: a negated phrase ("I don't want to kill
myself") still matches, because a clinician reviewing a false alarm is far
cheaper than missing a real one. Works offline, so it runs even when the
remote mental-health classifier is not configured.
"""
from __future__ import annotations

import re

_SELF = [
    r"kill(ing)? my ?self", r"end(ing)? (it all|my life|things)", r"take my (own )?life",
    r"suicid(e|al)", r"want(ed)? to die", r"wish i (was|were) dead", r"better off dead",
    r"(hurt(ing)?|harm(ing)?|cut(ting)?|injur(e|ing)|burn(ing)?) my ?self", r"self[- ]?harm(ing)?",
    r"(don'?t|do not) want to (live|be alive|exist|wake up)", r"no reason to (live|go on)",
    r"can'?t go on",
]
_OTHERS = [
    r"(kill(ing)?|hurt(ing)?|harm(ing)?|attack(ing)?|stab(bing)?|shoot(ing)?) (him|her|them|someone|somebody|people|everyone|my \w+)",
    r"want to (hurt|harm|kill) (others|someone|somebody|people)",
]

_SELF_RE = re.compile(r"\b(" + "|".join(_SELF) + r")\b", re.IGNORECASE)
_OTHERS_RE = re.compile(r"\b(" + "|".join(_OTHERS) + r")\b", re.IGNORECASE)


def screen_text(text: str) -> dict:
    """Returns {"self": bool, "others": bool}."""
    text = (text or "").replace("’", "'")
    return {"self": bool(_SELF_RE.search(text)), "others": bool(_OTHERS_RE.search(text))}
