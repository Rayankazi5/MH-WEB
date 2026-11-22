"""
Guardrailed insight chat — Section 4 of the algorithmic spec.
Keyword-driven navigation grounded entirely in the patient's own scoring data.
Claude is constrained to 3-4 sentences and one actionable suggestion per response.
"""
from __future__ import annotations
from typing import Optional

INSIGHT_SYSTEM_PROMPT = """You are a warm, supportive wellness companion helping a user understand patterns in their own behavioral data from a mental health tracking app.

STRICT RULES:
1. You are NOT a therapist. Never attempt diagnosis, clinical interpretation, or treatment advice.
2. Ground EVERY statement in the specific data provided in the user message. Do not add speculation or general wellness advice not supported by the data.
3. Use warm, first-person-supportive language directed at the user ("Your data shows...", "It looks like this week...", "You seem to have...").
4. Keep the response to exactly 3-4 sentences.
5. End with one gentle, concrete, actionable suggestion directly tied to the data.
6. If data for the requested area is insufficient or absent, acknowledge that warmly and suggest completing more check-ins.
7. Never use clinical jargon (no "depressive symptoms", "anxiety disorder", "pathology"). Use plain everyday language.
8. Never mention scores, weights, percentages, or model internals. Translate numbers into natural observations.
9. Never reveal that you are an AI language model or describe the underlying system.
"""

# Maps user-facing keyword to the relevant patient-type scores and questionnaire items.
# Safety items are deliberately not described back to the patient here.
KEYWORD_CONFIG = {
    "sleep": {
        "label": "Your Sleep & Eating",
        "domains": [],
        "indicators": ["sleep_hours", "meals_per_day"],
    },
    "mood": {
        "label": "Your Mood",
        "domains": ["depressive"],
        "indicators": ["ref_numb", "ref_not_worthy", "ref_no_excitement", "sentiment"],
    },
    "anxiety": {
        "label": "Your Worries",
        "domains": ["anxious"],
        "indicators": ["ref_thoughts_anxious", "ref_thoughts_scary"],
    },
    "energy": {
        "label": "Your Energy & Motivation",
        "domains": ["depressive"],
        "indicators": ["ref_start_finish", "ref_no_excitement", "ref_cant_change_behaviour"],
    },
    "thoughts": {
        "label": "Your Thoughts & Memories",
        "domains": ["obsessive", "trauma"],
        "indicators": ["ref_thoughts_repetitive", "ref_thoughts_unwanted", "ref_flashbacks"],
    },
    "social": {
        "label": "Your Relationships",
        "domains": ["interpersonal"],
        "indicators": ["ref_loneliness", "ref_no_one_to_rely_on", "ref_disapproval", "ref_harmful_relationships"],
    },
    "overall": {
        "label": "Your Overall Week",
        "domains": ["depressive", "anxious", "obsessive", "trauma", "interpersonal"],
        "indicators": ["sleep_hours", "meals_per_day", "ref_loneliness", "ref_thoughts_anxious", "sentiment"],
    },
}

# Patient-facing (non-clinical) names for each patient type.
DOMAIN_LABELS = {
    "depressive": "mood and motivation",
    "anxious": "worry and anxious thoughts",
    "obsessive": "repetitive or unwanted thoughts",
    "trauma": "upsetting memories",
    "interpersonal": "relationships and connection",
}

# How each questionnaire item reads back to the patient.
ITEM_PHRASES = {
    "ref_thoughts_anxious": "anxious or worried thoughts",
    "ref_thoughts_repetitive": "the same thoughts repeating",
    "ref_thoughts_unwanted": "unwanted thoughts",
    "ref_thoughts_scary": "frightening thoughts",
    "ref_loneliness": "feeling lonely",
    "ref_numb": "feeling numb",
    "ref_no_one_to_rely_on": "feeling there's no one to rely on",
    "ref_not_worthy": "feeling not worthy",
    "ref_disapproval": "feeling others disapprove of you",
    "ref_harmful_relationships": "staying in relationships that feel harmful",
    "ref_cant_change_behaviour": "finding it hard to change a habit",
    "ref_consequences": "your thoughts or actions causing problems",
    "ref_no_excitement": "nothing feeling exciting",
    "ref_start_finish": "trouble starting or finishing things",
    "ref_flashbacks": "flashbacks or upsetting memories",
}

