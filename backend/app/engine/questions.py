PHQ_SCALE = {
    "min": 0, "max": 3,
    "labels": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
}

QUESTION_BANK = [
    {"key": "phq_1a", "type": "phq9", "text": "This week, how often did you lose interest in things you normally care about?", "scale": PHQ_SCALE},
    {"key": "phq_1b", "type": "phq9", "text": "This week, how often did activities feel joyless or unfulfilling, even ones you usually enjoy?", "scale": PHQ_SCALE},
    {"key": "indirect_sleep_days", "type": "calendar", "text": "Which nights this week did you sleep well? Select all that apply.", "scale": None},
    {"key": "phq_2", "type": "phq9",  "text": "Feeling down, depressed, or hopeless?", "scale": PHQ_SCALE},
    {"key": "phq_3", "type": "phq9",  "text": "Trouble falling or staying asleep, or sleeping too much?", "scale": PHQ_SCALE},
    {"key": "indirect_social_days", "type": "calendar", "text": "Which days this week did you spend meaningful time with others? Select all that apply.", "scale": None},
    {"key": "phq_4", "type": "phq9",  "text": "Feeling tired or having little energy?", "scale": PHQ_SCALE},
    {"key": "phq_5a", "type": "phq9", "text": "This week, how often did you have little or no appetite?", "scale": PHQ_SCALE},
    {"key": "phq_5b", "type": "phq9", "text": "This week, how often did you eat much more than usual or feel out of control around food?", "scale": PHQ_SCALE},
    {"key": "sleep_hours", "type": "numeric", "text": "On average, how many hours of sleep did you get per night this week?", "scale": {"min": 0, "max": 12}},
    {"key": "phq_6", "type": "phq9",  "text": "Feeling bad about yourself — or that you are a failure?", "scale": PHQ_SCALE},
    {"key": "indirect_productive_days", "type": "calendar", "text": "Which days this week felt productive to you? Select all that apply.", "scale": None},
    {"key": "phq_7", "type": "phq9",  "text": "Trouble concentrating on things?", "scale": PHQ_SCALE},
    {"key": "phq_8", "type": "phq9",  "text": "Moving or speaking slowly — or being fidgety or restless?", "scale": PHQ_SCALE},
    {"key": "phq_9", "type": "phq9",  "text": "Thoughts that you would be better off dead or hurting yourself?", "scale": PHQ_SCALE},
]

EXPECTED_INDICATOR_KEYS = [
    "phq_1", "phq_2", "phq_3", "phq_4", "phq_5", "phq_6", "phq_7", "phq_8", "phq_9",
    "indirect_sleep_days", "indirect_social_days", "indirect_productive_days",
    "sleep_hours", "rt_mean",
    "sentiment", "journal_isolation", "journal_work_stress", "journal_sleep_disruption",
]
# phq_1 is derived from phq_1a + phq_1b (average); phq_5 from phq_5a + phq_5b (max)
