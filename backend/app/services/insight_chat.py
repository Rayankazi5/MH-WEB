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

# Maps user-facing keyword to the relevant scoring domains and indicator keys
KEYWORD_CONFIG = {
    "sleep": {
        "label": "Your Sleep",
        "domains": ["sleep_quality"],
        "indicators": ["sleep_hours", "indirect_sleep_days", "phq_3"],
    },
    "mood": {
        "label": "Your Mood",
        "domains": ["mood_stability"],
        "indicators": ["phq_2", "phq_6", "sentiment"],
    },
    "anxiety": {
        "label": "Your Anxiety",
        "domains": ["anxiety"],
        "indicators": ["phq_4", "phq_7", "phq_8", "rt_mean"],
    },
    "energy": {
        "label": "Your Energy",
        "domains": ["cognitive_fatigue"],
        "indicators": ["phq_4", "phq_7", "indirect_productive_days"],
    },
    "social": {
        "label": "Your Social Life",
        "domains": ["social_withdrawal"],
        "indicators": ["indirect_social_days", "phq_2"],
    },
    "overall": {
        "label": "Your Overall Week",
        "domains": ["cognitive_fatigue", "social_withdrawal", "anxiety", "mood_stability", "sleep_quality"],
        "indicators": ["sleep_hours", "indirect_sleep_days", "indirect_social_days", "indirect_productive_days", "sentiment"],
    },
}

DOMAIN_LABELS = {
    "cognitive_fatigue": "mental energy and focus",
    "social_withdrawal": "social connection",
    "anxiety": "anxiety and restlessness",
    "mood_stability": "mood stability",
    "sleep_quality": "sleep quality",
}

# Human-readable PHQ label names for the prompt
PHQ_LABELS = ["not at all", "on several days", "more than half the days", "nearly every day"]


def _describe_score(score: float, domain: str) -> str:
    label = DOMAIN_LABELS.get(domain, domain)
    # Scores are softmax-normalised across 5 domains; uniform baseline = 0.20.
    # Interpret relative to that baseline, not as absolute 0-1 measurements.
    if score < 0.14:
        return f"your {label} is not a significant area of concern this week"
    elif score < 0.22:
        return f"your {label} shows some mild indicators worth keeping an eye on"
    elif score < 0.30:
        return f"your {label} shows noticeable strain this week"
    else:
        return f"your {label} is the primary area of concern this period"


def _describe_indicator(key: str, value) -> Optional[str]:
    if key == "sleep_hours":
        try:
            h = float(value)
            return f"averaging {h:.1f} hours of sleep per night"
        except (TypeError, ValueError):
            return None
    if key == "indirect_sleep_days":
        try:
            n = int(value) if not isinstance(value, list) else len(value)
            return f"{n} out of 7 nights of good sleep"
        except (TypeError, ValueError):
            return None
    if key == "indirect_social_days":
        try:
            n = int(value) if not isinstance(value, list) else len(value)
            return f"meaningful social time on {n} out of 7 days"
        except (TypeError, ValueError):
            return None
    if key == "indirect_productive_days":
        try:
            n = int(value) if not isinstance(value, list) else len(value)
            return f"feeling productive on {n} out of 7 days"
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
    if key.startswith("phq_") and value is not None:
        try:
            idx = int(value)
            label = PHQ_LABELS[idx] if 0 <= idx <= 3 else None
            if label and idx >= 1:
                key_name = key.replace("phq_", "")
                return f"PHQ item {key_name} rated {label}"
        except (TypeError, ValueError, IndexError):
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
        f"DOMAIN SUMMARY (scores are softmax-normalised across 5 domains; baseline = 0.20 — "
        f"interpret these as relative concern, not absolute quality): {domain_text}.{trend_text}\n"
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
    Used to select the appropriate tip when domain scores (which are softmax-relative)
    would otherwise understate a genuinely poor pattern.
    """
    kw = keyword if keyword in KEYWORD_CONFIG else "overall"
    config = KEYWORD_CONFIG[kw]
    concerns = []
    for key in config["indicators"]:
        val = indicators.get(key)
        if val is None:
            continue
        if key == "sleep_hours":
            try:
                # 8+ h = 0 concern, 0 h = 1.0 concern
                concerns.append(max(0.0, 1.0 - float(val) / 8.0))
            except (TypeError, ValueError):
                pass
        elif key in ("indirect_sleep_days", "indirect_social_days", "indirect_productive_days"):
            try:
                n = len(val) if isinstance(val, list) else int(val)
                # 7 days = 0 concern, 0 days = 1.0 concern
                concerns.append(max(0.0, 1.0 - n / 7.0))
            except (TypeError, ValueError):
                pass
        elif key.startswith("phq_"):
            try:
                concerns.append(int(val) / 3.0)
            except (TypeError, ValueError):
                pass
    return sum(concerns) / len(concerns) if concerns else 0.0


def _rule_based_insight(keyword: str, domain_scores: dict, indicators: dict,
                        trend: Optional[str]) -> str:
    kw = keyword if keyword in KEYWORD_CONFIG else "overall"
    config = KEYWORD_CONFIG[kw]
    relevant_domains = [d for d in config["domains"] if d in domain_scores]

    if not relevant_domains:
        return (
            f"Complete a daily check-in to start seeing insights about {config['label'].lower()}. "
            "Your data builds up over time and makes these insights more meaningful."
        )

    avg_score = sum(domain_scores[d] for d in relevant_domains) / len(relevant_domains)

    domain_descs = [_describe_score(domain_scores[d], d) for d in relevant_domains]
    main = "Based on your recent check-ins, " + " and ".join(domain_descs) + "."

    indicator_descs = [
        desc for k in config["indicators"]
        if k in indicators and (desc := _describe_indicator(k, indicators[k])) is not None
    ]
    if indicator_descs:
        main += " Your data shows " + " and ".join(indicator_descs[:2]) + "."

    if trend:
        main += f" Compared to the previous period, things appear to be {trend}."

    # Use raw-indicator concern for tip selection — the softmax domain score can be
    # misleadingly low when other domains happen to score higher, so we take the
    # more conservative of the two signals.
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


def run_insight_chat(keyword: Optional[str], free_text: Optional[str],
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