SAFETY_KEYS = ("ref_self_harm", "ref_thoughts_harm_others", "ref_hopelessness")

_REASON_BY_KEY = {"ref_self_harm": "self", "ref_thoughts_harm_others": "others", "ref_hopelessness": "hopeless"}


def safety_note(reasons) -> Optional[str]:
    """Support line naming only what the patient reported ("self", "others", "hopeless")."""
    reasons = set(reasons or [])
    targets = [t for r, t in (("self", "yourself"), ("others", "someone else")) if r in reasons]
    parts = []
    if "hopeless" in reasons:
        parts.append("feeling hopeless")
    if targets:
        parts.append("having thoughts of harming " + " or ".join(targets))
    if not parts:
        return None
    return (f"If you're {' or '.join(parts)}, please reach out to your clinician or a local crisis "
            "line right away — you don't have to handle this alone.")

# Answer labels for the 0–3 questionnaire items, as read back to the patient
PHQ_LABELS = ["not at all", "on several days", "more than half the days", "nearly every day"]


def _describe_score(score: float, domain: str) -> str:
    label = DOMAIN_LABELS.get(domain, domain)
    # Scores are absolute 0–1; 0.33 ≈ an average answer of "several days".
    if score < 0.15:
        return f"there's no significant concern around {label} right now"
    elif score < 0.33:
        return f"there are some mild signs around {label} worth keeping an eye on"
    elif score < 0.6:
        return f"there's noticeable strain around {label} lately"
    else:
        return f"the main area of strain right now is {label}"


def _describe_indicator(key: str, value) -> Optional[str]:
    if key == "sleep_hours":
        try:
            return f"averaging {float(value):g} hours of sleep per night"
        except (TypeError, ValueError):
            return None
    if key == "meals_per_day":
        try:
            return f"eating about {float(value):g} meals a day"
        except (TypeError, ValueError):
            return None
    if key == "sentiment":
        try:
            s = float(value)
            if s < 0.35:
                return "journal entries with a generally positive tone"
            elif s < 0.6:
                return "journal entries with a mixed emotional tone"
            else:
                return "journal entries with a notably heavy or distressed tone"
        except (TypeError, ValueError):
            return None
    if key in ITEM_PHRASES and value is not None:
        try:
            idx = int(value)
            if 1 <= idx <= 3:
                return f"{ITEM_PHRASES[key]} {PHQ_LABELS[idx]}"
        except (TypeError, ValueError):
            return None
    return None


def build_insight_prompt(keyword: str, domain_scores: dict, indicators: dict, trend: Optional[str]) -> str:
    config = KEYWORD_CONFIG.get(keyword, KEYWORD_CONFIG["overall"])
    topic = config["label"]

    domain_descriptions = [
        _describe_score(domain_scores.get(d, 0.0), d)
        for d in config["domains"]
        if d in domain_scores
    ]

    indicator_descriptions = [
        desc
        for k in config["indicators"]
        if k in indicators and (desc := _describe_indicator(k, indicators[k])) is not None
    ]

    domain_text = "; ".join(domain_descriptions) if domain_descriptions else "insufficient data available"
    indicator_text = ", ".join(indicator_descriptions) if indicator_descriptions else "no specific indicators recorded"
    trend_text = f" The trend compared to last week is: {trend}." if trend else ""

    return (
        f"The user wants to understand: {topic}.\n\n"
        f"AREA SUMMARY: {domain_text}.{trend_text}\n"
        f"SPECIFIC INDICATORS (raw values — treat these as the ground truth for actual quality): {indicator_text}.\n\n"
        f"When domain summary and specific indicators conflict, always trust the specific indicators. "
        f"Provide a warm, data-grounded 3-4 sentence insight about the user's {topic.lower()} patterns "
        f"based strictly on the above data. End with one actionable suggestion."
    )


