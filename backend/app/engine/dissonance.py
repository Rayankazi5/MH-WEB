from typing import List, Dict, Any, Callable

_Rule = dict[str, Any]

DISSONANCE_RULES: list[_Rule] = [
    {
        "flag_type": "sleep_late_activity",
        "condition": lambda ind: (
            ind.get("phq_3", 1.0) < 0.4           # PHQ-3 sleep item normalised — reports OK sleep
            and ind.get("late_phone_activity_nights", 0) > 0.5
        ),
        "self_report_val": "User reports adequate sleep",
        "signal_val": lambda ind: (
            f'{int(ind.get("late_phone_activity_nights", 0) * 7)} nights of late device activity detected'
        ),
        "severity": "medium",
    },
    {
        "flag_type": "mood_movement",
        "condition": lambda ind: (
            ind.get("phq_2", 1.0) < 0.3            # phq_2 = depressed mood item
            and ind.get("daily_step_variance", 0) < 0.2
        ),
        "self_report_val": "User reports low mood",
        "signal_val": "Consistent sedentary pattern — minimal movement variance",
        "severity": "high",
    },
    {
        "flag_type": "social_report_vs_withdrawal",
        "condition": lambda ind: (
            ind.get("indirect_social_days", 0) > 0.7   # reports few social days (inverted)
            and ind.get("journal_isolation", 0) > 0.6
        ),
        "self_report_val": "Patient selected few social interactions this week",
        "signal_val": "High isolation keyword frequency in journal entries",
        "severity": "medium",
    },
]


def detect_dissonance(indicators: dict) -> list[dict]:
    flags = []
    for rule in DISSONANCE_RULES:
        try:
            if rule["condition"](indicators):
                signal_val = rule["signal_val"]
                if callable(signal_val):
                    signal_val = signal_val(indicators)
                flags.append({
                    "flag_type": rule["flag_type"],
                    "self_report_val": rule["self_report_val"],
                    "signal_val": signal_val,
                    "severity": rule["severity"],
                })
        except (KeyError, TypeError, ZeroDivisionError):
            continue
    return flags