def build_vent_prompt(free_text: str, domain_scores: dict) -> str:
    if not domain_scores:
        return (
            f"The user has shared the following: \"{free_text}\"\n\n"
            "No scoring data is available. Respond warmly and empathetically in 3-4 sentences. "
            "Acknowledge what they shared and offer one gentle suggestion."
        )
    most_strained = max(domain_scores, key=domain_scores.get)
    context = _describe_score(domain_scores[most_strained], most_strained)
    return (
        f"The user has shared the following in their own words: \"{free_text}\"\n\n"
        f"Their data context (do not quote directly): {context}.\n\n"
        "Respond warmly and empathetically in 3-4 sentences, acknowledging what they shared "
        "and connecting it gently to their data if appropriate. End with one supportive suggestion."
    )


_SUGGESTIONS = {
    "sleep": [
        "Your sleep looks solid — keep the routine you have going.",
        "Try winding down 30 minutes before bed without screens to improve sleep quality.",
        "A consistent sleep and wake time, even on weekends, can significantly improve rest.",
    ],
    "mood": [
        "Your mood appears relatively stable — keep the habits that are working for you.",
        "A 5-minute daily note about one positive moment can help anchor mood over time.",
        "Journaling, even briefly, can help you spot patterns before they deepen.",
    ],
    "anxiety": [
        "Your anxiety levels look manageable — note what's helping you stay calm.",
        "Physical activity, even a 10-minute walk, can reduce anxiety throughout the day.",
        "When tension rises, the 5-4-3-2-1 grounding method (name things you can see, hear, touch) can help.",
    ],
    "energy": [
        "Your energy and focus appear to be in a good place — keep it up.",
        "Staying hydrated and getting natural light during the day supports focus and energy.",
        "Breaking tasks into smaller pieces with short breaks every 45 minutes can help on low-energy days.",
    ],
    "thoughts": [
        "Your thoughts seem fairly settled lately — notice what helps you feel that way.",
        "When a thought keeps looping, writing it down can help you put it aside for a while.",
        "If upsetting memories or thoughts keep coming back, it can really help to talk them through with your clinician.",
    ],
    "social": [
        "Your social engagement looks healthy — keep investing in the relationships that matter.",
        "Even a quick check-in text to a friend can maintain connection when face-to-face feels hard.",
        "Scheduling one social activity this week, however small, can meaningfully boost how connected you feel.",
    ],
    "overall": [
        "Keep checking in regularly — patterns become clearer with more data over time.",
        "Small, consistent habits tend to have more impact than large one-off changes.",
        "When one area feels strained, addressing it early — even with a small step — usually helps the rest.",
    ],
}


def _indicator_concern_score(keyword: str, indicators: dict) -> float:
    """
    Compute a 0-1 concern estimate directly from raw indicator values.
    Used to select the appropriate tip when area scores
    would otherwise understate a genuinely poor pattern.
    """
    kw = keyword if keyword in KEYWORD_CONFIG else "overall"
    config = KEYWORD_CONFIG[kw]
    concerns = []
    for key in config["indicators"]:
        val = indicators.get(key)
        if val is None:
            continue
        try:
            if key == "sleep_hours":
                from app.engine.scoring import normalise_sleep_concern
                concerns.append(normalise_sleep_concern(float(val)))
            elif key == "meals_per_day":
                from app.engine.scoring import normalise_meals_concern
                concerns.append(normalise_meals_concern(float(val)))
            elif key in ITEM_PHRASES:
                concerns.append(max(0.0, min(1.0, int(val) / 3.0)))
        except (TypeError, ValueError):
            pass
    return sum(concerns) / len(concerns) if concerns else 0.0


def _rule_based_insight(keyword: str, domain_scores: dict, indicators: dict,
                        trend: Optional[str]) -> str:
    kw = keyword if keyword in KEYWORD_CONFIG else "overall"
    config = KEYWORD_CONFIG[kw]
    relevant_domains = [d for d in config["domains"] if d in domain_scores]

    indicator_descs = [
        desc for k in config["indicators"]
        if k in indicators and (desc := _describe_indicator(k, indicators[k])) is not None
    ]

    if not relevant_domains and not indicator_descs:
        return (
            f"Complete a daily check-in to start seeing insights about {config['label'].lower()}. "
            "Your data builds up over time and makes these insights more meaningful."
        )

    avg_score = (
        sum(domain_scores[d] for d in relevant_domains) / len(relevant_domains) if relevant_domains else 0.0
    )

    if relevant_domains:
        domain_descs = [_describe_score(domain_scores[d], d) for d in relevant_domains]
        main = "Based on your recent check-ins, " + " and ".join(domain_descs) + "."
    else:
        main = "Here's what your recent check-ins show."

    if indicator_descs:
        main += " Your data shows " + " and ".join(indicator_descs[:2]) + "."

    if trend:
        main += f" Compared to the previous period, things appear to be {trend}."

    # Take the more conservative of the area score and the raw-answer concern.
    indicator_concern = _indicator_concern_score(kw, indicators)
    effective_score = max(avg_score, indicator_concern)

    suggestions = _SUGGESTIONS.get(kw, _SUGGESTIONS["overall"])
    if effective_score >= 0.55:
        tip = suggestions[2]
    elif effective_score >= 0.35:
        tip = suggestions[1]
    else:
        tip = suggestions[0]

    return main + " " + tip


def _rule_based_vent(free_text: str, domain_scores: dict) -> str:
    if not domain_scores:
        return (
            "Thank you for sharing that. It takes courage to put your feelings into words. "
            "Try to be gentle with yourself — what you're feeling is valid. "
            "If these feelings persist, consider speaking with someone you trust or a mental health professional."
        )
    most_strained = max(domain_scores, key=domain_scores.get)
    context = _describe_score(domain_scores[most_strained], most_strained)
    return (
        f"Thank you for sharing that. Your check-in data reflects that {context}, "
        "and what you've written aligns with that. "
        "It's useful to notice these patterns — awareness is often the first step. "
        "Be gentle with yourself, and consider reaching out to someone you trust if things feel heavy."
    )


def _reasons_from_answers(indicators: dict) -> list:
    out = []
    for k in SAFETY_KEYS:
        try:
            if float(indicators.get(k, 0) or 0) > 0:
                out.append(_REASON_BY_KEY[k])
        except (TypeError, ValueError):
            continue
    return out


def run_insight_chat(keyword: Optional[str], free_text: Optional[str],
                     domain_scores: dict, indicators: dict, trend: Optional[str],
                     safety_reasons: Optional[list] = None) -> str:
    """safety_reasons: from the patient's unresolved safety flags; falls back to the raw answers."""
    response = _run_insight_chat(keyword, free_text, domain_scores, indicators, trend)
    note = safety_note(safety_reasons if safety_reasons is not None else _reasons_from_answers(indicators))
    if note:
        response = response.rstrip() + "\n\n" + note
    return response


def _run_insight_chat(keyword: Optional[str], free_text: Optional[str],
                      domain_scores: dict, indicators: dict, trend: Optional[str]) -> str:
    from app.config import get_settings
    settings = get_settings()
    kw = keyword or "overall"

    # Try Claude if API key is configured
    if settings.anthropic_api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            user_content = (
                build_vent_prompt(free_text, domain_scores)
                if free_text
                else build_insight_prompt(kw, domain_scores, indicators, trend)
            )
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                temperature=0.4,
                system=INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            return message.content[0].text.strip()
        except Exception:
            pass  # fall through to rule-based

    # Rule-based fallback — always produces a real insight
    if free_text:
        return _rule_based_vent(free_text, domain_scores)
    return _rule_based_insight(kw, domain_scores, indicators, trend)
